"""Event-driven research worker built with FastStream.

Consumes research requests off a ``research.requests`` stream, runs the
multi-agent workflow, and publishes the result to ``research.results``. This is
how you scale the system horizontally: run N workers behind a broker (Redis here;
swap for NATS/Kafka/RabbitMQ by changing the broker import).

Run with:  faststream run consilium.messaging.streams:app
"""

from __future__ import annotations

import os

from faststream import FastStream
from faststream.redis import RedisBroker
from pydantic import BaseModel

from ..config import Settings
from ..orchestration import ResearchRunner

broker = RedisBroker(os.environ.get("REDIS_URL", "redis://localhost:6379"))
app = FastStream(broker)

_runner = ResearchRunner(Settings.from_env())


class ResearchTask(BaseModel):
    topic: str
    depth: str = "standard"


class ResearchOutcome(BaseModel):
    run_id: str
    topic: str
    status: str
    findings: int
    sources: int
    total_tokens: int
    cost_usd: float


@broker.subscriber("research.requests")
@broker.publisher("research.results")
async def handle_research(task: ResearchTask) -> ResearchOutcome:  # pragma: no cover - needs broker
    state = await _runner.run(task.topic, depth=task.depth)
    return ResearchOutcome(
        run_id=state.run_id,
        topic=state.topic,
        status=state.status.value,
        findings=len(state.findings),
        sources=len(state.sources),
        total_tokens=state.usage.total_tokens,
        cost_usd=_runner.cost_usd(state),
    )


async def publish_task(topic: str, depth: str = "standard") -> None:  # pragma: no cover - needs broker
    """Helper to enqueue a research task from other code."""
    async with broker:
        await broker.publish(ResearchTask(topic=topic, depth=depth), "research.requests")
