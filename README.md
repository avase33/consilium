<div align="center">

# 🏛️ Consilium

### A production-grade multi-agent system for deep corporate & market research.

A **Supervisor** plans the work and routes hand-offs; a **Researcher** searches the web; an **Analyst** structures the evidence; a **Critic** grades it and can send the team back for another pass — all over a typed, async state graph.

[![CI](https://github.com/avase33/consilium/actions/workflows/ci.yml/badge.svg)](https://github.com/avase33/consilium/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009485)](https://fastapi.tiangolo.com)
[![FastStream](https://img.shields.io/badge/events-FastStream-ff69b4)](https://faststream.airt.ai)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![core deps](https://img.shields.io/badge/core%20runtime%20deps-0-brightgreen)](pyproject.toml)

</div>

---

**Consilium** is a team of specialized AI agents that collaborate to produce
cited research reports. It demonstrates the things that make agentic systems
actually work in production: explicit **state management**, **custom tools with
JSON-schema invocation**, **multi-agent routing with a revise loop**, plus the
operational layer around it — a REST + streaming API, an event-driven worker,
persistence, caching, observability, and Docker.

It is **offline-first**: with no API keys it runs end-to-end on a deterministic
mock model and mock search, so `git clone && python -m consilium research "..."`
just works. Drop in Anthropic/OpenAI + a real search backend for production.

```bash
pip install -e .
python -m consilium research "the global electric vehicle charging market"
```

```
  🧭 plan      status=planning     sources=0  findings=0
  🔎 research  status=researching  sources=8  findings=0
  🧩 analyze   status=analyzing    sources=8  findings=4
  ⚖️ critique  status=reviewing    sources=8  findings=4  score=0.0     ← gaps found
  🔎 research  status=researching  sources=16 findings=4                ← team revises, deepens
  🧩 analyze   status=analyzing    sources=16 findings=4
  ⚖️ critique  status=reviewing    sources=16 findings=4  score=10.0    ← passes
  📝 write     status=completed    sources=16 findings=4

# Research report: the global electric vehicle charging market
## Executive summary
...
```

## ✨ What it demonstrates

| Capability | How |
|---|---|
| 🧠 **Multi-agent collaboration** | Supervisor · Researcher · Analyst · Critic with explicit hand-offs |
| 🔀 **State-graph orchestration** | Typed async `StateGraph` with conditional edges + a **revise loop** (LangGraph-style; real LangGraph adapter included) |
| 🛠️ **Custom tools + JSON schema** | `@tool` auto-generates the function schema; pluggable `web_search` backend |
| 📄 **Grounded, cited output** | Findings carry source IDs; the report renders citations + references |
| 🌐 **Production API** | FastAPI REST + **SSE streaming** of live agent progress (Pydantic models, OpenAPI docs) |
| 📨 **Event-driven scale-out** | FastStream worker over Redis (`research.requests` → `research.results`) |
| 💾 **Persistence & caching** | SQLite run store + SQLite cache for search/LLM calls |
| 🔭 **Observability** | Per-node trace + token and **USD cost accounting** |
| 🐳 **Deployable** | Dockerfile + `docker-compose` (api + worker + redis), CI, Makefile |

## 🧱 The stack

**LangGraph-style orchestration** (built-in async engine, plus a real
[`langgraph`](https://github.com/langchain-ai/langgraph) adapter) ·
**Pydantic** (API schemas / validation) · **FastAPI** (REST + SSE) ·
**FastStream + Redis** (event worker) · **Anthropic / OpenAI** (LLMs) ·
**Tavily** (web search) — all optional behind an offline mock.

## 🚀 Usage

### CLI

```bash
python -m consilium research "cloud infrastructure market" --md report.md --json report.json
python -m consilium runs          # list past runs (persisted in SQLite)
python -m consilium serve         # run the API
```

### API

```bash
pip install -e ".[server]"
uvicorn consilium.service.api:app --reload      # http://127.0.0.1:8000/docs

curl -X POST localhost:8000/api/research -H 'content-type: application/json' \
     -d '{"topic":"semiconductor market","depth":"standard"}'

# stream live agent progress (Server-Sent Events):
curl -N -X POST localhost:8000/api/research/stream -H 'content-type: application/json' \
     -d '{"topic":"semiconductor market"}'
```

### Library

```python
import asyncio
from consilium.orchestration import ResearchRunner

runner = ResearchRunner()                       # offline mock by default
state = asyncio.run(runner.run("fintech payments market"))
print(state.report.executive_summary)
print("cost $", runner.cost_usd(state))
```

### Go live

```bash
export ANTHROPIC_API_KEY=sk-...     # or OPENAI_API_KEY
export TAVILY_API_KEY=tvly-...      # real web search
export CONSILIUM_SEARCH=tavily
python -m consilium research "your topic"
```

## 🔀 The workflow

```
plan → research → analyze → critique ─┬─ passed / budget spent → write → END
                     ▲                │
                     └──── gaps ──────┘   (Critic routes the team back to deepen weak areas)
```

The Critic is a real quality gate: the first research pass is deliberately
shallow, so the Critic finds gaps and routes back to the Researcher, which
deepens the search until coverage passes (or the iteration budget is spent).
See [`docs/architecture.md`](docs/architecture.md).

## 🐳 Run the whole thing

```bash
cd deploy && docker compose up --build     # api :8000 + FastStream worker + redis
```

## 🔬 Tested

The agent/graph core is covered by tests that need **no network and no keys** —
the graph engine (including the conditional loop), each agent, the full research
pipeline (asserting the revise loop actually fires), tools, persistence, and
Markdown rendering. The API is tested with FastAPI's `TestClient`, including the
streaming endpoint.

```bash
pip install -e ".[dev,server]"
pytest -q
```

CI runs the suite on Python 3.10–3.12, smoke-tests the CLI, imports the API, and
builds the Docker image.

## 🗺️ Roadmap

- [ ] Structured tool-calling loop with native function calling per provider
- [ ] Parallel researcher fan-out (one branch per subtopic)
- [ ] Vector memory of prior reports for cross-run synthesis
- [ ] Human-in-the-loop approval node before the final write
- [ ] Prometheus metrics + OpenTelemetry traces

## 📄 License

MIT © Akhil Vase — see [LICENSE](LICENSE).
