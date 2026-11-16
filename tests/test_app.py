"""Drive the Streamlit UI headlessly with a scripted model."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import coach.llm
from conftest import CALC, CALC_TESTS, ScriptedLLM, diagnosis, patch, quality

APP = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    llm = ScriptedLLM(diagnosis(), patch("a - b", "a + b"), quality(), "Minus subtracts.")
    monkeypatch.setattr(coach.llm, "ClaudeLLM", lambda *a, **k: llm)
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    return at


def _button(at, label):
    return next(b for b in at.button if b.label.startswith(label))


def test_review_mode_end_to_end(app):
    at = app
    at.radio[0].set_value("Paste my own code").run()
    at.text_input[0].set_value("calc.py")
    at.text_area[0].set_value(CALC)
    at.text_area[1].set_value(CALC_TESTS)
    at.text_area[3].set_value("add(2, 3) gives -1")
    _button(at, "Start debugging").click().run()

    assert not at.exception
    headers = [h.value for h in at.header]
    assert "2. Diagnosis" in headers and "3. Explanation" in headers

    _button(at, "Propose a fix").click().run()
    assert any("+    return a + b" in c.value for c in at.code)
    assert any("Nothing has run yet" in i.value for i in at.info)

    _button(at, "✅ Approve").click().run()
    assert not at.exception
    assert any("Fixed" in s.value for s in at.success)
    assert "5. Report" in [h.value for h in at.header]

    at.chat_input[0].set_value("Why?").run()
    assert any("Minus subtracts." in m.markdown[0].value for m in at.chat_message)


def test_start_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert _button(at, "Start debugging").disabled
