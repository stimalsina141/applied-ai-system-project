import os

from coach.runner import run_tests, syntax_check
from conftest import CALC, CALC_TESTS


def test_reports_passed_and_failed_tests():
    run = run_tests({"calc.py": CALC, "test_calc.py": CALC_TESTS})
    assert (run.passed, run.failed) == (1, 1)
    assert run.failing_names == {"test_calc::test_add"}
    assert not run.all_passed
    assert run.exit_code == 1
    assert run.duration > 0


def test_all_passing():
    fixed = CALC.replace("a - b", "a + b")
    run = run_tests({"calc.py": fixed, "test_calc.py": CALC_TESTS})
    assert run.all_passed
    assert run.headline().startswith("2 passed")


def test_syntax_error_in_code_counts_as_error():
    run = run_tests({"calc.py": "def add(:\n", "test_calc.py": CALC_TESTS})
    assert not run.all_passed
    assert run.problems >= 1


def test_infinite_loop_times_out():
    code = "def spin():\n    while True:\n        pass\n"
    tests = "from spin import spin\n\ndef test_spin():\n    spin()\n"
    run = run_tests({"spin.py": code, "test_spin.py": tests}, timeout=2)
    assert run.timed_out
    assert not run.all_passed


def test_api_keys_are_hidden_from_test_code(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    tests = "import os\n\ndef test_no_key():\n    assert 'ANTHROPIC_API_KEY' not in os.environ\n"
    run = run_tests({"test_env.py": tests})
    assert run.all_passed
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-secret"


def test_syntax_check_without_tests():
    assert syntax_check({"a.py": "x = 1\n"}, ["a.py"]).exit_code == 0
    assert syntax_check({"a.py": "x = (\n"}, ["a.py"]).exit_code == 1
