"""Base class shared by the specialized agents."""

from __future__ import annotations

from ..config import Settings
from ..llm.base import LLMProvider
from ..logging_setup import get_logger
from ..models import ResearchState, Usage


class Agent:
    role: str = "agent"

    def __init__(self, provider: LLMProvider, settings: Settings):
        self.provider = provider
        self.settings = settings
        self.log = get_logger(self.role)

    async def _think(self, system: str, prompt: str, state: ResearchState, max_tokens: int = 512) -> str:
        text, usage = await self.provider.complete(
            system, prompt, temperature=self.settings.temperature, max_tokens=max_tokens
        )
        state.usage = state.usage + usage
        return text

    async def __call__(self, state: ResearchState) -> ResearchState:  # pragma: no cover - overridden
        raise NotImplementedError
