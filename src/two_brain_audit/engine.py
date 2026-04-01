"""Core audit engine — dimension registry, scoring, reconciliation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from two_brain_audit.db import AuditDB
from two_brain_audit.grades import grade_to_score, is_failing, score_to_grade
from two_brain_audit.sidecar import Sidecar
from two_brain_audit.tiers import Tier

log = logging.getLogger("two_brain_audit")

# Default divergence threshold: flag when auto and manual disagree by > 0.15
# AND auto-confidence is high enough to trust the automated score.
DIVERGENCE_THRESHOLD = 0.15
CONFIDENCE_FLOOR = 0.5


@dataclass
class Dimension:
    """A single auditable dimension.

    Args:
        name: Unique identifier (e.g. "test_coverage", "security").
        check: Callable that returns (score: float 0.0-1.0, detail: dict).
        confidence: How much to trust the auto score (0.0-1.0).
        tier: Minimum tier required to run this check.
        description: Human-readable description.
    """

    name: str
    check: Callable[[], tuple[float, dict[str, Any]]]
    confidence: float = 0.75
    tier: Tier = Tier.LIGHT
    description: str = ""


@dataclass
class DimensionResult:
    """Result of scoring a single dimension."""

    name: str
    auto_score: float
    auto_detail: dict[str, Any]
    auto_confidence: float
    manual_grade: str | None
    manual_score: float | None
    divergent: bool
    acknowledged: bool
    tier: str
    timestamp: str = ""


@dataclass
class AuditEngine:
    """Main entry point — register dimensions, run tiers, reconcile.

    Args:
        db_path: Path to SQLite database file.
        baseline_path: Path to audit_baseline.json sidecar.
        divergence_threshold: Max allowed gap before flagging divergence.
        confidence_floor: Minimum auto-confidence to trigger divergence.
    """

    db_path: str = "audit.db"
    baseline_path: str = "audit_baseline.json"
    divergence_threshold: float = DIVERGENCE_THRESHOLD
    confidence_floor: float = CONFIDENCE_FLOOR
    _dimensions: dict[str, Dimension] = field(default_factory=dict, init=False, repr=False)
    _db: AuditDB | None = field(default=None, init=False, repr=False)
    _sidecar: Sidecar | None = field(default=None, init=False, repr=False)

    @property
    def db(self) -> AuditDB:
        if self._db is None:
            self._db = AuditDB(self.db_path)
        return self._db

    @property
    def sidecar(self) -> Sidecar:
        if self._sidecar is None:
            self._sidecar = Sidecar(self.baseline_path)
        return self._sidecar

    # ── Registration ─────────────────────────────────────────────────

    def register(self, dim: Dimension) -> None:
        """Register a dimension for auditing."""
        self._dimensions[dim.name] = dim

    def register_many(self, dims: list[Dimension]) -> None:
        """Register multiple dimensions at once."""
        for d in dims:
            self.register(d)

    def unregister(self, name: str) -> None:
        """Remove a dimension from the registry."""
        self._dimensions.pop(name, None)

    @property
    def dimensions(self) -> dict[str, Dimension]:
        """All registered dimensions."""
        return dict(self._dimensions)

    # ── Scoring ──────────────────────────────────────────────────────

    def run_tier(self, tier: Tier | str) -> list[DimensionResult]:
        """Run all dimensions at or below the given tier.

        Returns a list of DimensionResult with reconciliation status.
        """
        if isinstance(tier, str):
            tier = Tier(tier)

        baseline = self.sidecar.load()
        results: list[DimensionResult] = []
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        for name, dim in self._dimensions.items():
            if not tier.includes(dim.tier):
                continue

            try:
                auto_score, auto_detail = dim.check()
                auto_score = max(0.0, min(1.0, auto_score))
            except Exception as exc:
                log.warning("Dimension %s check failed: %s", name, exc)
                auto_score = 0.0
                auto_detail = {"error": str(exc)}

            # Manual grade from sidecar
            manual_entry = baseline.get("dimensions", {}).get(name, {})
            manual_grade = manual_entry.get("grade")
            manual_score = grade_to_score(manual_grade) if manual_grade else None

            # Divergence detection
            divergent = False
            if manual_score is not None and dim.confidence >= self.confidence_floor:
                divergent = abs(auto_score - manual_score) > self.divergence_threshold

            # Check if previously acknowledged
            acknowledged = self.db.is_acknowledged(name)

            result = DimensionResult(
                name=name,
                auto_score=auto_score,
                auto_detail=auto_detail,
                auto_confidence=dim.confidence,
                manual_grade=manual_grade,
                manual_score=manual_score,
                divergent=divergent,
                acknowledged=acknowledged,
                tier=tier.value,
                timestamp=ts,
            )
            results.append(result)

            # Persist
            self.db.write_score(result)

        return results

    def run_dimension(self, name: str) -> DimensionResult | None:
        """Run a single dimension regardless of tier. Returns None if not found."""
        dim = self._dimensions.get(name)
        if dim is None:
            return None
        # Temporarily run at weekly tier to bypass tier gating
        results = []
        baseline = self.sidecar.load()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            auto_score, auto_detail = dim.check()
            auto_score = max(0.0, min(1.0, auto_score))
        except Exception as exc:
            log.warning("Dimension %s check failed: %s", name, exc)
            auto_score = 0.0
            auto_detail = {"error": str(exc)}

        manual_entry = baseline.get("dimensions", {}).get(name, {})
        manual_grade = manual_entry.get("grade")
        manual_score = grade_to_score(manual_grade) if manual_grade else None

        divergent = False
        if manual_score is not None and dim.confidence >= self.confidence_floor:
            divergent = abs(auto_score - manual_score) > self.divergence_threshold

        result = DimensionResult(
            name=name,
            auto_score=auto_score,
            auto_detail=auto_detail,
            auto_confidence=dim.confidence,
            manual_grade=manual_grade,
            manual_score=manual_score,
            divergent=divergent,
            acknowledged=self.db.is_acknowledged(name),
            tier="single",
            timestamp=ts,
        )
        self.db.write_score(result)
        return result

    # ── Reconciliation ───────────────────────────────────────────────

    def get_divergences(self, *, include_acknowledged: bool = False) -> list[DimensionResult]:
        """Return all dimensions with active divergences."""
        return self.db.get_divergences(include_acknowledged=include_acknowledged)

    def acknowledge(self, dimension: str) -> None:
        """Acknowledge a divergence (dismiss without changing grade)."""
        self.db.acknowledge(dimension)

    # ── Feedback ─────────────────────────────────────────────────────

    def record_feedback(
        self,
        score: float,
        scope: str = "overall",
        text: str | None = None,
        session_id: str | None = None,
        actor: str | None = None,
    ) -> int:
        """Record user feedback. Returns the feedback row ID."""
        return self.db.write_feedback(
            score=max(0.0, min(1.0, score)),
            scope=scope,
            text=text,
            session_id=session_id,
            actor=actor,
        )

    def feedback_summary(self) -> dict[str, Any]:
        """Aggregated feedback statistics."""
        return self.db.feedback_summary()

    # ── Status ───────────────────────────────────────────────────────

    def latest_scores(self) -> list[DimensionResult]:
        """Get the most recent score for each dimension."""
        return self.db.latest_scores()

    def overall_score(self) -> float:
        """Weighted average of latest auto scores (equal weight)."""
        scores = self.latest_scores()
        if not scores:
            return 0.0
        return sum(r.auto_score for r in scores) / len(scores)

    def overall_grade(self) -> str:
        """Letter grade for the overall score."""
        return score_to_grade(self.overall_score())

    def health_check(self) -> dict[str, Any]:
        """Quick health summary for CI/smoke test integration.

        Returns:
            {ok: bool, grade: str, score: float, divergences: int, failing: list[str]}
        """
        scores = self.latest_scores()
        divergences = self.get_divergences()
        failing = [r.name for r in scores if is_failing(r.auto_score)]
        overall = self.overall_score()

        return {
            "ok": len(failing) == 0 and len(divergences) == 0,
            "grade": score_to_grade(overall),
            "score": round(overall, 3),
            "divergences": len(divergences),
            "failing": failing,
        }
