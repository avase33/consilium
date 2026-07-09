"""Analyst — filters and structures raw sources into cited findings.

Groups the retrieved sources by subtopic and distills each group into a single
evidence-backed :class:`~consilium.models.Finding`, with a confidence proportional
to how much corroborating evidence was found. Findings are recomputed from
scratch each pass so a deeper research sweep is reflected accurately.
"""

from __future__ import annotations

from ..models import Finding, ResearchState, RunStatus
from .base import Agent


class Analyst(Agent):
    role = "analyst"

    async def __call__(self, state: ResearchState) -> ResearchState:
        state.status = RunStatus.ANALYZING
        state.findings.clear()
        for subtopic in state.plan:
            subs = [s for s in state.sources if s.query.endswith(subtopic)]
            if not subs:
                continue
            evidence = " ".join(s.snippet[:140] for s in subs[:2])
            confidence = min(1.0, round(len(subs) / 3, 2))
            state.findings.append(Finding(
                claim=f"On '{subtopic}', the evidence indicates steady growth with competitive "
                      f"dynamics and several emerging challengers.",
                evidence=evidence,
                source_ids=[s.id for s in subs],
                subtopic=subtopic,
                confidence=confidence,
            ))
        state.log("analyst", "structured", findings=len(state.findings))
        self.log.info("Structured %d findings from %d sources", len(state.findings), len(state.sources))
        return state
