import asyncio

from consilium.agents import Analyst, Critic, Supervisor
from consilium.config import Settings
from consilium.llm import MockLLM
from consilium.models import ResearchState, Source
from consilium.tools import MockSearchBackend, ToolRegistry, make_web_search_tool


def test_mock_search_is_deterministic():
    backend = MockSearchBackend()
    a = asyncio.run(backend.search("ev charging market", 4))
    b = asyncio.run(backend.search("ev charging market", 4))
    assert len(a) == 4
    assert [s.url for s in a] == [s.url for s in b]  # reproducible


def test_web_search_tool_schema_and_call():
    tool = make_web_search_tool(MockSearchBackend())
    schema = tool.schema()
    assert schema["name"] == "web_search"
    assert "query" in schema["parameters"]["properties"]
    reg = ToolRegistry()
    reg.register(tool)
    results = asyncio.run(reg.call("web_search", query="cloud market", k=3))
    assert len(results) == 3 and all("url" in r for r in results)


def test_supervisor_plans_subtopics():
    s = Settings(subtopics=4)
    sup = Supervisor(MockLLM(), s)
    state = ResearchState(topic="EV charging market")
    state = asyncio.run(sup.plan(state))
    assert len(state.plan) == 4


def test_analyst_builds_findings_and_critic_scores():
    s = Settings()
    state = ResearchState(topic="EV charging market", plan=["Market size and segments"])
    # 3 sources for the single subtopic -> should be well-covered.
    for i in range(3):
        state.sources.append(Source(title=f"t{i}", url=f"http://x/{i}", snippet="growth and competition",
                                     query="EV charging market Market size and segments"))
    state = asyncio.run(Analyst(MockLLM(), s)(state))
    assert len(state.findings) == 1 and state.findings[0].subtopic == "Market size and segments"

    state = asyncio.run(Critic(MockLLM(), s)(state))
    assert state.critiques[-1].score == 10.0
    assert state.critiques[-1].passed is True


def test_critic_flags_gaps_when_undersourced():
    s = Settings()
    state = ResearchState(topic="EV", plan=["A", "B"])
    state.sources.append(Source(title="t", url="http://x/1", snippet="e", query="EV A"))  # only 1 for A, 0 for B
    state = asyncio.run(Critic(MockLLM(), s)(state))
    crit = state.critiques[-1]
    assert crit.passed is False
    assert set(crit.gaps) == {"A", "B"}
