"""Thin wrappers around the AI model.

The rest of the coach talks to an `LLM` object with two methods, so the model
can be swapped (a free local model through Ollama, or the paid Claude API) and
tests can use a scripted fake without touching the network.
"""
import json
import os
from typing import Protocol, TypeVar

import anthropic
import requests
from pydantic import BaseModel, ValidationError

from coach import config

T = TypeVar("T", bound=BaseModel)

# Server-side fallback: if a safety classifier declines a request, the API
# retries it on a fallback model inside the same call.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(Exception):
    """A model call failed in a way the user should be told about."""


class LLM(Protocol):
    def structured(self, *, system: str, prompt: str, schema: type[T]) -> T: ...

    def chat(self, *, system: str, messages: list[dict]) -> str: ...


def api_key_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def local_models() -> list[str] | None:
    """Names of the models downloaded in Ollama, or None if Ollama is not running."""
    try:
        models = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3).json().get("models", [])
    except (requests.RequestException, ValueError):
        return None
    return sorted(m["name"].removesuffix(":latest") for m in models if m.get("name"))


def llm_status(model: str | None = None) -> tuple[bool, str]:
    """Whether the model can be used right now, and a message for the user."""
    model = model or config.MODEL
    if config.PROVIDER == "claude":
        if api_key_available():
            return True, "Anthropic API key found"
        return False, "No Anthropic API key. Add one to `.env`, or set COACH_PROVIDER=ollama to use a free local model."
    if config.PROVIDER != "ollama":
        return False, f"Unknown COACH_PROVIDER {config.PROVIDER!r}. Use 'ollama' or 'claude'."
    names = local_models()
    if names is None:
        return False, "Ollama is not running. Start it with `ollama serve` (see README setup)."
    if model.removesuffix(":latest") not in names:
        return False, f"Model `{model}` is not downloaded. Run `ollama pull {model}`."
    return True, f"Local model ready: {model}"


def create_llm(model: str | None = None) -> "LLM":
    if config.PROVIDER == "claude":
        return ClaudeLLM(model or config.MODEL)
    return OllamaLLM(model or config.MODEL)


class OllamaLLM:
    """A free, open model running on this computer through Ollama (https://ollama.com).

    Ollama constrains the output to the JSON schema; Pydantic then validates it.
    Small models occasionally return values that fail validation, so the error is
    sent back once and the model gets one chance to correct itself.
    """

    def __init__(self, model: str = config.MODEL, url: str = config.OLLAMA_URL):
        self.model = model
        self.url = url

    def structured(self, *, system: str, prompt: str, schema: type[T]) -> T:
        json_schema = schema.model_json_schema()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{prompt}\n\nReply with JSON matching this schema:\n"
                                        f"{json.dumps(json_schema)}"},
        ]
        for _ in range(2):
            content = self._chat(messages, json_schema)
            try:
                return schema.model_validate_json(content)
            except ValidationError as e:
                messages += [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That JSON was invalid:\n{e}\nReply with corrected JSON only."},
                ]
        raise LLMError("The model's answer did not match the expected format.")

    def chat(self, *, system: str, messages: list[dict]) -> str:
        return self._chat([{"role": "system", "content": system}, *messages]).strip()

    def _chat(self, messages: list[dict], json_schema: dict | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": config.OLLAMA_CONTEXT_TOKENS},
        }
        if json_schema:
            payload["format"] = json_schema
        try:
            response = requests.post(f"{self.url}/api/chat", json=payload, timeout=config.LOCAL_TIMEOUT_SECONDS)
        except requests.ConnectionError as e:
            raise LLMError("Could not reach Ollama. Start it with `ollama serve`.") from e
        except requests.Timeout as e:
            raise LLMError("The local model took too long to answer.") from e
        if response.status_code == 404:
            raise LLMError(f"Model `{self.model}` is not downloaded. Run `ollama pull {self.model}`.")
        if not response.ok:
            raise LLMError(f"Ollama returned an error ({response.status_code}).")
        data = response.json()
        if data.get("done_reason") == "length":
            raise LLMError("The model's answer was cut off because it was too long.")
        return data["message"]["content"]


class ClaudeLLM:
    def __init__(self, model: str = config.MODEL, effort: str = config.EFFORT):
        self.model = model
        self.effort = effort
        self._client = anthropic.Anthropic(timeout=config.API_TIMEOUT_SECONDS, max_retries=2)

    def _request_args(self, system: str, messages: list[dict]) -> dict:
        return dict(
            model=self.model,
            max_tokens=config.MAX_OUTPUT_TOKENS,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            betas=[_FALLBACK_BETA],
            fallbacks="default",
        )

    def structured(self, *, system: str, prompt: str, schema: type[T]) -> T:
        args = self._request_args(system, [{"role": "user", "content": prompt}])
        response = self._call(lambda: self._client.beta.messages.parse(output_format=schema, **args))
        self._check_stop_reason(response)
        if response.parsed_output is None:
            raise LLMError("The model's answer did not match the expected format.")
        return response.parsed_output

    def chat(self, *, system: str, messages: list[dict]) -> str:
        response = self._call(
            lambda: self._client.beta.messages.create(**self._request_args(system, messages))
        )
        self._check_stop_reason(response)
        return "".join(block.text for block in response.content if block.type == "text").strip()

    @staticmethod
    def _check_stop_reason(response) -> None:
        if response.stop_reason == "refusal":
            raise LLMError("The model declined to answer this request.")
        if response.stop_reason == "max_tokens":
            raise LLMError("The model's answer was cut off because it was too long.")

    @staticmethod
    def _call(fn):
        try:
            return fn()
        except anthropic.AuthenticationError as e:
            raise LLMError("The Anthropic API key is missing or invalid.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Rate limited by the Anthropic API. Wait a moment and try again.") from e
        except anthropic.BadRequestError as e:
            raise LLMError(f"The API rejected the request: {e.message}") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"The Anthropic API returned an error ({e.status_code}).") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Could not reach the Anthropic API. Check your connection.") from e
