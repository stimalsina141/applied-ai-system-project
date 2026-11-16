from coach.agent import DebugSession
from coach.report import build_report, reliability_rows
from conftest import ScriptedLLM, analysis, diagnosis, patch, quality


def test_report_has_every_section(calc_workspace):
    session = DebugSession(calc_workspace, ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality()))
    session.run_auto()
    report = build_report(session)
    for heading in ["## Problem", "## Root cause", "## Changes made", "## Validation",
                    "## Concept learned", "## Code quality", "## Remaining concerns"]:
        assert heading in report
    assert "**Status:** Fixed" in report
    assert "Arithmetic operators matter." in report


def test_reliability_rows_for_fixed_session(calc_workspace):
    session = DebugSession(calc_workspace, ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality()))
    session.run_auto()
    rows = dict(reliability_rows(session))
    assert rows["Original bug addressed"] == "1 of 1 failing tests now pass"
    assert rows["Existing tests preserved"] == "1 of 1 still pass"
    assert rows["Unrelated behavior changed"] == "Not detected"


def test_report_lists_still_failing_tests(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a * b"), analysis("give_up"))
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    report = build_report(session)
    assert "**Status:** Unable to fix" in report
    assert "test_calc::test_add" in report
    assert "Suggested next step" in report
