"""Researcher — gathers evidence with the web-search tool.

On the first pass it does a shallow sweep; if the Critic sends the team back, it
deepens the search (more results per query) for the subtopics flagged as gaps.
New sources are de-duplicated by URL.
"""

from __future__ import annotations

from ..models import ResearchState, RunStatus, Source
from ..tools.base import ToolRegistry
from .base import Agent


class Researcher(Agent):
    role = "researcher"

    def __init__(self, provider, settings, tools: ToolRegistry):
        super().__init__(provider, settings)
        self.tools = tools

    async def __call__(self, state: ResearchState) -> ResearchState:
        state.status = RunStatus.RESEARCHING
        # Shallow on the first pass, deeper on any revise pass.
        k = 2 if state.iteration == 0 else self.settings.results_per_query
        seen_urls = {s.url for s in state.sources}
        added = 0
        for subtopic in state.plan:
            query = f"{state.topic} {subtopic}"
            results = await self.tools.call("web_search", query=query, k=k)
            for r in results:
                if r["url"] in seen_urls:
                    continue
                seen_urls.add(r["url"])
                state.sources.append(Source(
                    title=r["title"], url=r["url"], snippet=r["snippet"],
                    query=query, score=r.get("score", 0.0), id=r["id"],
                ))
                added += 1
        state.log("researcher", "searched", pass_k=k, sources_added=added, total=len(state.sources))
        self.log.info("Gathered %d new sources (k=%d), %d total", added, k, len(state.sources))
        return state
