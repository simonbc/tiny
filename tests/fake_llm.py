from __future__ import annotations

import copy
from typing import Any

from tiny.llm import LLMResponse


class FakeLLMClient:
    """Scripted LLM client. Returns prepared responses in order."""

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create_message(self, *, system, messages, tools) -> LLMResponse:
        self.calls.append({"system": system, "messages": copy.deepcopy(messages), "tools": tools})
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


def tool_use(id_: str, name: str, input_: dict) -> dict:
    return {"type": "tool_use", "id": id_, "name": name, "input": input_}


def text(value: str) -> dict:
    return {"type": "text", "text": value}
