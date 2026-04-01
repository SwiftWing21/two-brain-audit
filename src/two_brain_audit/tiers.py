"""Tier definitions and scheduling."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Tier(enum.Enum):
    """Audit depth tiers — higher tiers include everything from lower tiers."""

    LIGHT = "light"
    MEDIUM = "medium"
    DAILY = "daily"
    WEEKLY = "weekly"

    @property
    def depth(self) -> int:
        """Numeric depth for comparison (light=0, weekly=3)."""
        return list(Tier).index(self)

    def includes(self, other: Tier) -> bool:
        """True if this tier includes checks from `other`."""
        return self.depth >= other.depth


@dataclass(frozen=True)
class Schedule:
    """When a tier should be triggered automatically.

    hour/minute: time of day (24h).
    weekday: 0=Monday, 6=Sunday. None means every day.
    """

    tier: Tier
    hour: int = 3
    minute: int = 0
    weekday: int | None = None

    def matches(self, *, hour: int, minute: int, weekday: int) -> bool:
        """True if the given time matches this schedule."""
        if self.weekday is not None and weekday != self.weekday:
            return False
        return self.hour == hour and self.minute == minute


DEFAULT_SCHEDULES = [
    Schedule(tier=Tier.DAILY, hour=3, minute=0),
    Schedule(tier=Tier.WEEKLY, hour=3, minute=30, weekday=6),
]
