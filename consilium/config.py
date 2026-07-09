"""Runtime configuration, resolved from environment variables.

Offline-first: with nothing set, Consilium uses the deterministic mock LLM and
mock search backend, so the full pipeline runs and tests pass with no API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    return default if val is None else val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # LLM
    provider: str = "mock"            # mock | anthropic | openai
    model: str = ""
    temperature: float = 0.3
    request_timeout: int = 60

    # Search
    search_backend: str = "mock"      # mock | tavily | http
    search_api_key: str = ""

    # Orchestration
    orchestrator: str = "builtin"     # builtin | langgraph
    max_iterations: int = 2
    critique_threshold: float = 7.0
    subtopics: int = 4
    results_per_query: int = 4

    # Infra
    db_path: str = "consilium.db"
    cache_enabled: bool = True
    log_level: str = "INFO"
    log_json: bool = False

    # Cost accounting (USD per 1K tokens; rough defaults, override via env)
    price_prompt_per_1k: float = 0.003
    price_completion_per_1k: float = 0.015

    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.environ.get("CONSILIUM_PROVIDER")
        if not provider:
            if os.environ.get("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
            else:
                provider = "mock"

        search_backend = os.environ.get("CONSILIUM_SEARCH", "")
        if not search_backend:
            search_backend = "tavily" if os.environ.get("TAVILY_API_KEY") else "mock"

        return cls(
            provider=provider,
            model=os.environ.get("CONSILIUM_MODEL", ""),
            temperature=float(os.environ.get("CONSILIUM_TEMPERATURE", "0.3")),
            search_backend=search_backend,
            search_api_key=os.environ.get("TAVILY_API_KEY", ""),
            orchestrator=os.environ.get("CONSILIUM_ORCHESTRATOR", "builtin"),
            max_iterations=int(os.environ.get("CONSILIUM_MAX_ITERATIONS", "2")),
            critique_threshold=float(os.environ.get("CONSILIUM_CRITIQUE_THRESHOLD", "7.0")),
            subtopics=int(os.environ.get("CONSILIUM_SUBTOPICS", "4")),
            results_per_query=int(os.environ.get("CONSILIUM_RESULTS_PER_QUERY", "4")),
            db_path=os.environ.get("CONSILIUM_DB", "consilium.db"),
            cache_enabled=_env_bool("CONSILIUM_CACHE", True),
            log_level=os.environ.get("CONSILIUM_LOG_LEVEL", "INFO"),
            log_json=_env_bool("CONSILIUM_LOG_JSON", False),
        )
