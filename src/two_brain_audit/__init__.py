"""Two-Brain Audit — dual-layer automated + manual audit system."""

import logging

from two_brain_audit.engine import AuditEngine, Dimension, DimensionResult
from two_brain_audit.grades import GRADE_TO_SCORE, grade_to_score, score_to_grade
from two_brain_audit.tiers import Tier

# Library best practice: NullHandler so users configure their own logging
logging.getLogger("two_brain_audit").addHandler(logging.NullHandler())

__all__ = [
    "AuditEngine",
    "Dimension",
    "DimensionResult",
    "GRADE_TO_SCORE",
    "Tier",
    "grade_to_score",
    "score_to_grade",
]

__version__ = "1.0.0"
