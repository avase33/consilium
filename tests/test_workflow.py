import asyncio

from consilium.config import Settings
from consilium.orchestration import ResearchRunner
from consilium.reporting import to_markdown


def _settings(tmp_path):
    s = Settings()
    s.provider = "mock"
    s.search_backend = "mock"
    s.cache_enabled = False
    s.db_path = str(tmp_path / "consilium.db")
    s.subtopics = 4
    s.max_iterations = 2
    return s


def test_full_pipeline_produces_report(tmp_path):
    runner = ResearchRunner(_settings(tmp_path))
    state = asyncio.run(runner.run("electric vehicle charging market in Europe"))

    assert state.status.value == "completed"
    assert len(state.plan) == 4
    assert state.report is not None
    assert state.report.executive_summary
    assert len(state.report.sections) == 4
    assert state.usage.total_tokens > 0


def test_revise_loop_actually_runs(tmp_path):
    # First pass is shallow (k=2) -> Critic finds gaps -> team revises -> deep pass passes.
    runner = ResearchRunner(_settings(tmp_path))
    state = asyncio.run(runner.run("cloud infrastructure market"))

    assert len(state.critiques) >= 2, "expected a revise cycle"
    assert state.critiques[0].passed is False
    assert state.critiques[-1].passed is True
    assert state.iteration >= 1


def test_run_is_persisted_and_listed(tmp_path):
    runner = ResearchRunner(_settings(tmp_path))
    state = asyncio.run(runner.run("semiconductor market"))
    stored = runner.store.get(state.run_id)
    assert stored is not None and stored["report"] is not None
    assert any(r["id"] == state.run_id for r in runner.store.list())


def test_report_renders_markdown(tmp_path):
    runner = ResearchRunner(_settings(tmp_path))
    state = asyncio.run(runner.run("renewable energy storage market"))
    md = to_markdown(state.report)
    assert md.startswith("# Research report:")
    assert "## Executive summary" in md
    assert "## References" in md


def test_streaming_emits_events(tmp_path):
    runner = ResearchRunner(_settings(tmp_path))

    async def collect():
        nodes = []
        async for node, _state in runner.stream("fintech payments market"):
            nodes.append(node)
        return nodes

    nodes = asyncio.run(collect())
    assert nodes[0] == "plan"
    assert "write" in nodes
    assert nodes.count("research") >= 2  # revise loop => researched twice
