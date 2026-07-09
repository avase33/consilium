"""SQLite persistence for research runs and their reports."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..models import Report, ResearchState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, topic TEXT, status TEXT, created_at REAL,
  iterations INTEGER, sources INTEGER, findings INTEGER,
  prompt_tokens INTEGER, completion_tokens INTEGER, report TEXT, trace TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
"""


class RunStore:
    def __init__(self, path: str = "consilium.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def save(self, state: ResearchState) -> None:
        report_json = json.dumps(state.report.to_dict()) if state.report else None
        trace_json = json.dumps([{"node": e.node, "kind": e.kind, "data": e.data, "at": e.at}
                                 for e in state.trace])
        self.conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (state.run_id, state.topic, state.status.value, time.time(), state.iteration,
             len(state.sources), len(state.findings), state.usage.prompt_tokens,
             state.usage.completion_tokens, report_json, trace_json),
        )
        self.conn.commit()

    def get(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["report"] = json.loads(data["report"]) if data["report"] else None
        data["trace"] = json.loads(data["trace"]) if data["trace"] else []
        return data

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, topic, status, created_at, sources, findings, "
            "prompt_tokens, completion_tokens FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
