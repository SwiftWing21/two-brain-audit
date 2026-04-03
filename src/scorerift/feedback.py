"""User feedback collection and optional LLM-based dimension classification."""

from __future__ import annotations

import logging
from typing import Any, Protocol

log = logging.getLogger("scorerift")


class LLMClassifier(Protocol):
    """Protocol for LLM-based feedback text classification.

    Implementations should take raw feedback text and return a list of
    {dimension, confidence} dicts mapping the text to audit dimensions.
    """

    def classify(self, text: str, dimensions: list[str]) -> list[dict[str, Any]]:
        """Classify text into audit dimensions.

        Args:
            text: Raw user feedback text.
            dimensions: Available dimension names to classify into.

        Returns:
            List of {"dimension": str, "confidence": float} dicts.
        """
        ...


class NullClassifier:
    """No-op classifier — returns empty list. Default when no LLM is configured."""

    def classify(self, text: str, dimensions: list[str]) -> list[dict[str, Any]]:
        return []


def star_to_score(stars: int) -> float:
    """Convert 1-5 star rating to 0.0-1.0 score."""
    return max(0.0, min(1.0, stars * 0.2))


def slider_to_score(pct: int) -> float:
    """Convert 1-100 slider value to 0.0-1.0 score."""
    return max(0.01, min(1.0, pct / 100.0))
