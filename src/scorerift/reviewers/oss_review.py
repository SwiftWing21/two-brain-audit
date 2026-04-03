"""OSS Review — multi-lens swarm review with cross-validation.

4 specialized lenses review independently, then findings are
cross-validated. Findings that appear in multiple lenses get
marked as high-confidence. This is the "right brain on demand."

Single review: one provider, one lens (fast, cheap).
Swarm review: one provider, 4 lenses (thorough, cross-validated).
"""

from __future__ import annotations

import logging
from typing import Any

from scorerift.grades import score_to_grade
from scorerift.reviewers.providers import (
    ClaudeProvider,
    ReviewResult,
    build_review_prompt,
)

log = logging.getLogger("scorerift.reviewers")

# ── Specialized Lenses ───────────────────────────────────────────────

LENSES: dict[str, str] = {
    "security_auditor": (
        "You are a senior security auditor. Focus on: authentication flaws, "
        "injection vulnerabilities, hardcoded secrets, path traversal, unsafe "
        "deserialization, missing input validation, OWASP Top 10 violations."
    ),
    "performance_engineer": (
        "You are a performance engineer. Focus on: N+1 queries, missing indexes, "
        "unbounded loops, memory leaks, missing timeouts on I/O, blocking calls "
        "in async code, unnecessary allocations, cache opportunities."
    ),
    "software_architect": (
        "You are a senior software architect. Focus on: module coupling, single "
        "responsibility violations, API surface area, dependency hygiene, "
        "abstraction leaks, file size / complexity thresholds, extensibility."
    ),
    "compliance_auditor": (
        "You are a compliance auditor. Focus on: license compatibility, "
        "dependency supply chain risks, audit trail completeness, data handling "
        "practices, error logging quality, documentation currency."
    ),
}


def _normalize_finding(finding: str) -> str:
    """Normalize a finding string for dedup comparison."""
    return finding.lower().strip().rstrip(".")


# ── Single Review ────────────────────────────────────────────────────

def oss_review(
    dimension: str,
    context: str,
    provider: Any | None = None,
    lens: str | None = None,
) -> ReviewResult:
    """Run a single-lens review on a dimension.

    Args:
        dimension: What to review (e.g., "security", "architecture")
        context: Project context (code, file listings, etc.)
        provider: Provider instance (default: ClaudeProvider)
        lens: Optional lens name from LENSES dict
    """
    if provider is None:
        provider = ClaudeProvider()

    lens_prompt = LENSES.get(lens) if lens else None
    system, user = build_review_prompt(dimension, context, lens=lens_prompt)
    return provider.review(system, user)


# ── Swarm Review ─────────────────────────────────────────────────────

def swarm_review(
    dimension: str,
    context: str,
    provider: Any | None = None,
    lenses: list[str] | None = None,
) -> dict[str, Any]:
    """Run all lenses independently, then cross-validate findings.

    Each lens reviews the same context from its specialized perspective.
    Findings that appear in 2+ lenses are marked as cross-validated
    (higher confidence). Unique findings are kept but flagged as
    single-source.

    Args:
        dimension: What to review
        context: Project context
        provider: Provider instance (default: ClaudeProvider)
        lenses: Which lenses to use (default: all 4)

    Returns:
        {
            "grade": "A-",
            "score": 0.85,
            "confidence": 0.88,
            "lens_results": {lens_name: ReviewResult, ...},
            "cross_validated": ["finding that 2+ lenses agree on", ...],
            "single_source": [{"lens": "security", "finding": "..."}, ...],
            "all_findings": ["finding1", "finding2", ...],
            "recommendations": ["rec1", "rec2", ...],
            "total_cost_usd": 0.0123,
        }
    """
    if provider is None:
        provider = ClaudeProvider()

    if lenses is None:
        lenses = list(LENSES.keys())

    # Run each lens independently
    lens_results: dict[str, ReviewResult] = {}
    for lens_name in lenses:
        if lens_name not in LENSES:
            log.warning("Unknown lens: %s, skipping", lens_name)
            continue
        log.info("Running %s lens on %s", lens_name, dimension)
        result = oss_review(dimension, context, provider=provider, lens=lens_name)
        lens_results[lens_name] = result

    if not lens_results:
        return {"grade": "C", "score": 0.6, "confidence": 0.0,
                "error": "No lens results", "lens_results": {}}

    # Cross-validate findings
    cross_validated, single_source = _cross_validate(lens_results)

    # Aggregate scores (weighted by confidence)
    total_weight = 0.0
    weighted_score = 0.0
    for result in lens_results.values():
        w = result.confidence
        weighted_score += result.score * w
        total_weight += w

    avg_score = weighted_score / total_weight if total_weight > 0 else 0.5

    # Cross-validated findings boost confidence
    n_cross = len(cross_validated)
    n_total = n_cross + len(single_source)
    confidence_boost = (n_cross / n_total * 0.15) if n_total > 0 else 0.0
    avg_confidence = (total_weight / len(lens_results)) + confidence_boost
    avg_confidence = min(0.98, avg_confidence)

    # Dedup recommendations
    all_recs: list[str] = []
    seen_recs: set[str] = set()
    for result in lens_results.values():
        for rec in result.recommendations:
            norm = _normalize_finding(rec)
            if norm not in seen_recs:
                seen_recs.add(norm)
                all_recs.append(rec)

    # All findings (deduped)
    all_findings: list[str] = list(cross_validated)
    for item in single_source:
        all_findings.append(item["finding"])

    total_cost = sum(r.cost_usd for r in lens_results.values())

    return {
        "grade": score_to_grade(avg_score),
        "score": round(avg_score, 3),
        "confidence": round(avg_confidence, 3),
        "lens_results": {
            name: {
                "grade": r.grade, "score": r.score, "confidence": r.confidence,
                "findings": r.findings, "model": r.model, "cost_usd": r.cost_usd,
                "latency_ms": round(r.latency_ms, 1),
            }
            for name, r in lens_results.items()
        },
        "cross_validated": cross_validated,
        "single_source": single_source,
        "all_findings": all_findings,
        "recommendations": all_recs,
        "total_cost_usd": round(total_cost, 6),
        "lenses_run": len(lens_results),
    }


def _cross_validate(
    lens_results: dict[str, ReviewResult],
) -> tuple[list[str], list[dict[str, str]]]:
    """Compare findings across lenses.

    Returns:
        (cross_validated, single_source)
        cross_validated: findings that appear in 2+ lenses
        single_source: findings from only 1 lens, with lens attribution
    """
    # Build finding → set of lenses that found it
    finding_sources: dict[str, set[str]] = {}
    finding_original: dict[str, str] = {}  # normalized → original text

    for lens_name, result in lens_results.items():
        for finding in result.findings:
            norm = _normalize_finding(finding)
            if norm not in finding_sources:
                finding_sources[norm] = set()
                finding_original[norm] = finding
            finding_sources[norm].add(lens_name)

    cross_validated: list[str] = []
    single_source: list[dict[str, str]] = []

    for norm, sources in finding_sources.items():
        original = finding_original[norm]
        if len(sources) >= 2:
            cross_validated.append(original)
        else:
            single_source.append({
                "lens": next(iter(sources)),
                "finding": original,
            })

    return cross_validated, single_source
