# Consilium architecture

Consilium is a multi-agent research system with a clean separation between the
**agent/orchestration core** (pure standard library, fully testable offline) and
the **production surface** (FastAPI, FastStream, Redis, Docker).

```
        HTTP client / CLI / message producer
                     │
        ┌────────────┼──────────────────────────────┐
        ▼            ▼                               ▼
   FastAPI       FastStream worker             consilium CLI
   (REST+SSE)    (research.requests →          (research / runs / serve)
        │         research.results)                 │
        └────────────┬──────────────────────────────┘
                     ▼
              ResearchRunner  ── assembles provider, tools, agents, graph, store
                     │
                     ▼
        ┌──────────  State graph (async)  ──────────┐
        │  plan → research → analyze → critique ─┐   │
        │            ▲                           │   │
        │            └────── revise loop ────────┘   │
        │                         │                  │
        │                         ▼                  │
        │                       write → END          │
        └────────────────────────────────────────────┘
             │            │           │          │
             ▼            ▼           ▼          ▼
         Supervisor   Researcher   Analyst    Critic
             │            │
             │            ▼
             │       web_search tool ─► SearchBackend (mock | Tavily)
             ▼
          LLM provider (mock | Anthropic | OpenAI)

   Cross-cutting: SQLite cache · SQLite run store · run tracing · token/cost accounting
```

## The state graph

The orchestration core is a tiny async **`StateGraph`** (see
[`graph/engine.py`](../consilium/graph/engine.py)): register async nodes,
connect them with static or **conditional** edges, `compile()`, then `invoke`
or `stream`. Conditional edges implement multi-agent routing and the Critic's
revise loop. A drop-in [`langgraph_adapter.py`](../consilium/graph/langgraph_adapter.py)
builds the same workflow on the real LangGraph runtime when
`CONSILIUM_ORCHESTRATOR=langgraph`.

A single **`ResearchState`** flows through every node, accumulating the plan,
sources, findings, critiques, token usage, and a structured trace.

## The agents

| Agent | Responsibility | Key mechanic |
|---|---|---|
| **Supervisor** | Plan subtopics; write the final report | Decomposition + synthesis |
| **Researcher** | Gather evidence via the `web_search` tool | Shallow first pass, deeper on revise |
| **Analyst** | Filter/structure sources into cited findings | Group by subtopic, confidence scoring |
| **Critic** | Grade coverage, flag gaps | Quality gate that can trigger a revise |

Hand-offs are edges in the graph, not ad-hoc calls, so the control flow is
explicit, observable, and easy to change.

## Tools & JSON schemas

Tools are typed async functions wrapped by `@tool`, which derives the JSON
schema an LLM function-calling API expects. `web_search` is backed by a
pluggable `SearchBackend` (deterministic mock for offline/dev, Tavily for
production) with an optional SQLite cache in front.

## Production concerns

- **Persistence** — every run (status, plan, sources, findings, report, trace)
  is stored in SQLite (`RunStore`).
- **Caching** — search/LLM results cached in SQLite to cut latency and spend.
- **Observability** — per-node trace events plus token and USD cost accounting.
- **Scale-out** — a FastStream worker consumes research tasks off Redis; run N
  workers behind the broker. `docker-compose` brings up Redis + API + worker.
- **Offline-first** — the mock provider/search make the whole system run and CI
  pass with zero credentials.
