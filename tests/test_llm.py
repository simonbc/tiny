import pytest

from tiny.llm import AnthropicClient


def test_anthropic_client_raises_helpful_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicClient()
