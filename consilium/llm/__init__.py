"""LLM provider layer."""

from __future__ import annotations

from ..config import Settings
from .base import LLMProvider
from .mock import MockLLM


def get_provider(name: str | None = None, **kwargs) -> LLMProvider:
    name = (name or Settings.from_env().provider or "mock").lower()
    if name in ("mock", "offline"):
        return MockLLM()
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(**kwargs)
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(**kwargs)
    raise ValueError(f"Unknown provider: {name!r}")


__all__ = ["LLMProvider", "MockLLM", "get_provider"]
