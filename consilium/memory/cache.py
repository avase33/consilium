"""A small SQLite-backed cache for tool/LLM results.

Caching search and model calls is a cheap, high-impact production win: it makes
re-runs fast and deterministic and cuts API spend. ``NullCache`` is a no-op
drop-in when caching is disabled.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from typing import Any


class NullCache:
    def get(self, namespace: str, *key_parts: Any) -> Any | None:
        return None

    def set(self, namespace: str, value: Any, *key_parts: Any) -> None:
        pass


class SqliteCache:
    def __init__(self, path: str = "consilium-cache.db", ttl_seconds: int | None = None):
        self.ttl = ttl_seconds
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, created_at REAL)"
        )
        self.conn.commit()

    @staticmethod
    def _key(namespace: str, key_parts: tuple) -> str:
        raw = namespace + "|" + json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, namespace: str, *key_parts: Any) -> Any | None:
        row = self.conn.execute(
            "SELECT value, created_at FROM cache WHERE key=?", (self._key(namespace, key_parts),)
        ).fetchone()
        if not row:
            return None
        value, created = row
        if self.ttl is not None and time.time() - created > self.ttl:
            return None
        return json.loads(value)

    def set(self, namespace: str, value: Any, *key_parts: Any) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?,?)",
            (self._key(namespace, key_parts), json.dumps(value, default=str), time.time()),
        )
        self.conn.commit()
