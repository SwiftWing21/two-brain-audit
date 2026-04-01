"""SQLite storage for audit scores and user feedback."""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any

from two_brain_audit.grades import grade_to_score

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_scores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL DEFAULT (datetime('now')),
    tier         TEXT    NOT NULL,
    dimension    TEXT    NOT NULL,
    auto_score   REAL,
    auto_detail  TEXT,
    auto_confidence REAL,
    manual_grade TEXT,
    divergence   INTEGER DEFAULT 0,
    acknowledged INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_scores(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_dim ON audit_scores(dimension);

CREATE TABLE IF NOT EXISTS user_feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  TEXT    NOT NULL DEFAULT (datetime('now')),
    score      REAL    NOT NULL,
    scope      TEXT    NOT NULL,
    session_id TEXT,
    text       TEXT,
    inferred   TEXT,
    actor      TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_scope_ts ON user_feedback(scope, timestamp);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""

CURRENT_VERSION = 1


class AuditDB:
    """Thread-safe SQLite storage for audit data.

    Connections are cached per-thread. WAL mode is enabled for concurrent reads.
    """

    def __init__(self, db_path: str = "audit.db") -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        # Track schema version
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_VERSION,))
            conn.commit()

    # ── Scores ───────────────────────────────────────────────────────

    def write_score(self, result: Any) -> None:
        """Write a DimensionResult to the audit_scores table."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO audit_scores
               (timestamp, tier, dimension, auto_score, auto_detail,
                auto_confidence, manual_grade, divergence, acknowledged)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.timestamp,
                result.tier,
                result.name,
                result.auto_score,
                json.dumps(result.auto_detail),
                result.auto_confidence,
                result.manual_grade,
                1 if result.divergent else 0,
                1 if result.acknowledged else 0,
            ),
        )
        conn.commit()

    def latest_scores(self) -> list[Any]:
        """Get the most recent score per dimension."""
        from two_brain_audit.engine import DimensionResult

        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM audit_scores
               WHERE id IN (
                   SELECT MAX(id) FROM audit_scores GROUP BY dimension
               )
               ORDER BY dimension"""
        ).fetchall()

        results = []
        for row in rows:
            results.append(DimensionResult(
                name=row["dimension"],
                auto_score=row["auto_score"],
                auto_detail=json.loads(row["auto_detail"] or "{}"),
                auto_confidence=row["auto_confidence"] or 0.0,
                manual_grade=row["manual_grade"],
                manual_score=grade_to_score(row["manual_grade"]) if row["manual_grade"] else None,
                divergent=bool(row["divergence"]),
                acknowledged=bool(row["acknowledged"]),
                tier=row["tier"],
                timestamp=row["timestamp"],
            ))
        return results

    def score_history(self, dimension: str | None = None, days: int = 30) -> list[dict[str, Any]]:
        """Time series of scores, optionally filtered by dimension."""
        conn = self._get_conn()
        if dimension:
            rows = conn.execute(
                """SELECT * FROM audit_scores
                   WHERE dimension = ?
                   AND timestamp >= datetime('now', ?)
                   ORDER BY timestamp""",
                (dimension, f"-{days} days"),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM audit_scores
                   WHERE timestamp >= datetime('now', ?)
                   ORDER BY timestamp""",
                (f"-{days} days",),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_divergences(self, *, include_acknowledged: bool = False) -> list[Any]:
        """Active divergences from most recent scores."""
        scores = self.latest_scores()
        return [
            s for s in scores
            if s.divergent and (include_acknowledged or not s.acknowledged)
        ]

    def is_acknowledged(self, dimension: str) -> bool:
        """Check if the latest score for a dimension has been acknowledged."""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT acknowledged FROM audit_scores
               WHERE dimension = ?
               ORDER BY id DESC LIMIT 1""",
            (dimension,),
        ).fetchone()
        return bool(row["acknowledged"]) if row else False

    def acknowledge(self, dimension: str) -> None:
        """Mark the latest divergence for a dimension as acknowledged."""
        conn = self._get_conn()
        conn.execute(
            """UPDATE audit_scores SET acknowledged = 1
               WHERE dimension = ?
               AND id = (SELECT MAX(id) FROM audit_scores WHERE dimension = ?)""",
            (dimension, dimension),
        )
        conn.commit()

    # ── Feedback ─────────────────────────────────────────────────────

    def write_feedback(
        self,
        score: float,
        scope: str = "overall",
        text: str | None = None,
        session_id: str | None = None,
        actor: str | None = None,
        inferred: str | None = None,
    ) -> int:
        """Record user feedback. Returns the row ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO user_feedback (score, scope, text, session_id, actor, inferred)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (score, scope, text, session_id, actor, inferred),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def feedback_summary(self) -> dict[str, Any]:
        """Aggregated feedback statistics."""
        conn = self._get_conn()
        row = conn.execute(
            """SELECT COUNT(*) as count, AVG(score) as avg_score,
                      MIN(score) as min_score, MAX(score) as max_score
               FROM user_feedback"""
        ).fetchone()
        return dict(row) if row else {"count": 0, "avg_score": None}

    # ── Maintenance ──────────────────────────────────────────────────

    def row_count(self) -> dict[str, int]:
        """Row counts for monitoring DB growth."""
        conn = self._get_conn()
        scores = conn.execute("SELECT COUNT(*) FROM audit_scores").fetchone()[0]
        feedback = conn.execute("SELECT COUNT(*) FROM user_feedback").fetchone()[0]
        return {"audit_scores": scores, "user_feedback": feedback}
