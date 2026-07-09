"""Optional adapter that builds the same research workflow on real LangGraph.

Enabled with ``CONSILIUM_ORCHESTRATOR=langgraph`` (requires ``pip install
langgraph``). This keeps Consilium honest about the ecosystem while the built-in
engine guarantees the project runs with zero dependencies. The node functions
are identical — only the graph runtime differs.
"""

from __future__ import annotations

from typing import Any


def build_langgraph_app(nodes: dict[str, Any], entry: str, router_map: dict[str, Any]):  # pragma: no cover
    """Construct a LangGraph ``StateGraph`` from the same node callables.

    ``router_map`` maps a source node to a ``(router, {label: dest})`` pair for
    conditional edges; plain strings are treated as static edges.
    """
    try:
        from langgraph.graph import END as LG_END
        from langgraph.graph import StateGraph as LGStateGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "CONSILIUM_ORCHESTRATOR=langgraph requires the 'langgraph' package. "
            "Install it with: pip install langgraph"
        ) from exc

    graph = LGStateGraph(dict)
    for name, fn in nodes.items():
        graph.add_node(name, fn)
    graph.set_entry_point(entry)

    for src, spec in router_map.items():
        if isinstance(spec, str):
            graph.add_edge(src, LG_END if spec == "__end__" else spec)
        else:
            router, mapping = spec
            mapping = {k: (LG_END if v == "__end__" else v) for k, v in mapping.items()}
            graph.add_conditional_edges(src, router, mapping)

    return graph.compile()
