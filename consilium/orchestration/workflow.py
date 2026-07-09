"""Wires the agents into the research state-graph.

    plan → research → analyze → critique ─┬─(passed / budget spent)→ write → END
                          ▲                │
                          └──(gaps found)──┘   revise loop
"""

from __future__ import annotations

from ..agents import Analyst, Critic, Researcher, Supervisor
from ..config import Settings
from ..graph import END, CompiledGraph, StateGraph
from ..models import ResearchState


def build_workflow(
    supervisor: Supervisor,
    researcher: Researcher,
    analyst: Analyst,
    critic: Critic,
    settings: Settings,
) -> CompiledGraph[ResearchState]:
    graph: StateGraph[ResearchState] = StateGraph()

    graph.add_node("plan", supervisor.plan)
    graph.add_node("research", researcher.__call__)
    graph.add_node("analyze", analyst.__call__)
    graph.add_node("critique", critic.__call__)
    graph.add_node("write", supervisor.write_report)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "analyze")
    graph.add_edge("analyze", "critique")
    graph.add_edge("write", END)

    def route_after_critique(state: ResearchState) -> str:
        last = state.critiques[-1] if state.critiques else None
        if last is not None and last.passed:
            return "write"
        if state.iteration + 1 >= state.max_iterations:
            state.log("supervisor", "budget_exhausted", iteration=state.iteration)
            return "write"  # graceful stop: write with what we have
        state.iteration += 1
        state.log("supervisor", "revise", iteration=state.iteration, gaps=last.gaps if last else [])
        return "research"

    graph.add_conditional_edges("critique", route_after_critique)
    return graph.compile()
