"""Drive the Streamlit UI headlessly with a scripted model."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import coach.llm
from conftest import CALC, CALC_TESTS, ScriptedLLM, analysis, diagnosis, patch, quality

APP = Path(__file__).resolve().parent.parent / "app.py"


def _fake_model(monkeypatch, *responses):
    llm = ScriptedLLM(*responses)
    monkeypatch.setattr(coach.llm, "local_models", lambda: ["qwen2.5-coder:3b"])
    monkeypatch.setattr(coach.llm, "llm_status", lambda *a: (True, "ready"))
    monkeypatch.setattr(coach.llm, "create_llm", lambda *a: llm)
    return llm


@pytest.fixture
def app(monkeypatch):
    diag = diagnosis()
    diag.small_example = "Here's the idea:\n```python\ndef add(a, b):\n    return a + b\n```"
    _fake_model(monkeypatch, diag, patch("a - b", "a + b"), quality(), "Minus subtracts.")
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    return at


def _button(at, label):
    return next(b for b in at.button if b.label.startswith(label))


def _paste(at, code=CALC, tests=CALC_TESTS):
    at.radio[0].set_value("Paste my own code").run()
    at.text_input[0].set_value("calc.py")
    at.text_area[0].set_value(code)
    at.text_area[1].set_value(tests)
    at.text_area[3].set_value("add(2, 3) gives -1")


def test_review_mode_end_to_end(app):
    at = app
    _paste(at)
    _button(at, "Start debugging").click().run()

    assert not at.exception
    headers = [h.value for h in at.header]
    assert "2. Diagnosis" in headers and "3. Explanation" in headers
    # The example contains the fix, so it stays hidden until the fix is tested.
    assert not any("return a + b" in c.value for c in at.code)
    assert any("hidden until the fix has been tested" in c.value for c in at.caption)
    assert at.slider[0].disabled  # the attempt limit can't change mid-session
    assert any("Attempts used: **0 of 3**" in c.value for c in at.sidebar.caption)

    _button(at, "Propose a fix").click().run()
    assert any("+    return a + b" in c.value for c in at.code)
    assert any("Nothing has run yet" in i.value for i in at.info)

    _button(at, "✅ Approve").click().run()
    assert not at.exception
    assert any("Fixed" in s.value for s in at.success)
    assert "5. Report" in [h.value for h in at.header]
    # Now the example is shown, with its prose outside the code block.
    example = next(c.value for c in at.code if c.value.startswith("def add"))
    assert "Here's the idea" not in example

    at.chat_input[0].set_value("Why?").run()
    assert any("Minus subtracts." in m.markdown[0].value for m in at.chat_message)


def test_run_automatically_skips_approval_but_still_runs_tests(monkeypatch):
    _fake_model(monkeypatch, diagnosis(), patch("a - b", "a + b"), quality())
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.toggle[0].set_value(True)
    _paste(at)
    _button(at, "Start debugging").click().run()

    assert not at.exception
    assert not [b for b in at.button if b.label.startswith("✅ Approve")]
    assert any("Tests:** 2 passed" in s.value for s in at.success)  # the claim comes from pytest
    assert "5. Report" in [h.value for h in at.header]


def test_unfixable_bug_stops_at_slider_limit(monkeypatch):
    _fake_model(monkeypatch, diagnosis(), patch("a - b", "a * b"), analysis(), patch("a - b", "b - a"), analysis())
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.toggle[0].set_value(True)
    at.slider[0].set_value(2)
    _paste(at)
    _button(at, "Start debugging").click().run()

    assert not at.exception
    assert any("Unable to fix" in e.value and "2 attempts" in e.value for e in at.error)
    assert any("Attempt 2 of 2" in x.label for x in at.expander)
    assert not any("Fixed" in s.value for s in at.success)


@pytest.mark.parametrize("code, filename, message", [
    ("   ", "calc.py", "Paste some Python code"),
    (CALC, "test_calc.py", "cannot look like a test file"),
])
def test_bad_input_shows_message_without_crashing(monkeypatch, code, filename, message):
    _fake_model(monkeypatch)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    _paste(at, code=code)
    at.text_input[0].set_value(filename)
    _button(at, "Start debugging").click().run()
    assert not at.exception
    assert any(message in e.value for e in at.error)


def test_syntax_error_in_pasted_code_does_not_crash(monkeypatch):
    _fake_model(monkeypatch, diagnosis(), patch("a - b", "a + b"), quality())
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    _paste(at, code="def add(a, b)\n    return a - b\n")
    _button(at, "Start debugging").click().run()
    assert not at.exception
    assert any("error" in m.value.lower() for m in at.markdown if "Before any changes" in m.value)


def test_start_disabled_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(coach.llm, "local_models", lambda: None)
    monkeypatch.setattr(coach.llm, "llm_status", lambda *a: (False, "Ollama is not running."))
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert _button(at, "Start debugging").disabled
    assert any("Ollama is not running." in e.value for e in at.error)
