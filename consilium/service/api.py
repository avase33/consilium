"""FastAPI service exposing the multi-agent research system.

Endpoints
  GET  /api/health
  POST /api/research           -> run to completion, return the report
  POST /api/research/stream    -> Server-Sent Events with live agent progress
  GET  /api/runs               -> list past runs
  GET  /api/runs/{id}          -> a stored run + report
  GET  /api/runs/{id}/report.md-> the report as Markdown

Run with:  uvicorn consilium.service.api:app  (or `consilium serve`).
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from ..config import Settings
from ..logging_setup import configure_logging
from ..models import ResearchState
from ..orchestration import ResearchRunner
from ..reporting import to_markdown
from .schemas import (
    FindingOut,
    ReportOut,
    ResearchRequest,
    RunResult,
    RunSummary,
    SectionOut,
    SourceOut,
    UsageOut,
)

settings = Settings.from_env()
configure_logging(settings.log_level, settings.log_json)
runner = ResearchRunner(settings)

app = FastAPI(
    title="Consilium",
    version="0.1.0",
    description="A multi-agent corporate research system (Supervisor · Researcher · Analyst · Critic).",
)


def _to_result(state: ResearchState) -> RunResult:
    report = None
    if state.report:
        report = ReportOut(
            topic=state.report.topic,
            executive_summary=state.report.executive_summary,
            sections=[SectionOut(heading=s.heading, content=s.content, citations=s.citations)
                      for s in state.report.sections],
            sources=[SourceOut(id=s.id, title=s.title, url=s.url, snippet=s.snippet, score=s.score)
                     for s in state.report.sources],
        )
    return RunResult(
        run_id=state.run_id,
        status=state.status.value,
        iterations=state.iteration,
        plan=state.plan,
        findings=[FindingOut(id=f.id, claim=f.claim, subtopic=f.subtopic,
                             confidence=f.confidence, source_ids=f.source_ids) for f in state.findings],
        report=report,
        usage=UsageOut(
            prompt_tokens=state.usage.prompt_tokens,
            completion_tokens=state.usage.completion_tokens,
            total_tokens=state.usage.total_tokens,
            cost_usd=runner.cost_usd(state),
        ),
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "provider": settings.provider, "search": settings.search_backend,
            "orchestrator": settings.orchestrator}


@app.post("/api/research", response_model=RunResult)
async def research(req: ResearchRequest) -> RunResult:
    if req.max_iterations:
        runner.settings.max_iterations = req.max_iterations
    state = await runner.run(req.topic, depth=req.depth)
    return _to_result(state)


@app.post("/api/research/stream")
async def research_stream(req: ResearchRequest) -> StreamingResponse:
    if req.max_iterations:
        runner.settings.max_iterations = req.max_iterations

    async def gen():
        final: ResearchState | None = None
        async for node, state in runner.stream(req.topic, depth=req.depth):
            final = state
            yield "data: " + json.dumps({
                "event": "node", "node": node, "status": state.status.value,
                "sources": len(state.sources), "findings": len(state.findings),
                "iteration": state.iteration,
            }) + "\n\n"
        if final is not None:
            yield "data: " + json.dumps({"event": "done", "result": _to_result(final).model_dump()}) + "\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/runs", response_model=list[RunSummary])
async def list_runs() -> list[RunSummary]:
    return [RunSummary(**r) for r in runner.store.list()]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    data = runner.store.get(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="run not found")
    return data


@app.get("/api/runs/{run_id}/report.md", response_class=PlainTextResponse)
async def get_run_markdown(run_id: str) -> str:
    data = runner.store.get(run_id)
    if not data or not data.get("report"):
        raise HTTPException(status_code=404, detail="report not found")
    from ..models import Report, ReportSection, Source

    rd = data["report"]
    report = Report(
        topic=rd["topic"], executive_summary=rd["executive_summary"],
        sections=[ReportSection(**s) for s in rd["sections"]],
        sources=[Source(**{k: v for k, v in s.items() if k in ("id", "title", "url", "snippet", "query", "score")})
                 for s in rd["sources"]],
    )
    return to_markdown(report)
