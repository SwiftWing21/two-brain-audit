"""Claim schema and gap taxonomy for structured divergence analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

log = logging.getLogger("scorerift")

# Threshold for considering two claims "aligned" — matches engine.DIVERGENCE_THRESHOLD.
DIVERGENCE_THRESHOLD = 0.15

# Keywords that suggest the manual reviewer found qualitative issues
# the automated tool cannot detect.
_QUALITATIVE_KEYWORDS = frozenset({
    # Code quality concerns
    "technical debt", "complexity", "design", "coupling", "readability",
    "naming", "convention", "smell", "refactor", "unclear", "confusing",
    "hard to follow", "brittle", "fragile", "workaround", "hack",
    # Runtime / environmental concerns (context gaps)
    "thread", "concurren", "deploy", "runtime", "environment",
    "race condition", "state", "side effect",
})


class GapType(str, Enum):
    """Classification of the divergence between auto and manual claims."""

    stale_optimism = "stale_optimism"
    metric_blindness = "metric_blindness"
    false_positive = "false_positive"
    context_gap = "context_gap"
    agreement = "agreement"


class Severity(str, Enum):
    """Impact level of a divergence."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ClaimDimension(str, Enum):
    """Standard audit dimensions a claim can belong to."""

    security = "security"
    performance = "performance"
    correctness = "correctness"
    maintainability = "maintainability"
    test_coverage = "test_coverage"
    architecture = "architecture"
    thread_safety = "thread_safety"
    error_handling = "error_handling"


@dataclass
class Claim:
    """A single scored assertion about a file or project dimension."""

    source: str
    dimension: str
    statement: str
    confidence: float
    evidence: str
    file_path: str | None = None
    line_range: tuple[int, int] | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Divergence:
    """A typed gap between an automated claim and a manual claim."""

    gap_type: GapType
    severity: Severity
    dimension: str
    auto_claim: Claim | None
    manual_claim: Claim | None
    explanation: str
    file_path: str | None
    actionable: bool = True


def _has_qualitative_keywords(text: str) -> bool:
    """Check if text contains qualitative review keywords."""
    lower = text.lower()
    return any(kw in lower for kw in _QUALITATIVE_KEYWORDS)


def classify_divergence(
    auto: Claim | None,
    manual: Claim | None,
    *,
    last_review_timestamp: str | None = None,
    last_commit_timestamp: str | None = None,
) -> Divergence:
    """Compare one auto claim vs one manual claim on the same file+dimension.

    Returns a Divergence describing the gap type, severity, and explanation.
    """
    # Determine shared metadata
    dimension = (auto.dimension if auto else None) or (manual.dimension if manual else "unknown")
    file_path = (auto.file_path if auto else None) or (manual.file_path if manual else None)

    # One side missing → context gap
    if auto is None or manual is None:
        present = auto or manual
        side = "auto" if auto else "manual"
        return Divergence(
            gap_type=GapType.context_gap,
            severity=Severity.medium,
            dimension=dimension,
            auto_claim=auto,
            manual_claim=manual,
            explanation=f"Only {side} claim present ({present.statement if present else '?'})",
            file_path=file_path,
            actionable=True,
        )

    gap = abs(auto.confidence - manual.confidence)

    # Staleness check: if the last commit is newer than the last review,
    # the manual assessment may be outdated.
    if last_commit_timestamp and last_review_timestamp and last_commit_timestamp > last_review_timestamp:
            return Divergence(
                gap_type=GapType.stale_optimism,
                severity=Severity.medium,
                dimension=dimension,
                auto_claim=auto,
                manual_claim=manual,
                explanation=(
                    f"Last commit ({last_commit_timestamp}) is newer than "
                    f"last review ({last_review_timestamp}); manual score may be stale"
                ),
                file_path=file_path,
                actionable=True,
            )

    # Both present and aligned
    if gap <= DIVERGENCE_THRESHOLD:
        return Divergence(
            gap_type=GapType.agreement,
            severity=Severity.low,
            dimension=dimension,
            auto_claim=auto,
            manual_claim=manual,
            explanation="Auto and manual claims are aligned",
            file_path=file_path,
            actionable=False,
        )

    # Auto high, manual low
    if auto.confidence > manual.confidence:
        combined_evidence = f"{auto.evidence} {manual.evidence}"
        if _has_qualitative_keywords(combined_evidence):
            return Divergence(
                gap_type=GapType.context_gap,
                severity=Severity.high,
                dimension=dimension,
                auto_claim=auto,
                manual_claim=manual,
                explanation=(
                    "Auto rates higher than manual; qualitative concerns detected "
                    "that automated tooling cannot capture"
                ),
                file_path=file_path,
                actionable=True,
            )
        return Divergence(
            gap_type=GapType.metric_blindness,
            severity=Severity.medium,
            dimension=dimension,
            auto_claim=auto,
            manual_claim=manual,
            explanation=(
                f"Auto confidence ({auto.confidence:.2f}) exceeds manual "
                f"({manual.confidence:.2f}) by {gap:.2f}; metrics may miss issues"
            ),
            file_path=file_path,
            actionable=True,
        )

    # Auto low, manual high → false positive
    return Divergence(
        gap_type=GapType.false_positive,
        severity=Severity.low,
        dimension=dimension,
        auto_claim=auto,
        manual_claim=manual,
        explanation=(
            f"Manual confidence ({manual.confidence:.2f}) exceeds auto "
            f"({auto.confidence:.2f}); automated tool may be over-flagging"
        ),
        file_path=file_path,
        actionable=False,
    )


def classify_divergences(
    auto_claims: list[Claim],
    manual_claims: list[Claim],
    **kwargs: Any,
) -> list[Divergence]:
    """Batch-classify divergences by matching claims on (file_path, dimension).

    Extra keyword arguments are forwarded to classify_divergence().
    """
    # Index manual claims by (file_path, dimension)
    manual_index: dict[tuple[str | None, str], Claim] = {}
    for mc in manual_claims:
        manual_index[(mc.file_path, mc.dimension)] = mc

    seen_keys: set[tuple[str | None, str]] = set()
    divergences: list[Divergence] = []

    for ac in auto_claims:
        key = (ac.file_path, ac.dimension)
        seen_keys.add(key)
        mc = manual_index.get(key)
        divergences.append(classify_divergence(ac, mc, **kwargs))

    # Manual claims with no matching auto claim
    for key, mc in manual_index.items():
        if key not in seen_keys:
            divergences.append(classify_divergence(None, mc, **kwargs))

    return divergences


_SEVERITY_ICON = {
    Severity.critical: "\u2622\ufe0f",  # radioactive
    Severity.high: "\U0001f534",        # red circle
    Severity.medium: "\U0001f7e1",      # yellow circle
    Severity.low: "\U0001f7e2",         # green circle
}

_SEVERITY_ORDER = {
    Severity.critical: 0,
    Severity.high: 1,
    Severity.medium: 2,
    Severity.low: 3,
}


def tension_report(divergences: list[Divergence]) -> str:
    """Generate a markdown Tension Map sorted by severity, grouped by file."""
    if not divergences:
        return "# Tension Map\n\nNo divergences found.\n"

    # Sort by severity (most severe first), then by file path
    sorted_divs = sorted(
        divergences,
        key=lambda d: (_SEVERITY_ORDER.get(d.severity, 99), d.file_path or ""),
    )

    # Group by file
    groups: dict[str, list[Divergence]] = {}
    for div in sorted_divs:
        fp = div.file_path or "(project-level)"
        groups.setdefault(fp, []).append(div)

    lines: list[str] = ["# Tension Map\n"]

    for file_path, divs in groups.items():
        lines.append(f"## {file_path}\n")
        for div in divs:
            icon = _SEVERITY_ICON.get(div.severity, "?")
            action = "actionable" if div.actionable else "informational"
            lines.append(
                f"- {icon} **{div.severity.value.upper()}** "
                f"[{div.gap_type.value}] {div.dimension}: "
                f"{div.explanation} ({action})"
            )
        lines.append("")

    return "\n".join(lines)
