"""Run a full research study offline and print the report.

    python examples/run_research.py
"""

import asyncio

from consilium.config import Settings
from consilium.orchestration import ResearchRunner
from consilium.reporting import to_markdown


async def main() -> None:
    settings = Settings()  # defaults -> mock LLM + mock search (offline)
    runner = ResearchRunner(settings)

    topic = "the global electric vehicle charging market"
    print(f"Researching: {topic}\n")
    async for node, state in runner.stream(topic):
        print(f"  [{node:<9}] status={state.status.value:<11} "
              f"sources={len(state.sources)} findings={len(state.findings)}")

    print("\n" + "=" * 70 + "\n")
    print(to_markdown(state.report))
    print(f"\nTokens: {state.usage.total_tokens} | "
          f"cost: ${runner.cost_usd(state):.4f} | iterations: {state.iteration}")


if __name__ == "__main__":
    asyncio.run(main())
