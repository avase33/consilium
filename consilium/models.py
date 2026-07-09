"""Core domain models (framework-free dataclasses).

These are the shared vocabulary that flows through the agent graph. Keeping them
as plain dataclasses (rather than tied to a web framework) means the whole
orchestration core has zero third-party dependencies and is trivially testable.
Pydantic models at the API boundary (see ``service/schemas.py``) mirror these.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class RunStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    REVIEWING = "reviewing"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.prompt_tokens + other.prompt_tokens,
                     self.completion_tokens + other.completion_tokens)

    def cost_usd(self, prompt_per_1k: float, completion_per_1k: float) -> float:
        return round(
            self.prompt_tokens / 1000 * prompt_per_1k
            + self.completion_tokens / 1000 * completion_per_1k,
            6,
        )


@dataclass
class Source:
    """A retrieved web result / document."""

    title: str
    url: str
    snippet: str
    query: str = ""
    score: float = 0.0
    id: str = field(default_factory=lambda: new_id("src"))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "url": self.url,
                "snippet": self.snippet, "query": self.query, "score": round(self.score, 4)}


@dataclass
class Finding:
    """A structured, evidence-backed claim produced by the Analyst."""

    claim: str
    evidence: str
    source_ids: list[str] = field(default_factory=list)
    subtopic: str = ""
    confidence: float = 0.5
    id: str = field(default_factory=lambda: new_id("fnd"))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "claim": self.claim, "evidence": self.evidence,
                "source_ids": self.source_ids, "subtopic": self.subtopic,
                "confidence": round(self.confidence, 3)}


@dataclass
class Critique:
    """The Critic's assessment of the current findings."""

    score: float  # 0..10
    passed: bool
    gaps: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "passed": self.passed, "gaps": self.gaps, "notes": self.notes}


@dataclass
class ReportSection:
    heading: str
    content: str
    citations: list[str] = field(default_factory=list)


@dataclass
class Report:
    topic: str
    executive_summary: str
    sections: list[ReportSection] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "executive_summary": self.executive_summary,
            "sections": [{"heading": s.heading, "content": s.content, "citations": s.citations}
                         for s in self.sections],
            "sources": [s.to_dict() for s in self.sources],
            "generated_at": self.generated_at,
        }


@dataclass
class TraceEvent:
    node: str
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    at: float = field(default_factory=time.time)


@dataclass
class ResearchState:
    """The single state object that flows through the graph."""

    topic: str
    depth: str = "standard"                       # quick | standard | deep
    plan: list[str] = field(default_factory=list)  # subtopics / research questions
    sources: list[Source] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    critiques: list[Critique] = field(default_factory=list)
    report: Report | None = None
    iteration: int = 0
    max_iterations: int = 2
    status: RunStatus = RunStatus.PENDING
    usage: Usage = field(default_factory=Usage)
    trace: list[TraceEvent] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: new_id("run"))
    error: str | None = None

    def log(self, node: str, kind: str, **data: Any) -> None:
        self.trace.append(TraceEvent(node=node, kind=kind, data=data))

    def source_by_id(self, sid: str) -> Source | None:
        return next((s for s in self.sources if s.id == sid), None)
