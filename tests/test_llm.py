"""The local Ollama client and model-availability checks, with the HTTP calls faked."""
import pytest
import requests

from coach import config, llm
from coach.llm import LLMError, OllamaLLM, llm_status
from coach.schemas import QualityReview
from conftest import quality

GOOD = quality().model_dump_json()


class FakeResponse:
    def __init__(self, status=200, content="", done_reason="stop", json_body=None):
        self.status_code = status
        self.ok = status < 400
        self._body = json_body if json_body is not None else {
            "message": {"content": content}, "done_reason": done_reason}

    def json(self):
        return self._body


def fake_post(monkeypatch, *responses):
    """Make requests.post return `responses` in order and record each payload."""
    queue, payloads = list(responses), []

    def post(url, json, timeout):
        payloads.append(json)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm.requests, "post", post)
    return payloads


def test_structured_sends_schema_and_parses(monkeypatch):
    payloads = fake_post(monkeypatch, FakeResponse(content=GOOD))
    result = OllamaLLM(model="m").structured(system="sys", prompt="review", schema=QualityReview)
    assert result == quality()
    assert payloads[0]["format"] == QualityReview.model_json_schema()
    assert payloads[0]["options"]["temperature"] == 0
    assert payloads[0]["messages"][0] == {"role": "system", "content": "sys"}


def test_invalid_json_gets_one_correction(monkeypatch):
    payloads = fake_post(monkeypatch, FakeResponse(content='{"issues": "oops"}'), FakeResponse(content=GOOD))
    assert OllamaLLM(model="m").structured(system="s", prompt="p", schema=QualityReview) == quality()
    assert "invalid" in payloads[1]["messages"][-1]["content"]


def test_gives_up_after_second_invalid_answer(monkeypatch):
    fake_post(monkeypatch, FakeResponse(content="{}"), FakeResponse(content="{}"))
    with pytest.raises(LLMError, match="expected format"):
        OllamaLLM(model="m").structured(system="s", prompt="p", schema=QualityReview)


@pytest.mark.parametrize("response, message", [
    (requests.ConnectionError(), "ollama serve"),
    (FakeResponse(status=404), "ollama pull m"),
    (FakeResponse(content="...", done_reason="length"), "cut off"),
])
def test_errors_become_friendly_messages(monkeypatch, response, message):
    fake_post(monkeypatch, response)
    with pytest.raises(LLMError, match=message):
        OllamaLLM(model="m").chat(system="s", messages=[{"role": "user", "content": "hi"}])


def test_status_reports_missing_model_and_ready(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "ollama")
    monkeypatch.setattr(config, "MODEL", "qwen2.5-coder:7b")
    tags = {"models": [{"name": "llama3:latest"}]}
    monkeypatch.setattr(llm.requests, "get", lambda url, timeout: FakeResponse(json_body=tags))
    ready, message = llm_status()
    assert not ready and "ollama pull qwen2.5-coder:7b" in message

    tags["models"].append({"name": "qwen2.5-coder:7b"})
    assert llm_status()[0]


def test_status_when_ollama_not_running(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "ollama")

    def refuse(url, timeout):
        raise requests.ConnectionError()

    monkeypatch.setattr(llm.requests, "get", refuse)
    assert llm_status() == (False, "Ollama is not running. Start it with `ollama serve` (see README setup).")


def test_status_for_claude_needs_api_key(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert not llm_status()[0]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert llm_status()[0]
