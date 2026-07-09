"""Supervisor — plans the research and writes the final report.

The supervisor bookends the workflow: first it decomposes the topic into research
questions (the plan), and at the end it synthesizes the reviewed findings into a
structured, cited report. Routing/hand-off decisions live in the workflow graph.
"""

from __future__ import annotations

import re

from ..models import Report, ReportSection, ResearchState, RunStatus
from .base import Agent

_PLAN_SYS = "You are a research director. Decompose a topic into distinct, non-overlapping research questions."
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")


class Supervisor(Agent):
    role = "supervisor"

    async def plan(self, state: ResearchState) -> ResearchState:
        state.status = RunStatus.PLANNING
        prompt = (
            f"[[TASK:PLAN]] [[TOPIC:{state.topic}]] [[N:{self.settings.subtopics}]]\n"
            f"List the {self.settings.subtopics} key subtopics to research for: {state.topic}"
        )
        text = await self._think(_PLAN_SYS, prompt, state)
        plan = [m.group(1).strip() for line in text.splitlines() if (m := _NUMBERED.match(line))]
        if not plan:
            plan = [ln.strip() for ln in text.splitlines() if ln.strip()][: self.settings.subtopics]
        state.plan = plan or [state.topic]
        state.log("supervisor", "plan_created", subtopics=state.plan)
        self.log.info("Planned %d subtopics for %r", len(state.plan), state.topic)
        return state

    async def write_report(self, state: ResearchState) -> ResearchState:
        state.status = RunStatus.WRITING
        summary = await self._think(
            "You are a research director writing an executive summary.",
            f"[[TASK:SUMMARY]] [[TOPIC:{state.topic}]]\nWrite a 4-6 sentence executive summary "
            f"based on {len(state.findings)} findings across {len(state.plan)} subtopics.",
            state, max_tokens=400,
        )

        sections: list[ReportSection] = []
        for subtopic in state.plan:
            sub_findings = [f for f in state.findings if f.subtopic == subtopic]
            if not sub_findings:
                continue
            body = await self._think(
                "You write a concise, evidence-grounded report section.",
                f"[[TASK:SECTION]] [[TOPIC:{state.topic}]]\nSubtopic: {subtopic}\n"
                + "\n".join(f"- {f.claim} ({f.evidence[:120]})" for f in sub_findings),
                state, max_tokens=300,
            )
            citations = sorted({sid for f in sub_findings for sid in f.source_ids})
            bullet = "\n".join(f"- {f.claim}" for f in sub_findings)
            sections.append(ReportSection(heading=subtopic, content=f"{body}\n\n{bullet}", citations=citations))

        state.report = Report(
            topic=state.topic,
            executive_summary=summary.strip(),
            sections=sections,
            sources=state.sources,
        )
        state.status = RunStatus.COMPLETED
        state.log("supervisor", "report_written", sections=len(sections))
        self.log.info("Report written: %d sections, %d sources", len(sections), len(state.sources))
        return state
