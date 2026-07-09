"""Pydantic request/response models for the HTTP API.

These validate and document the API surface (FastAPI turns them into OpenAPI).
They mirror the internal dataclasses in ``consilium.models``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300, examples=["EV charging market in Europe"])
    depth: Literal["quick", "standard", "deep"] = "standard"
    max_iterations: int | None = Field(default=None, ge=1, le=5)


class SourceOut(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    score: float = 0.0


class FindingOut(BaseModel):
    id: str
    claim: str
    subtopic: str
    confidence: float
    source_ids: list[str]


class SectionOut(BaseModel):
    heading: str
    content: str
    citations: list[str]


class ReportOut(BaseModel):
    topic: str
    executive_summary: str
    sections: list[SectionOut]
    sources: list[SourceOut]


class UsageOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class RunResult(BaseModel):
    run_id: str
    status: str
    iterations: int
    plan: list[str]
    findings: list[FindingOut]
    report: ReportOut | None
    usage: UsageOut


class RunSummary(BaseModel):
    id: str
    topic: str
    status: str
    sources: int
    findings: int
    prompt_tokens: int
    completion_tokens: int
