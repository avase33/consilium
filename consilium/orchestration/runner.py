"""ResearchRunner — assembles the system and executes a research run.

Owns provider, search backend, cache, agents, the compiled workflow, and the
persistence store. Exposes both a one-shot ``run`` and a ``stream`` that yields an
event after every graph node so a UI can show live progress.
"""

from __future__ import annotations

from typing import AsyncIterator

from ..agents import Analyst, Critic, Researcher, Supervisor
from ..config import Settings
from ..llm import get_provider
from ..logging_setup import get_logger
from ..memory import NullCache, RunStore, SqliteCache
from ..models import ResearchState, RunStatus
from ..tools import ToolRegistry, get_search_backend, make_web_search_tool
from .workflow import build_workflow

log = get_logger("runner")


class ResearchRunner:
    def __init__(self, settings: Settings | None = None, store: RunStore | None = None):
        self.settings = settings or Settings.from_env()
        self.provider = get_provider(self.settings.provider)

        cache = SqliteCache("consilium-cache.db") if self.settings.cache_enabled else NullCache()
        backend = get_search_backend(self.settings.search_backend)
        self.tools = ToolRegistry()
        self.tools.register(make_web_search_tool(backend, cache))

        self.supervisor = Supervisor(self.provider, self.settings)
        self.researcher = Researcher(self.provider, self.settings, self.tools)
        self.analyst = Analyst(self.provider, self.settings)
        self.critic = Critic(self.provider, self.settings)

        self.graph = build_workflow(
            self.supervisor, self.researcher, self.analyst, self.critic, self.settings
        )
        self.store = store or RunStore(self.settings.db_path)

    def _new_state(self, topic: str, depth: str) -> ResearchState:
        return ResearchState(topic=topic, depth=depth, max_iterations=self.settings.max_iterations)

    async def run(self, topic: str, depth: str = "standard") -> ResearchState:
        state = self._new_state(topic, depth)
        log.info("Starting research run %s: %r", state.run_id, topic)
        try:
            state = await self.graph.invoke(state)
        except Exception as exc:  # noqa: BLE001
            state.status = RunStatus.FAILED
            state.error = str(exc)
            log.exception("Run %s failed", state.run_id)
        self.store.save(state)
        return state

    async def stream(self, topic: str, depth: str = "standard") -> AsyncIterator[tuple[str, ResearchState]]:
        state = self._new_state(topic, depth)
        try:
            async for node, state in self.graph.stream(state):
                yield node, state
        except Exception as exc:  # noqa: BLE001
            state.status = RunStatus.FAILED
            state.error = str(exc)
            log.exception("Run %s failed", state.run_id)
        self.store.save(state)

    def cost_usd(self, state: ResearchState) -> float:
        return state.usage.cost_usd(
            self.settings.price_prompt_per_1k, self.settings.price_completion_per_1k
        )
