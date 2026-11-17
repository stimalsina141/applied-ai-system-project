import pytest

from coach.agent import DebugSession, SessionError
from coach.llm import LLMError
from coach.workspace import Workspace
from conftest import CALC, ScriptedLLM, analysis, diagnosis, patch, quality


def test_fixes_bug_on_first_attempt(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.run_auto()

    assert session.status == "fixed"
    assert len(session.attempts) == 1
    assert session.attempts[0].kept
    assert session.baseline.failed == 1
    assert session.current_run.all_passed
    assert "a + b" in session.current_files["calc.py"]


def test_original_files_are_never_modified(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    assert calc_workspace.files["calc.py"] == CALC
    assert session.original_files["calc.py"] == CALC


def test_retries_after_failed_attempt_then_fixes(calc_workspace):
    llm = ScriptedLLM(
        diagnosis(),
        patch("a - b", "a * b"),  # wrong fix: 2 * 3 != 5
        analysis("retry"),
        patch("a - b", "a + b"),
        quality(),
    )
    session = DebugSession(calc_workspace, llm)
    session.run_auto()

    assert session.status == "fixed"
    assert [a.kept for a in session.attempts] == [False, True]
    # The second patch prompt must tell the AI what happened on the first attempt.
    second_patch_prompt = [p for name, p in llm.prompts if name == "PatchProposal"][1]
    assert "Attempt 1" in second_patch_prompt and "Discarded" in second_patch_prompt


def test_stops_after_max_attempts(calc_workspace):
    llm = ScriptedLLM(
        diagnosis(),
        patch("a - b", "a * b"), analysis(),
        patch("a - b", "b - a"), analysis(),
        patch("a - b", "a // b"), analysis(),
    )
    session = DebugSession(calc_workspace, llm, max_attempts=3)
    session.run_auto()

    assert session.status == "unable_to_fix"
    assert len(session.attempts) == 3
    assert "3 attempts" in session.stop_reason
    assert session.current_files["calc.py"] == CALC


def test_patch_that_breaks_passing_test_is_discarded(calc_workspace):
    bad = patch("a - b", "a + b", function="add")
    bad.targets.append(bad.targets[0].model_copy(update={"function": "double"}))
    bad.edits.append(bad.edits[0].model_copy(update={"function": "double",
                                                      "new_code": "def double(x):\n    return x * 3\n"}))
    llm = ScriptedLLM(diagnosis(), bad, analysis("give_up"))
    session = DebugSession(calc_workspace, llm)
    session.run_auto()

    attempt = session.attempts[0]
    assert not attempt.kept
    assert "broke 1 test" in attempt.keep_reason
    assert session.status == "unable_to_fix"


def test_guardrail_blocks_edit_to_test_file_and_counts_attempt(calc_workspace):
    cheat = patch("add(2, 3) == 5", "True", function="test_add", file="test_calc.py")
    llm = ScriptedLLM(diagnosis(), cheat, patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.run_auto()

    assert session.attempts[0].state == "invalid"
    assert "protected" in session.attempts[0].error
    assert session.status == "fixed"
    assert len(session.attempts) == 2


def test_needs_more_info_stops_before_patching(calc_workspace):
    llm = ScriptedLLM(diagnosis(needs_more_info=True))
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    assert session.status == "needs_user_input"
    assert session.attempts == []


def test_step_mode_requires_approval_before_running(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.start()
    attempt = session.propose()

    assert session.phase == "awaiting_approval"
    assert attempt.test_run is None
    assert attempt.diff and "+    return a + b" in attempt.diff[0].unified
    with pytest.raises(SessionError):
        session.propose()

    session.approve()
    assert session.status == "fixed"


def test_rejected_patch_feedback_reaches_next_prompt(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "abs(a - b)"), patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.start()
    session.propose()
    session.reject("That hides the bug instead of fixing it.")
    assert session.attempts[0].test_run is None

    session.propose()
    last_prompt = [p for name, p in llm.prompts if name == "PatchProposal"][-1]
    assert "hides the bug" in last_prompt
    session.approve()
    assert session.status == "fixed"


def test_partial_fix_is_reported_as_partial():
    files = {
        "calc.py": "def add(a, b):\n    return a - b\n\n\ndef double(x):\n    return x * 3\n",
        "test_calc.py": "from calc import add, double\n\ndef test_add():\n    assert add(2, 3) == 5\n\n"
                        "def test_double():\n    assert double(4) == 8\n",
    }
    ws = Workspace(files=files, editable={"calc.py"})
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), analysis("give_up"), quality())
    session = DebugSession(ws, llm)
    session.run_auto()
    assert session.status == "partially_fixed"
    assert session.attempts[0].kept


def test_no_tests_means_unverified():
    ws = Workspace.from_paste("def add(a, b):\n    return a - b\n", filename="calc.py")
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality())
    session = DebugSession(ws, llm)
    session.run_auto()
    assert session.status == "unverified"
    assert session.baseline.kind == "syntax"


def test_ai_service_error_ends_session_cleanly(calc_workspace):
    llm = ScriptedLLM(diagnosis(), LLMError("Rate limited"))
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    assert session.done
    assert session.status == "unable_to_fix"
    assert "Rate limited" in session.stop_reason


def test_follow_up_question_uses_session_context(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality(), "Because minus subtracts.")
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    answer = session.ask("Why did you change calc.py?")
    assert answer == "Because minus subtracts."
    assert session.chat[-1]["role"] == "assistant"


def test_events_are_logged_without_source_code(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality())
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    messages = [e.message for e in session.log.events]
    assert any(m.startswith("Session started") for m in messages)
    assert any(m.startswith("Diagnosis generated") for m in messages)
    assert any("patch proposed" in m for m in messages)
    assert any(m.startswith("Final status: Fixed") for m in messages)
    assert not any("return a" in m for m in messages)
