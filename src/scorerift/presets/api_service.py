"""Preset dimensions for REST API services."""

from __future__ import annotations

from scorerift import Dimension, Tier


def _stub(name: str) -> tuple[float, dict]:
    return 0.5, {"note": f"{name} check not yet implemented"}


API_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="endpoint_health",
        check=lambda: _stub("endpoint_health"),
        confidence=0.95,
        tier=Tier.LIGHT,
        description="All registered endpoints return 2xx/3xx",
    ),
    Dimension(
        name="response_latency",
        check=lambda: _stub("response_latency"),
        confidence=0.85,
        tier=Tier.MEDIUM,
        description="p95 response time under threshold",
    ),
    Dimension(
        name="error_rate",
        check=lambda: _stub("error_rate"),
        confidence=0.90,
        tier=Tier.LIGHT,
        description="5xx error rate below threshold",
    ),
    Dimension(
        name="auth_coverage",
        check=lambda: _stub("auth_coverage"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="All sensitive endpoints require authentication",
    ),
    Dimension(
        name="schema_validation",
        check=lambda: _stub("schema_validation"),
        confidence=0.85,
        tier=Tier.MEDIUM,
        description="OpenAPI schema matches actual responses",
    ),
    Dimension(
        name="rate_limiting",
        check=lambda: _stub("rate_limiting"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="Rate limiting configured and functional",
    ),
    Dimension(
        name="cors_config",
        check=lambda: _stub("cors_config"),
        confidence=0.85,
        tier=Tier.DAILY,
        description="CORS headers match allowed origins",
    ),
    Dimension(
        name="tls_expiry",
        check=lambda: _stub("tls_expiry"),
        confidence=0.95,
        tier=Tier.WEEKLY,
        description="TLS certificate not expiring within 30 days",
    ),
]
