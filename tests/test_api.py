"""API tests — require the server extras (fastapi + httpx + pydantic)."""

import importlib

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSILIUM_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("CONSILIUM_PROVIDER", "mock")
    monkeypatch.setenv("CONSILIUM_SEARCH", "mock")
    monkeypatch.setenv("CONSILIUM_CACHE", "false")
    import consilium.service.api as api
    importlib.reload(api)
    return TestClient(api.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["provider"] == "mock"


def test_research_returns_report(client):
    r = client.post("/api/research", json={"topic": "electric vehicle charging market"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["report"] is not None
    assert len(body["report"]["sections"]) >= 1
    assert body["usage"]["total_tokens"] > 0


def test_runs_listed_after_research(client):
    client.post("/api/research", json={"topic": "cloud market"})
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_stream_endpoint(client):
    with client.stream("POST", "/api/research/stream", json={"topic": "ai chips market"}) as resp:
        assert resp.status_code == 200
        events = [line for line in resp.iter_lines() if line and line.startswith("data: ")]
    assert events  # received SSE events
