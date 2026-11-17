import pytest

from coach.agent import DebugSession
from coach.report import build_report, reliability_rows, split_code
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
    assert rows["Unrelated behavior changed"] == \
        "Not detected by the 2 provided tests (only the declared functions changed)"


def test_report_does_not_overclaim(calc_workspace):
    session = DebugSession(calc_workspace, ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality()))
    session.run_auto()
    report = build_report(session)
    assert "None found by the 2 provided tests. Inputs and behavior the tests don't cover were not checked." in report
    assert "the fix follows your tests" in report  # no design choice reported, so the default note appears


def test_design_choices_are_reported(calc_workspace):
    p = patch("a - b", "a + b")
    p.design_choices = ["Returns 0 for an empty list because test_average_empty requires it; "
                        "None or ValueError are common alternatives."]
    session = DebugSession(calc_workspace, ScriptedLLM(diagnosis(), p, quality()))
    session.run_auto()
    assert "- Returns 0 for an empty list because test_average_empty requires it" in build_report(session)


@pytest.mark.parametrize("text, prose, code", [
    ("To fix it, add a check. Here's an example:\n\n```python\ndef f(x):\n    return x\n```\nThat's all.",
     "To fix it, add a check. Here's an example:\n\nThat's all.", "def f(x):\n    return x"),
    ("def f(x):\n    return x", "", "def f(x):\n    return x"),
    ("Just a sentence.", "Just a sentence.", ""),
    ("", "", ""),
])
def test_split_code_separates_prose_from_code(text, prose, code):
    assert split_code(text) == (prose, code)


def test_report_lists_still_failing_tests(calc_workspace):
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a * b"), analysis("give_up"))
    session = DebugSession(calc_workspace, llm)
    session.run_auto()
    report = build_report(session)
    assert "**Status:** Unable to fix" in report
    assert "test_calc::test_add" in report
    assert "Suggested next step" in report
