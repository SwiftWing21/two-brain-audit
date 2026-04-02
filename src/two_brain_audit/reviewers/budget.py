"""Per-session budget guard to prevent runaway API spend."""

from __future__ import annotations

import logging

log = logging.getLogger("two_brain_audit.reviewers")


class BudgetGuard:
    """Per-session cost cap to prevent runaway API spend."""

    def __init__(self, max_usd: float = 1.0) -> None:
        self.max_usd = max_usd
        self.spent_usd = 0.0

    def check(self, estimated_cost: float = 0.05) -> bool:
        """Return True if budget allows this call."""
        return (self.spent_usd + estimated_cost) <= self.max_usd

    def record(self, cost: float) -> None:
        """Record actual cost after a provider call."""
        self.spent_usd += cost

    @property
    def remaining(self) -> float:
        """Return remaining budget in USD."""
        return max(0.0, self.max_usd - self.spent_usd)
