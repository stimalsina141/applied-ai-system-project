"""The final educational debugging report and reliability summary."""
from coach.agent import STATUS_LABELS, DebugSession


def reliability_rows(session: DebugSession) -> list[tuple[str, str]]:
    """Checks computed from test results, not from what the AI says."""
    if not session.has_tests or session.baseline is None:
        return [
            ("Tests available", "No - only a syntax check was possible"),
            ("Code compiles", "Yes" if session.current_run and session.current_run.exit_code == 0 else "No"),
            ("Unrelated behavior changed", _scope_result(session)),
        ]

    base, final = session.baseline, session.current_run
    originally_failing = base.failing_names
    now_fixed = originally_failing & final.passing_names
    originally_passing = base.passing_names
    still_passing = originally_passing & final.passing_names

    if base.problems and not originally_failing:
        bug_check = "Passed" if final.all_passed else "Failed"  # e.g. a collection error at baseline
    elif originally_failing:
        bug_check = f"{len(now_fixed)} of {len(originally_failing)} failing tests now pass"
    else:
        bug_check = "Not measurable (no test failed before the fix)"

    return [
        ("Original bug addressed", bug_check),
        ("Existing tests preserved",
         f"{len(still_passing)} of {len(originally_passing)} still pass" if originally_passing else "No tests passed before"),
        ("Full test suite", final.headline()),
        ("Unrelated behavior changed", _scope_result(session)),
    ]


def _scope_result(session: DebugSession) -> str:
    if not session.kept_attempts:
        return "No changes kept"
    extra = session.out_of_scope_changes()
    return "Not detected" if not extra else "Changes outside declared targets: " + ", ".join(extra)


def build_report(session: DebugSession) -> str:
    d = session.diagnosis
    lines = ["# Debugging Report", ""]
    lines += [f"**Status:** {STATUS_LABELS.get(session.status, 'In progress')}",
              f"**Why it stopped:** {session.stop_reason or 'Still running.'}",
              f"**Attempts used:** {len(session.attempts)} of {session.max_attempts}", ""]

    lines += ["## Problem", "", session.workspace.symptom or "(no description given)", ""]
    if session.workspace.error:
        lines += ["```text", session.workspace.error.strip(), "```", ""]

    lines += ["## Root cause", ""]
    if d:
        lines += [d.root_cause, "", f"Confidence: {d.confidence}", ""]
        for f in d.findings:
            lines.append(f"- **{f.status.capitalize()}** `{f.file}` `{f.function}` (lines {f.lines}): {f.summary}")
        if d.questions_for_user:
            lines += ["", "Questions for you:"] + [f"- {q}" for q in d.questions_for_user]
    else:
        lines.append("No diagnosis was produced.")
    lines.append("")

    lines += ["## Changes made", ""]
    if session.kept_attempts:
        for a in session.kept_attempts:
            targets = ", ".join(f"`{t.file}` `{t.function}`" for t in a.proposal.targets)
            lines.append(f"- **Attempt {a.number}** ({targets}): {a.proposal.summary}")
            for assumption in a.proposal.assumptions:
                lines.append(f"  - Assumption: {assumption}")
    else:
        lines.append("No changes were kept.")
    discarded = [a for a in session.attempts if not a.kept]
    if discarded:
        lines += ["", "Attempts that were not kept:"]
        for a in discarded:
            reason = {"invalid": f"blocked by a guardrail ({a.error})",
                      "rejected": f"rejected ({a.user_feedback or 'no reason given'})",
                      "tested": f"discarded because {a.keep_reason}"}.get(a.state, a.state)
            lines.append(f"- Attempt {a.number}: {reason}")
    lines.append("")

    lines += ["## Validation", ""]
    if session.baseline:
        lines.append(f"- Before: {session.baseline.headline()}")
    if session.current_run:
        lines.append(f"- After: {session.current_run.headline()}")
    lines += ["", "| Check | Result |", "|---|---|"]
    lines += [f"| {check} | {result} |" for check, result in reliability_rows(session)]
    lines.append("")

    lines += ["## Concept learned", ""]
    if session.quality:
        lines.append(session.quality.concept_learned)
    elif d:
        lines.append(f"{d.concept}.")
    lines.append("")

    lines += ["## Code quality", ""]
    if session.static_findings or (session.quality and session.quality.issues):
        for f in session.static_findings:
            lines.append(f"- `{f['file']}` line {f['line']}: {f['issue']} (automated check)")
        if session.quality:
            for issue in session.quality.issues:
                lines.append(f"- {issue.category} ({issue.severity}): {issue.description}")
    else:
        lines.append("No issues found." if session.quality else "Not reviewed (no changes were kept).")
    if session.quality and session.quality.suggested_tests:
        lines += ["", "Suggested tests:"] + [f"- {t}" for t in session.quality.suggested_tests]
    lines.append("")

    lines += ["## Remaining concerns", ""]
    concerns = _remaining_concerns(session)
    lines += [f"- {c}" for c in concerns] if concerns else ["None identified."]
    return "\n".join(lines) + "\n"


def _remaining_concerns(session: DebugSession) -> list[str]:
    concerns = []
    if session.current_run:
        for case in session.current_run.cases:
            if case.outcome in ("failed", "error"):
                concerns.append(f"`{case.name}` still fails: {case.message or 'see test output'}")
    if session.status == "unverified":
        if not session.has_tests:
            concerns.append("No tests were provided, so the fix is unverified. Add a test that reproduces the bug.")
        else:
            concerns.append("The tests passed even before the fix, so they do not capture the reported bug.")
    if session.diagnosis:
        for f in session.diagnosis.findings:
            if f.status == "unknown":
                concerns.append(f"Unconfirmed: {f.summary}")
    last = session.attempts[-1] if session.attempts else None
    if last and last.analysis and session.status != "fixed":
        concerns.append(f"Suggested next step: {last.analysis.next_step}")
    extra = session.out_of_scope_changes() if session.kept_attempts else []
    if extra:
        concerns.append("Review changes outside the declared targets: " + ", ".join(extra))
    return concerns
