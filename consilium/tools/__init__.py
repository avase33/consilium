"""Tools: JSON-schema tool abstraction + pluggable web search."""

from .base import Tool, ToolRegistry, tool
from .web_search import (
    MockSearchBackend,
    SearchBackend,
    TavilyBackend,
    get_search_backend,
    make_web_search_tool,
)

__all__ = [
    "Tool",
    "ToolRegistry",
    "tool",
    "SearchBackend",
    "MockSearchBackend",
    "TavilyBackend",
    "get_search_backend",
    "make_web_search_tool",
]
