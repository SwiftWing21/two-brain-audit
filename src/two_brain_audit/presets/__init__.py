"""Preset dimension configurations for common project types."""

from two_brain_audit.presets.api_service import API_DIMENSIONS
from two_brain_audit.presets.database import DATABASE_DIMENSIONS
from two_brain_audit.presets.infrastructure import INFRASTRUCTURE_DIMENSIONS
from two_brain_audit.presets.ml_pipeline import ML_PIPELINE_DIMENSIONS
from two_brain_audit.presets.python_project import PYTHON_DIMENSIONS

PRESETS: dict[str, list] = {
    "python": PYTHON_DIMENSIONS,
    "api": API_DIMENSIONS,
    "database": DATABASE_DIMENSIONS,
    "infrastructure": INFRASTRUCTURE_DIMENSIONS,
    "ml_pipeline": ML_PIPELINE_DIMENSIONS,
}

__all__ = ["PRESETS", "PYTHON_DIMENSIONS", "API_DIMENSIONS", "DATABASE_DIMENSIONS",
           "INFRASTRUCTURE_DIMENSIONS", "ML_PIPELINE_DIMENSIONS"]
