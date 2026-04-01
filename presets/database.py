"""Preset dimensions for database health auditing."""

from __future__ import annotations

from two_brain_audit import Dimension, Tier


def _stub(name: str) -> tuple[float, dict]:
    return 0.5, {"note": f"{name} check not yet implemented"}


DATABASE_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="schema_completeness",
        check=lambda: _stub("schema_completeness"),
        confidence=0.85,
        tier=Tier.MEDIUM,
        description="All expected tables/columns exist with correct types",
    ),
    Dimension(
        name="index_coverage",
        check=lambda: _stub("index_coverage"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="Frequently queried columns are indexed",
    ),
    Dimension(
        name="query_performance",
        check=lambda: _stub("query_performance"),
        confidence=0.75,
        tier=Tier.DAILY,
        description="No slow queries above threshold in recent log",
    ),
    Dimension(
        name="backup_freshness",
        check=lambda: _stub("backup_freshness"),
        confidence=0.95,
        tier=Tier.DAILY,
        description="Most recent backup exists and is within SLA window",
    ),
    Dimension(
        name="replication_lag",
        check=lambda: _stub("replication_lag"),
        confidence=0.90,
        tier=Tier.LIGHT,
        description="Replica lag below threshold",
    ),
    Dimension(
        name="pool_utilization",
        check=lambda: _stub("pool_utilization"),
        confidence=0.85,
        tier=Tier.LIGHT,
        description="Connection pool not exhausted or near limit",
    ),
    Dimension(
        name="migration_currency",
        check=lambda: _stub("migration_currency"),
        confidence=0.90,
        tier=Tier.DAILY,
        description="All pending migrations have been applied",
    ),
]
