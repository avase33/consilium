"""Pluggable web-search tool.

``SearchBackend`` is the interface; ``MockSearchBackend`` returns deterministic
synthetic results so the pipeline runs fully offline, and ``TavilyBackend`` calls
a real search API when a key is configured. Results are optionally cached.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

from ..errors import SearchError
from ..models import Source
from .base import Tool, tool


class SearchBackend(ABC):
    name: str = "base"

    @abstractmethod
    async def search(self, query: str, k: int = 4) -> list[Source]:
        ...


class MockSearchBackend(SearchBackend):
    """Deterministic offline search — reproducible synthetic sources per query."""

    name = "mock"
    _DOMAINS = ["marketwatch.example", "techcrunch.example", "statista.example",
                "reuters.example", "gartner.example", "crunchbase.example"]

    async def search(self, query: str, k: int = 4) -> list[Source]:
        seed = int(hashlib.md5(query.encode()).hexdigest(), 16)
        out: list[Source] = []
        for i in range(k):
            domain = self._DOMAINS[(seed + i) % len(self._DOMAINS)]
            slug = urllib.parse.quote_plus(query.lower())[:60]
            out.append(Source(
                title=f"{query.strip().title()} — analysis {i + 1}",
                url=f"https://{domain}/{slug}-{i + 1}",
                snippet=(
                    f"Industry coverage of {query}: the segment shows steady growth with several "
                    f"established players and emerging challengers competing on price and product. "
                    f"Recent figures indicate continued expansion, though margins and regulation "
                    f"remain watch items."
                ),
                query=query,
                score=round(1.0 - i * 0.12, 3),
            ))
        return out


class TavilyBackend(SearchBackend):  # pragma: no cover - network
    name = "tavily"
    _URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise SearchError("TAVILY_API_KEY is not set")
        self.timeout = timeout

    def _call(self, query: str, k: int) -> list[Source]:
        payload = {"api_key": self.api_key, "query": query, "max_results": k,
                   "search_depth": "advanced"}
        req = urllib.request.Request(
            self._URL, data=json.dumps(payload).encode(),
            headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        return [
            Source(title=r.get("title", ""), url=r.get("url", ""),
                   snippet=r.get("content", "")[:600], query=query, score=r.get("score", 0.0))
            for r in body.get("results", [])
        ]

    async def search(self, query: str, k: int = 4) -> list[Source]:
        try:
            return await asyncio.to_thread(self._call, query, k)
        except Exception as exc:  # noqa: BLE001
            raise SearchError(f"Tavily search failed: {exc}") from exc


def get_search_backend(name: str = "mock", **kwargs) -> SearchBackend:
    name = (name or "mock").lower()
    if name == "mock":
        return MockSearchBackend()
    if name == "tavily":
        return TavilyBackend(**kwargs)
    raise SearchError(f"unknown search backend: {name!r}")


def make_web_search_tool(backend: SearchBackend, cache=None) -> Tool:
    """Wrap a backend as a schema-carrying ``web_search`` tool (with optional cache)."""

    @tool(name="web_search", description="Search the web for a query and return titled results with snippets and URLs.")
    async def web_search(query: str, k: int = 4) -> list[dict]:
        if cache is not None:
            cached = cache.get("search", query, k)
            if cached is not None:
                return cached
        results = await backend.search(query, k)
        payload = [s.to_dict() for s in results]
        if cache is not None:
            cache.set("search", payload, query, k)
        return payload

    return web_search
