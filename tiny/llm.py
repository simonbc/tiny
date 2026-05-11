from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResponse:
    """Provider-neutral wrapper around a single model response.

    `content` is a list of blocks, each either
      {"type": "text", "text": str} or
      {"type": "tool_use", "id": str, "name": str, "input": dict}.
    """

    content: list[dict[str, Any]]
    stop_reason: str = "end_turn"


class LLMClient(Protocol):
    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


class AnthropicClient:
    """Thin wrapper around the Anthropic SDK that returns LLMResponse."""

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, *, api_key: str | None = None, model: str | None = None):
        from anthropic import Anthropic

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env, fill in "
                "your key, and restart the server (or `set -a; source .env; set +a`)."
            )
        self._client = Anthropic(api_key=key)
        self._model = model or self.DEFAULT_MODEL

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        )
        content: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        return LLMResponse(content=content, stop_reason=response.stop_reason)
