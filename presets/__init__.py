"""Preset dimension configurations for common project types."""

from presets.python_project import PYTHON_DIMENSIONS
from presets.api_service import API_DIMENSIONS
from presets.database import DATABASE_DIMENSIONS
from presets.infrastructure import INFRASTRUCTURE_DIMENSIONS
from presets.ml_pipeline import ML_PIPELINE_DIMENSIONS

PRESETS: dict[str, list] = {
    "python": PYTHON_DIMENSIONS,
    "api": API_DIMENSIONS,
    "database": DATABASE_DIMENSIONS,
    "infrastructure": INFRASTRUCTURE_DIMENSIONS,
    "ml_pipeline": ML_PIPELINE_DIMENSIONS,
}

__all__ = ["PRESETS", "PYTHON_DIMENSIONS", "API_DIMENSIONS", "DATABASE_DIMENSIONS",
           "INFRASTRUCTURE_DIMENSIONS", "ML_PIPELINE_DIMENSIONS"]
