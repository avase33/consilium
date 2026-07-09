"""Critic — the quality gate.

Grades the current findings on evidence coverage and flags gaps. If the score is
below threshold (and iteration budget remains), the workflow routes the team back
to the Researcher to deepen the weak areas; otherwise it proceeds to writing.
"""

from __future__ import annotations

from ..models import Critique, ResearchState, RunStatus
from .base import Agent

_MIN_SOURCES = 3


class Critic(Agent):
    role = "critic"

    async def __call__(self, state: ResearchState) -> ResearchState:
        state.status = RunStatus.REVIEWING
        total = len(state.plan) or 1
        gaps: list[str] = []
        well_covered = 0
        for subtopic in state.plan:
            n = sum(1 for s in state.sources if s.query.endswith(subtopic))
            if n >= _MIN_SOURCES:
                well_covered += 1
            else:
                gaps.append(subtopic)

        score = round(10 * well_covered / total, 1)
        notes = await self._think(
            "You are a rigorous research critic.",
            f"[[TASK:CRITIQUE]] [[TOPIC:{state.topic}]]\n"
            f"{well_covered}/{total} subtopics are well-sourced. Gaps: {gaps or 'none'}.",
            state, max_tokens=200,
        )
        passed = score >= self.settings.critique_threshold and not gaps
        critique = Critique(score=score, passed=passed, gaps=gaps, notes=notes.strip())
        state.critiques.append(critique)
        state.log("critic", "reviewed", score=score, passed=passed, gaps=gaps)
        self.log.info("Critique: score=%.1f passed=%s gaps=%d", score, passed, len(gaps))
        return state
