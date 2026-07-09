"""Tools with auto-generated JSON schemas.

The ``@tool`` decorator turns a typed (async) function into a ``Tool`` carrying a
JSON schema for its arguments — the exact shape an LLM function-calling API
expects. A ``ToolRegistry`` exposes those schemas and safely dispatches calls.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..errors import ToolError

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


def _schema(fn: Callable) -> dict[str, Any]:
    props, required = {}, []
    for name, p in inspect.signature(fn).parameters.items():
        if name in ("self", "cls"):
            continue
        props[name] = {"type": _JSON_TYPES.get(p.annotation, "string")}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": props, "required": required}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Awaitable[Any]]

    async def run(self, **kwargs: Any) -> Any:
        allowed = set(self.parameters.get("properties", {}))
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}
        try:
            return await self.func(**kwargs)
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolError(f"tool '{self.name}' failed: {exc}") from exc

    def schema(self) -> dict[str, Any]:
        """OpenAI/Anthropic-style function schema."""
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


def tool(fn: Callable | None = None, *, name: str | None = None, description: str | None = None):
    def wrap(f: Callable) -> Tool:
        if not inspect.iscoroutinefunction(f):
            raise ToolError(f"tool '{f.__name__}' must be async")
        return Tool(name or f.__name__, (description or inspect.getdoc(f) or "").strip(), _schema(f), f)

    return wrap(fn) if fn else wrap


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, t: Tool) -> Tool:
        self.tools[t.name] = t
        return t

    def get(self, name: str) -> Tool:
        if name not in self.tools:
            raise ToolError(f"no tool named '{name}'")
        return self.tools[name]

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    async def call(self, name: str, **kwargs: Any) -> Any:
        return await self.get(name).run(**kwargs)
