# Deploying Consilium

## Local (offline, zero setup)

```bash
pip install -e .
python -m consilium research "electric vehicle charging market"
```

Runs on the deterministic mock model + mock search — no keys, no network.

## Local with real models

```bash
pip install -e ".[server]"
cp .env.example .env      # add ANTHROPIC_API_KEY / OPENAI_API_KEY / TAVILY_API_KEY
export $(grep -v '^#' .env | xargs)
uvicorn consilium.service.api:app --reload   # http://127.0.0.1:8000/docs
```

## Docker Compose (API + worker + Redis)

```bash
cd deploy
docker compose up --build
```

Brings up:
- **redis** — the message broker.
- **api** — FastAPI service on `:8000` (`/docs` for interactive OpenAPI).
- **worker** — FastStream consumer of `research.requests`.

Configure via environment (see `.env.example`). For production, set
`CONSILIUM_PROVIDER`, a real search backend, and point `REDIS_URL` at a managed
broker.

## Scaling

The workflow is stateless per request (state lives in SQLite / the message
payload), so you scale by running more `worker` replicas behind Redis and more
`api` replicas behind a load balancer. Swap the FastStream broker import
(`RedisBroker` → `NatsBroker`/`KafkaBroker`) to change transports without
touching the agents.

## Configuration reference

See [`.env.example`](../.env.example) for every supported variable (provider,
search backend, orchestrator, iteration budget, thresholds, DB path, caching,
logging).
