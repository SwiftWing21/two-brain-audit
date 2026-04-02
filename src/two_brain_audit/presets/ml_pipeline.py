"""Preset dimensions for ML pipeline auditing."""

from __future__ import annotations

from two_brain_audit import Dimension, Tier


def _stub(name: str) -> tuple[float, dict]:
    return 0.5, {"note": f"{name} check not yet implemented"}


ML_PIPELINE_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="model_freshness",
        check=lambda: _stub("model_freshness"),
        confidence=0.85,
        tier=Tier.DAILY,
        description="Model was retrained within acceptable window",
    ),
    Dimension(
        name="data_drift",
        check=lambda: _stub("data_drift"),
        confidence=0.75,
        tier=Tier.DAILY,
        description="Input feature distributions haven't drifted from training data",
    ),
    Dimension(
        name="inference_latency",
        check=lambda: _stub("inference_latency"),
        confidence=0.90,
        tier=Tier.LIGHT,
        description="Inference p95 latency under SLA threshold",
    ),
    Dimension(
        name="prediction_accuracy",
        check=lambda: _stub("prediction_accuracy"),
        confidence=0.80,
        tier=Tier.DAILY,
        description="Holdout set accuracy above minimum threshold",
    ),
    Dimension(
        name="feature_store_currency",
        check=lambda: _stub("feature_store_currency"),
        confidence=0.85,
        tier=Tier.DAILY,
        description="Feature store has been updated within expected cadence",
    ),
    Dimension(
        name="gpu_utilization",
        check=lambda: _stub("gpu_utilization"),
        confidence=0.85,
        tier=Tier.LIGHT,
        description="GPU utilization within healthy bounds during training",
    ),
    Dimension(
        name="experiment_tracking",
        check=lambda: _stub("experiment_tracking"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="All experiments have metadata, metrics, and artifacts logged",
    ),
]
