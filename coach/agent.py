"""The agentic debugging workflow.

    inspect -> diagnose -> plan + patch -> preview / approve -> run tests
            -> review results -> retry (up to MAX_ATTEMPTS) -> report

The AI proposes and reasons. This module decides what actually happens:
it applies patches through guardrails, runs the tests, decides whether a
patch is kept, and computes the final status from test results, never
from what the AI claims.
"""
import uuid
from dataclasses import dataclass, field

from coach import config, prompts
from coach.llm import LLM, LLMError
from coach.logging_setup import SessionLog
from coach.runner import TestRun, validate
from coach.schemas import Diagnosis, FailureAnalysis, PatchProposal, QualityReview
from coach.workspace import (
    FileDiff, PatchError, Workspace, apply_patch, changed_functions, make_diff, static_checks,
)

STATUS_LABELS = {
    "fixed": "Fixed",
    "partially_fixed": "Partially fixed",
    "unable_to_fix": "Unable to fix",
    "needs_user_input": "Needs user input",
    "unverified": "Patch proposed, not verified",
}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


class SessionError(Exception):
    """An action was requested that the current phase does not allow."""


@dataclass
class Attempt:
    number: int
    proposal: PatchProposal
    state: str = "proposed"  # proposed | invalid | rejected | tested
    files_after: dict[str, str] | None = None
    diff: list[FileDiff] = field(default_factory=list)
    error: str = ""
    user_feedback: str = ""
    test_run: TestRun | None = None
    kept: bool = False
    keep_reason: str = ""
    analysis: FailureAnalysis | None = None


class DebugSession:
    def __init__(self, workspace: Workspace, llm: LLM, max_attempts: int = config.MAX_ATTEMPTS):
        self.id = uuid.uuid4().hex[:8]
        self.workspace = workspace
        self.llm = llm
        self.max_attempts = max_attempts
        self.log = SessionLog(self.id)

        self.original_files = dict(workspace.files)
        self.current_files = dict(workspace.files)
        self.baseline: TestRun | None = None
        self.current_run: TestRun | None = None
        self.diagnosis: Diagnosis | None = None
        self.attempts: list[Attempt] = []

        self.phase = "new"  # new | diagnosed | awaiting_approval | done
        self.status: str | None = None
        self.stop_reason = ""
        self.static_findings: list[dict] = []
        self.quality: QualityReview | None = None
        self.chat: list[dict] = []

        n_tests = len(workspace.test_files)
        self.log.info(
            f"Session started: {workspace.name}. {_plural(len(workspace.files), 'file')} "
            f"({', '.join(workspace.files)}), {_plural(n_tests, 'test file')}, "
            f"max {_plural(max_attempts, 'attempt')}"
        )

    # ----- convenience -------------------------------------------------

    @property
    def has_tests(self) -> bool:
        return bool(self.workspace.test_files)

    @property
    def code_paths(self) -> list[str]:
        return sorted(self.workspace.editable)

    @property
    def done(self) -> bool:
        return self.phase == "done"

    @property
    def attempts_left(self) -> int:
        return self.max_attempts - len(self.attempts)

    @property
    def pending(self) -> Attempt | None:
        if self.attempts and self.attempts[-1].state == "proposed":
            return self.attempts[-1]
        return None

    @property
    def kept_attempts(self) -> list[Attempt]:
        return [a for a in self.attempts if a.kept]

    # ----- steps -------------------------------------------------------

    def start(self) -> None:
        """Inspect the code and tests, then diagnose."""
        if self.phase != "new":
            raise SessionError("This session has already started.")
        self.baseline = validate(self.current_files, self.code_paths, self.has_tests)
        self.current_run = self.baseline
        self.log.info(f"Baseline: {self.baseline.headline()}")

        self.diagnosis = self.llm.structured(
            system=prompts.SYSTEM,
            prompt=prompts.diagnose(
                files=self.current_files, editable=self.workspace.editable,
                symptom=self.workspace.symptom, error=self.workspace.error, baseline=self.baseline,
            ),
            schema=Diagnosis,
        )
        counts = {s: sum(f.status == s for f in self.diagnosis.findings) for s in ("confirmed", "likely", "unknown")}
        self.log.info(
            f"Diagnosis generated: {self.diagnosis.concept} (confidence {self.diagnosis.confidence}; "
            f"{counts['confirmed']} confirmed, {counts['likely']} likely, {counts['unknown']} unknown)"
        )
        self.phase = "diagnosed"

        if self.diagnosis.needs_more_info:
            self.finish("The coach needs more information before it can propose a fix.",
                        forced_status="needs_user_input")

    def propose(self, user_feedback: str = "") -> Attempt:
        """Ask the AI for a patch and check it against the guardrails."""
        if self.phase != "diagnosed":
            raise SessionError("A patch can only be proposed after diagnosis, when none is pending.")
        if self.attempts_left <= 0:
            raise SessionError("No attempts left.")

        proposal = self.llm.structured(
            system=prompts.SYSTEM,
            prompt=prompts.propose_patch(
                files=self.current_files, editable=self.workspace.editable,
                diagnosis=self.diagnosis, current_run=self.current_run,
                history=self._history(), user_feedback=user_feedback,
            ),
            schema=PatchProposal,
        )
        attempt = Attempt(number=len(self.attempts) + 1, proposal=proposal)
        self.attempts.append(attempt)
        target_names = ", ".join(sorted({f"{t.file}:{t.function}" for t in proposal.targets}))

        try:
            attempt.files_after = apply_patch(self.current_files, self.workspace.editable, proposal)
        except PatchError as e:
            attempt.state = "invalid"
            attempt.error = str(e)
            self.log.warning(f"Attempt {attempt.number}: patch blocked by guardrail: {e}")
            if self.attempts_left <= 0:
                self.finish("Every attempt was used up.")
            return attempt

        attempt.diff = make_diff(self.current_files, attempt.files_after)
        added = sum(d.added for d in attempt.diff)
        removed = sum(d.removed for d in attempt.diff)
        self.log.info(f"Attempt {attempt.number}: patch proposed for {target_names} (+{added} -{removed} lines)")
        self.phase = "awaiting_approval"
        return attempt

    def reject(self, feedback: str = "") -> None:
        """The user declined the pending patch. Nothing is run."""
        attempt = self._require_pending()
        attempt.state = "rejected"
        attempt.user_feedback = feedback.strip()
        self.log.info(f"Attempt {attempt.number}: patch rejected by user")
        self.phase = "diagnosed"
        if self.attempts_left <= 0:
            self.finish("The last proposed patch was rejected and no attempts are left.",
                        forced_status=None if self.kept_attempts else "needs_user_input")

    def approve(self) -> Attempt:
        """Run the tests against the pending patch in a sandbox and review the results."""
        attempt = self._require_pending()
        self.log.info(f"Attempt {attempt.number}: approved, running {'pytest' if self.has_tests else 'syntax check'}")
        run = validate(attempt.files_after, self.code_paths, self.has_tests)
        attempt.test_run = run
        attempt.state = "tested"
        self.log.info(f"Attempt {attempt.number}: {run.headline()}")

        attempt.kept, attempt.keep_reason = self._judge(run)
        if attempt.kept:
            self.current_files = attempt.files_after
            self.current_run = run
            self.log.info(f"Attempt {attempt.number}: patch kept ({attempt.keep_reason})")
        else:
            self.log.warning(f"Attempt {attempt.number}: patch discarded ({attempt.keep_reason})")
        self.phase = "diagnosed"

        if not self.has_tests:
            if attempt.kept:
                self.finish("The patch compiles, but there were no tests to verify the fix.")
            elif self.attempts_left <= 0:
                self.finish("Every attempt was used up.")
            return attempt

        if run.all_passed:
            self.finish("All tests pass.")
            return attempt

        attempt.analysis = self.llm.structured(
            system=prompts.SYSTEM,
            prompt=prompts.analyze_failure(
                files=attempt.files_after, editable=self.workspace.editable,
                diagnosis=self.diagnosis, patch=attempt.proposal, run=run,
            ),
            schema=FailureAnalysis,
        )
        self.log.info(
            f"Attempt {attempt.number}: failure analysis, caused by patch: "
            f"{attempt.analysis.caused_by_patch}, recommendation: {attempt.analysis.recommendation}"
        )

        if attempt.analysis.recommendation == "needs_user_input":
            self.finish("The coach needs clarification about the intended behavior.",
                        forced_status=None if self.kept_attempts else "needs_user_input")
        elif attempt.analysis.recommendation == "give_up":
            self.finish("The coach could not find a fix within the files it is allowed to edit.")
        elif self.attempts_left <= 0:
            self.finish(f"Stopped after {self.max_attempts} attempts.")
        else:
            self.log.info(f"Retrying ({self.attempts_left} attempts left)")
        return attempt

    def run_auto(self) -> None:
        """Run the whole loop without pausing for approval (patches still only run in the sandbox)."""
        try:
            if self.phase == "new":
                self.start()
            while not self.done:
                if self.pending:
                    self.approve()
                else:
                    self.propose()
        except LLMError as e:
            self.log.error(f"AI service error: {e}")
            if not self.done:
                self.finish(f"Stopped because of an AI service error: {e}")

    def finish(self, reason: str, forced_status: str | None = None) -> None:
        if self.done:
            return
        if self.pending:
            self.pending.state = "rejected"
            self.pending.user_feedback = "Session ended before this patch was approved."
        self.status = forced_status or self._final_status()
        self.stop_reason = reason
        self.phase = "done"
        self.log.info(f"Retry count: {len(self.attempts)} of {self.max_attempts}")
        self.log.info(f"Final status: {STATUS_LABELS[self.status]}. {reason}")
        if self.kept_attempts:
            self._review_quality()

    def ask(self, question: str) -> str:
        """Answer a follow-up question about this session."""
        from coach.report import build_report  # avoid a circular import

        question = question.strip()
        if not question:
            raise SessionError("Ask a question first.")
        summary = build_report(self) + "\n\nFinal code:\n\n" + prompts.render_files(
            self.current_files, self.workspace.editable)
        messages = self.chat[-10:] + [{"role": "user", "content": question}]
        answer = self.llm.chat(system=prompts.follow_up_system(summary), messages=messages)
        self.chat += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        self.log.info("Follow-up question answered")
        return answer

    # ----- application logic -------------------------------------------

    def _require_pending(self) -> Attempt:
        if self.phase != "awaiting_approval" or not self.pending:
            raise SessionError("There is no patch waiting for approval.")
        return self.pending

    def _judge(self, run: TestRun) -> tuple[bool, str]:
        """Keep a patch only if it makes measurable progress without breaking anything."""
        if not self.has_tests:
            return (run.exit_code == 0,
                    "the code compiles" if run.exit_code == 0 else "the patched code has a syntax error")
        before = self.current_run
        if run.timed_out:
            return False, "the tests timed out"
        broken = sorted(before.passing_names - run.passing_names)
        if broken:
            shown = ", ".join(broken[:3]) + ("..." if len(broken) > 3 else "")
            return False, f"it broke {len(broken)} test(s) that passed before: {shown}"
        if run.all_passed:
            return True, "all tests pass"
        if run.problems < before.problems:
            return True, f"failures went from {before.problems} to {run.problems}"
        return False, f"no improvement ({run.problems} failing before and after)"

    def _final_status(self) -> str:
        if not self.has_tests:
            return "unverified" if self.kept_attempts else "unable_to_fix"
        if self.current_run.all_passed:
            # If the tests already passed before any change, they never captured the bug.
            return "unverified" if self.baseline.all_passed else "fixed"
        if self.current_run.problems < self.baseline.problems:
            return "partially_fixed"
        return "unable_to_fix"

    def _history(self) -> list[str]:
        lines = []
        for a in self.attempts:
            head = f"Attempt {a.number}: {a.proposal.plan}"
            if a.state == "invalid":
                lines.append(f"{head}\n  Blocked by a guardrail before running: {a.error}")
            elif a.state == "rejected":
                lines.append(f"{head}\n  Rejected by the learner: {a.user_feedback or 'no reason given'}")
            elif a.state == "tested":
                result = f"{head}\n  Result: {a.test_run.headline()}. "
                result += "Kept." if a.kept else f"Discarded because {a.keep_reason}."
                if a.analysis:
                    result += f"\n  Analysis: {a.analysis.next_step}"
                lines.append(result)
        return lines

    def _review_quality(self) -> None:
        self.static_findings = static_checks(self.current_files, self.workspace.editable)
        try:
            self.quality = self.llm.structured(
                system=prompts.SYSTEM,
                prompt=prompts.review_quality(
                    original=self.original_files, final=self.current_files,
                    editable=self.workspace.editable, static_findings=self.static_findings,
                ),
                schema=QualityReview,
            )
            self.log.info(f"Quality review: {len(self.quality.issues)} issues, "
                          f"{len(self.static_findings)} automated findings")
        except LLMError as e:
            self.log.warning(f"Quality review skipped: {e}")

    # ----- derived results ---------------------------------------------

    def declared_targets(self) -> set[tuple[str, str]]:
        return {(t.file, t.function.removesuffix("()")) for a in self.kept_attempts for t in a.proposal.targets}

    def out_of_scope_changes(self) -> list[str]:
        """Functions changed by the kept patches that no patch declared as a target."""
        declared = self.declared_targets()
        extra = []
        for path, functions in changed_functions(self.original_files, self.current_files).items():
            for fn in sorted(functions):
                if (path, fn) not in declared:
                    extra.append(f"{path}:{fn}")
        return extra
