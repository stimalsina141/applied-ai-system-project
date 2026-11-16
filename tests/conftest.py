"""Shared fixtures: a scripted stand-in for Claude so tests run offline."""
import pytest

from coach.schemas import Diagnosis, Edit, FailureAnalysis, Finding, PatchProposal, QualityReview, Target


class ScriptedLLM:
    """Returns pre-written responses in order and records every prompt it was sent."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []

    def structured(self, *, system, prompt, schema):
        self.prompts.append((schema.__name__, prompt))
        assert self.responses, f"No scripted response left for {schema.__name__}"
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, schema), f"Expected {schema.__name__}, got {type(response).__name__}"
        return response

    def chat(self, *, system, messages):
        self.prompts.append(("chat", messages[-1]["content"]))
        return self.responses.pop(0)


def diagnosis(needs_more_info=False, function="add"):
    return Diagnosis(
        problem_summary="add() returns the wrong value.",
        findings=[Finding(status="confirmed", summary="add subtracts instead of adding",
                          evidence="test_add fails: assert -1 == 5", file="calc.py",
                          function=function, lines="2")],
        root_cause="The function uses - instead of +.",
        confidence="high",
        needs_more_info=needs_more_info,
        questions_for_user=["What should add() return?"] if needs_more_info else [],
        concept="arithmetic operators",
        explanation="The minus sign subtracts the numbers.",
        small_example="print(2 + 3)",
    )


def patch(find, replace, function="add", file="calc.py"):
    return PatchProposal(
        targets=[Target(file=file, function=function, lines="2")],
        plan=f"Replace {find!r} with {replace!r}.",
        edits=[Edit(file=file, function=function, find=find, replace=replace)],
        summary="Only the return line of add changed.",
        assumptions=[],
    )


def analysis(recommendation="retry"):
    return FailureAnalysis(
        explanations=[], caused_by_patch="no", progress="Nothing yet.",
        next_step="Fix the operator.", recommendation=recommendation,
    )


def quality():
    return QualityReview(issues=[], suggested_tests=["Test negative numbers"],
                         concept_learned="Arithmetic operators matter.")


CALC = "def add(a, b):\n    return a - b\n\n\ndef double(x):\n    return x * 2\n"
CALC_TESTS = (
    "from calc import add, double\n\n"
    "def test_add():\n    assert add(2, 3) == 5\n\n"
    "def test_double():\n    assert double(4) == 8\n"
)


@pytest.fixture
def calc_workspace():
    from coach.workspace import Workspace
    return Workspace(files={"calc.py": CALC, "test_calc.py": CALC_TESTS}, editable={"calc.py"},
                     symptom="add(2, 3) gives -1")
