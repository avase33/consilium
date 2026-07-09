import asyncio

import pytest

from consilium.errors import GraphError
from consilium.graph import END, StateGraph


def test_linear_graph_runs_in_order():
    async def main():
        g: StateGraph[dict] = StateGraph()

        async def a(s):
            s["path"].append("a")
            return s

        async def b(s):
            s["path"].append("b")
            return s

        g.add_node("a", a).add_node("b", b).set_entry_point("a")
        g.add_edge("a", "b").add_edge("b", END)
        return await g.compile().invoke({"path": []})

    assert asyncio.run(main())["path"] == ["a", "b"]


def test_conditional_loop_terminates():
    async def main():
        g: StateGraph[dict] = StateGraph()

        async def step(s):
            s["count"] += 1
            return s

        async def gate(s):
            return s

        g.add_node("step", step).add_node("gate", gate).set_entry_point("step")
        g.add_edge("step", "gate")
        g.add_conditional_edges("gate", lambda s: END if s["count"] >= 3 else "step")
        return await g.compile().invoke({"count": 0})

    assert asyncio.run(main())["count"] == 3


def test_stream_yields_each_node():
    async def main():
        g: StateGraph[dict] = StateGraph()
        async def a(s): return s
        g.add_node("a", a).set_entry_point("a").add_edge("a", END)
        seen = []
        async for node, _state in g.compile().stream({}):
            seen.append(node)
        return seen

    assert asyncio.run(main()) == ["a"]


def test_sync_node_rejected():
    g: StateGraph[dict] = StateGraph()
    with pytest.raises(GraphError):
        g.add_node("bad", lambda s: s)  # not async
