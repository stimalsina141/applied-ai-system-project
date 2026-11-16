"""The built-in examples double as the evaluation set, so they must be valid:
each one fails as shipped, and its reference solution passes every test."""
import pytest

from coach.examples import list_examples
from coach.runner import run_tests

EXAMPLES = list_examples()


def test_examples_exist():
    assert len(EXAMPLES) >= 5
    assert EXAMPLES[0].key == "number_guessing_game"


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.key)
def test_example_fails_before_fix(example):
    ws = example.workspace()
    assert ws.test_files, "every example needs tests"
    assert "solution/" not in " ".join(ws.files)
    run = run_tests(ws.files)
    assert run.problems > 0


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.key)
def test_reference_solution_passes(example):
    run = run_tests(example.solution_files())
    assert run.all_passed, run.output


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.key)
def test_expected_functions_exist(example):
    ws = example.workspace()
    source = "\n".join(ws.files[p] for p in ws.editable)
    for fn in ws.expected["functions"]:
        assert f"def {fn}(" in source
