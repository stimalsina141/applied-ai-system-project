"""Thin wrapper around the Claude API.

The rest of the coach talks to an `LLM` object with two methods, so tests can
swap in a scripted fake without touching the network.
"""
import os
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

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
