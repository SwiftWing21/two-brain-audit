"""Preset dimensions for infrastructure/DevOps auditing."""

from __future__ import annotations

from two_brain_audit import Dimension, Tier


def _stub(name: str) -> tuple[float, dict]:
    return 0.5, {"note": f"{name} check not yet implemented"}


INFRASTRUCTURE_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="uptime",
        check=lambda: _stub("uptime"),
        confidence=0.95,
        tier=Tier.LIGHT,
        description="Service uptime above SLA threshold",
    ),
    Dimension(
        name="cert_expiry",
        check=lambda: _stub("cert_expiry"),
        confidence=0.95,
        tier=Tier.WEEKLY,
        description="SSL/TLS certificates not expiring within 30 days",
    ),
    Dimension(
        name="resource_utilization",
        check=lambda: _stub("resource_utilization"),
        confidence=0.85,
        tier=Tier.LIGHT,
        description="CPU/RAM/disk within healthy bounds",
    ),
    Dimension(
        name="config_drift",
        check=lambda: _stub("config_drift"),
        confidence=0.80,
        tier=Tier.DAILY,
        description="Deployed state matches declared config (Terraform/K8s)",
    ),
    Dimension(
        name="secret_rotation",
        check=lambda: _stub("secret_rotation"),
        confidence=0.85,
        tier=Tier.WEEKLY,
        description="Secrets/API keys rotated within policy window",
    ),
    Dimension(
        name="dns_propagation",
        check=lambda: _stub("dns_propagation"),
        confidence=0.90,
        tier=Tier.DAILY,
        description="DNS records resolve correctly from multiple locations",
    ),
    Dimension(
        name="cdn_cache_hit_rate",
        check=lambda: _stub("cdn_cache_hit_rate"),
        confidence=0.80,
        tier=Tier.DAILY,
        description="CDN cache hit rate above target threshold",
    ),
    Dimension(
        name="container_health",
        check=lambda: _stub("container_health"),
        confidence=0.90,
        tier=Tier.LIGHT,
        description="All containers healthy with no restart loops",
    ),
]
