"""Grade scale — letter grades ↔ numeric scores."""

from __future__ import annotations

GRADE_TO_SCORE: dict[str, float] = {
    "S": 1.00,
    "A+": 0.95,
    "A": 0.90,
    "A-": 0.85,
    "B+": 0.80,
    "B": 0.75,
    "B-": 0.70,
    "C+": 0.65,
    "C": 0.60,
    "D": 0.50,
    "F": 0.30,
}

_SCORE_THRESHOLDS = sorted(GRADE_TO_SCORE.items(), key=lambda x: x[1], reverse=True)

# D and below are failing grades
FAILING_THRESHOLD = 0.50


def grade_to_score(grade: str) -> float:
    """Convert a letter grade to its numeric score (0.0-1.0).

    Returns 0.0 for unrecognized grades.
    """
    return GRADE_TO_SCORE.get(grade, 0.0)


def score_to_grade(score: float) -> str:
    """Convert a numeric score to the nearest letter grade.

    Uses a half-step tolerance of 0.035 for intuitive rounding across
    the full scale (S needs score >= 0.965, A+ >= 0.915, etc.).
    """
    for grade, threshold in _SCORE_THRESHOLDS:
        if score >= threshold - 0.035:
            return grade
    return "F"


def is_failing(score: float) -> bool:
    """True if the score maps to D or below."""
    return score <= FAILING_THRESHOLD
