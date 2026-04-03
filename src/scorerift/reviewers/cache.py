"""Local review cache — avoid re-reviewing unchanged content.

Cache key = hash(dimension + context + provider + model + lens).
Cached results are stored in the audit DB alongside scores.
TTL-based expiry prevents stale reviews.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
from typing import Any

log = logging.getLogger("scorerift.reviewers")

_DEFAULT_TTL = 86400 * 7  # 7 days


class ReviewCache:
    """SQLite-backed review result cache.

    Prevents redundant API calls when context hasn't changed.
    Also enables batch mode: cache misses are collected and can be
    sent as a batch request instead of individual calls.
    """

    def __init__(self, db_path: str = "audit.db", ttl: int = _DEFAULT_TTL) -> None:
        self.db_path = db_path
        self.ttl = ttl
        self._local = threading.local()
        self._init_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_table(self) -> None:
        self._get_conn().executescript("""
            CREATE TABLE IF NOT EXISTS review_cache (
                cache_key  TEXT PRIMARY KEY,
                dimension  TEXT NOT NULL,
                provider   TEXT NOT NULL,
                model      TEXT NOT NULL,
                lens       TEXT,
                result     TEXT NOT NULL,
                cost_usd   REAL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_review_cache_dim
                ON review_cache(dimension);
        """)

    @staticmethod
    def make_key(dimension: str, context: str, provider: str, model: str,
                 lens: str | None = None) -> str:
        """Deterministic cache key from review parameters."""
        parts = f"{dimension}|{provider}|{model}|{lens or ''}|{context}"
        return hashlib.sha256(parts.encode()).hexdigest()[:32]

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a cached review result. Returns None on miss or expiry."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT result, expires_at FROM review_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        # Check expiry
        if row["expires_at"] < time.strftime("%Y-%m-%dT%H:%M:%S"):
            conn.execute("DELETE FROM review_cache WHERE cache_key = ?", (key,))
            conn.commit()
            return None
        return json.loads(row["result"])

    def put(self, key: str, dimension: str, provider: str, model: str,
            result: dict[str, Any], cost_usd: float = 0.0,
            lens: str | None = None) -> None:
        """Store a review result in the cache."""
        conn = self._get_conn()
        expires = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(time.time() + self.ttl),
        )
        conn.execute(
            """INSERT OR REPLACE INTO review_cache
               (cache_key, dimension, provider, model, lens, result, cost_usd, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, dimension, provider, model, lens,
             json.dumps(result, ensure_ascii=False), cost_usd, expires),
        )
        conn.commit()

    def invalidate(self, dimension: str | None = None) -> int:
        """Clear cache entries. If dimension given, only clear that dimension."""
        conn = self._get_conn()
        if dimension:
            cursor = conn.execute(
                "DELETE FROM review_cache WHERE dimension = ?", (dimension,),
            )
        else:
            cursor = conn.execute("DELETE FROM review_cache")
        conn.commit()
        return cursor.rowcount

    def stats(self) -> dict[str, Any]:
        """Cache statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM review_cache").fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM review_cache WHERE expires_at < datetime('now')"
        ).fetchone()[0]
        total_cost = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM review_cache"
        ).fetchone()[0]
        return {
            "cached_reviews": total,
            "expired": expired,
            "active": total - expired,
            "total_cost_saved_usd": round(total_cost, 4),
        }
