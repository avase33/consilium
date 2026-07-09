"""Async LLM provider interface.

Agents build a system + user prompt and call ``complete``; providers return the
text plus token usage. Keeping the surface tiny makes every agent trivially
mockable and every provider a ~40-line adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Usage


class LLMProvider(ABC):
    name: str = "base"
    default_model: str = ""

    @abstractmethod
    async def complete(
        self, system: str, prompt: str, *, temperature: float | None = None, max_tokens: int = 1024
    ) -> tuple[str, Usage]:
        """Return ``(text, usage)`` for a single-turn system+user prompt."""
