"""JSON sidecar for manual grades (audit_baseline.json)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("two_brain_audit")

DEFAULT_BASELINE: dict[str, Any] = {
    "version": "0.1.0",
    "dimensions": {},
    "ratchets": {},
}


class Sidecar:
    """Read/write manual grades from a JSON sidecar file.

    The sidecar is the right-brain's persistent state. It holds:
    - Manual grades per dimension (grade, source, updated, notes, findings)
    - Ratchet targets (minimum allowed grade per dimension)
    - User feedback aggregates (avg_score, sample_size, trend)
    """

    def __init__(self, path: str | Path = "audit_baseline.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        """Load the sidecar. Returns default if file doesn't exist."""
        if not self.path.exists():
            import copy
            return copy.deepcopy(DEFAULT_BASELINE)
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            log.warning("Failed to parse %s", self.path, exc_info=True)
            return dict(DEFAULT_BASELINE)

    def save(self, data: dict[str, Any]) -> None:
        """Write sidecar back to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def init(self) -> Path:
        """Create a default sidecar file if it doesn't exist. Returns the path."""
        if not self.path.exists():
            self.save(DEFAULT_BASELINE)
        return self.path

    # ── Grade Management ─────────────────────────────────────────────

    def get_grade(self, dimension: str) -> dict[str, Any] | None:
        """Get the manual grade entry for a dimension."""
        data = self.load()
        return data.get("dimensions", {}).get(dimension)

    def set_grade(
        self,
        dimension: str,
        grade: str,
        source: str = "human",
        notes: str = "",
        **kwargs: Any,
    ) -> None:
        """Set or update a manual grade for a dimension."""
        data = self.load()
        dims = data.setdefault("dimensions", {})
        entry = dims.get(dimension, {})
        entry.update({
            "grade": grade,
            "source": source,
            "updated": time.strftime("%Y-%m-%d"),
            "notes": notes,
            **kwargs,
        })
        dims[dimension] = entry
        self.save(data)

    # ── Ratchets ─────────────────────────────────────────────────────

    def get_ratchet(self, dimension: str) -> str | None:
        """Get the ratchet floor grade for a dimension. None = no ratchet."""
        data = self.load()
        return data.get("ratchets", {}).get(dimension)

    def set_ratchet(self, dimension: str, grade: str) -> None:
        """Set or update a ratchet target grade."""
        data = self.load()
        ratchets = data.setdefault("ratchets", {})
        ratchets[dimension] = grade
        self.save(data)

    def remove_ratchet(self, dimension: str) -> None:
        """Remove a ratchet target."""
        data = self.load()
        data.get("ratchets", {}).pop(dimension, None)
        self.save(data)

    # ── Feedback Aggregation ─────────────────────────────────────────

    def update_feedback_aggregate(
        self,
        dimension: str,
        avg_score: float,
        sample_size: int,
        trend_7d: float = 0.0,
        recent_complaints: list[str] | None = None,
    ) -> None:
        """Update the user_feedback field on a dimension entry."""
        data = self.load()
        dims = data.setdefault("dimensions", {})
        entry = dims.setdefault(dimension, {})
        entry["user_feedback"] = {
            "avg_score": round(avg_score, 3),
            "sample_size": sample_size,
            "last_7d_trend": round(trend_7d, 3),
            "recent_complaints": recent_complaints or [],
        }
        self.save(data)

    # ── Staleness Detection ──────────────────────────────────────────

    def stale_grades(self, max_age_days: int = 30) -> list[str]:
        """Return dimension names with grades older than max_age_days."""
        import datetime

        data = self.load()
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=max_age_days)).strftime("%Y-%m-%d")
        stale = []
        for name, entry in data.get("dimensions", {}).items():
            updated = entry.get("updated", "")
            if updated and updated < cutoff:
                stale.append(name)
        return stale
