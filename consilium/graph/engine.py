"""A tiny, typed, async state-graph engine — the orchestration core.

This is a LangGraph-style API: you register async **nodes** that transform a
shared state object, connect them with static or **conditional** edges, compile,
then ``invoke`` or ``stream`` the graph. Conditional edges are what make
multi-agent routing and revise-loops possible.

A real ``langgraph`` adapter lives in ``langgraph_adapter.py``; this built-in
engine keeps the project dependency-free and fully testable offline.
"""

from __future__ import annotations

import inspect
from typing import Any, AsyncIterator, Awaitable, Callable, Generic, TypeVar

from ..errors import GraphError

S = TypeVar("S")

END = "__end__"

Node = Callable[[S], Awaitable[Any]]
Router = Callable[[S], str]


class StateGraph(Generic[S]):
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, str] = {}
        self._conditional: dict[str, Router] = {}
        self._entry: str | None = None

    def add_node(self, name: str, fn: Node) -> "StateGraph[S]":
        if name in (END,):
            raise GraphError(f"'{name}' is a reserved node name")
        if not inspect.iscoroutinefunction(fn):
            raise GraphError(f"node '{name}' must be an async function")
        self._nodes[name] = fn
        return self

    def set_entry_point(self, name: str) -> "StateGraph[S]":
        self._entry = name
        return self

    def add_edge(self, src: str, dst: str) -> "StateGraph[S]":
        self._edges[src] = dst
        return self

    def add_conditional_edges(self, src: str, router: Router) -> "StateGraph[S]":
        self._conditional[src] = router
        return self

    def compile(self) -> "CompiledGraph[S]":
        if self._entry is None:
            raise GraphError("no entry point set")
        if self._entry not in self._nodes:
            raise GraphError(f"entry point '{self._entry}' is not a registered node")
        return CompiledGraph(self._nodes, self._edges, self._conditional, self._entry)


class CompiledGraph(Generic[S]):
    def __init__(self, nodes, edges, conditional, entry, max_steps: int = 100):
        self._nodes = nodes
        self._edges = edges
        self._conditional = conditional
        self._entry = entry
        self.max_steps = max_steps

    def _next(self, name: str, state: S) -> str:
        if name in self._conditional:
            return self._conditional[name](state)
        return self._edges.get(name, END)

    async def stream(self, state: S) -> AsyncIterator[tuple[str, S]]:
        """Run the graph, yielding ``(node_name, state)`` after each node."""
        current = self._entry
        steps = 0
        while current != END:
            if steps >= self.max_steps:
                raise GraphError(f"graph exceeded {self.max_steps} steps (cycle?)")
            steps += 1
            node = self._nodes.get(current)
            if node is None:
                raise GraphError(f"unknown node '{current}'")
            result = await node(state)
            if result is not None:
                state = result  # nodes may mutate-in-place or return a new state
            yield current, state
            current = self._next(current, state)

    async def invoke(self, state: S) -> S:
        async for _node, state in self.stream(state):
            pass
        return state
