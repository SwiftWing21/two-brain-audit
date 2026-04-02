"""Multi-provider consensus — same dimension reviewed by N providers.

Runs the same prompt through Claude, Gemini, and OpenAI (whichever have
API keys configured), then compares their grades. Agreement = high
confidence. Disagreement = the interesting signal.

Supports:
- Parallel execution via ThreadPoolExecutor (all providers at once)
- Local caching (skip providers that already reviewed this exact context)
- Batch-friendly: collect all cache misses, run them, cache results
- Claude prompt caching via cache_control markers on stable content
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from two_brain_audit.grades import score_to_grade
from two_brain_audit.reviewers.budget import BudgetGuard  # noqa: TCH001
from two_brain_audit.reviewers.cache import ReviewCache  # noqa: TCH001
from two_brain_audit.reviewers.providers import (
    ReviewResult,
    build_review_prompt,
    get_available_providers,
)

log = logging.getLogger("two_brain_audit.reviewers")


def consensus_review(
    dimension: str,
    context: str,
    providers: list | None = None,
    cache: ReviewCache | None = None,
    parallel: bool = True,
    budget: BudgetGuard | None = None,
) -> dict[str, Any]:
    """Run the same review through multiple providers and compare.

    Args:
        dimension: What to review
        context: Project context
        providers: Provider instances (default: all available)
        cache: Review cache (default: None, no caching)
        parallel: Run providers in parallel (default: True)

    Returns:
        {
            "consensus_grade": "A-",
            "consensus_score": 0.85,
            "agreement": 0.92,  # 0-1, how much providers agree
            "provider_results": {
                "claude": {"grade": "A", "score": 0.90, ...},
                "gemini": {"grade": "A-", "score": 0.85, ...},
            },
            "merged_findings": ["finding1", ...],
            "total_cost_usd": 0.0234,
            "cache_hits": 1,
            "cache_misses": 2,
        }
    """
    if providers is None:
        providers = get_available_providers()

    if not providers:
        return {
            "consensus_grade": "--",
            "consensus_score": 0.0,
            "agreement": 0.0,
            "error": "No API keys configured. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY.",
            "provider_results": {},
            "total_cost_usd": 0.0,
        }

    system, user = build_review_prompt(dimension, context)

    # Check cache for each provider
    results: dict[str, ReviewResult] = {}
    to_run: list[Any] = []
    cache_hits = 0

    for provider in providers:
        if cache:
            key = cache.make_key(dimension, context, provider.name, provider.model)
            cached = cache.get(key)
            if cached:
                log.info("Cache hit for %s/%s on %s", provider.name, provider.model, dimension)
                cache_hits += 1
                from two_brain_audit.reviewers.providers import ReviewResult as RR
                results[provider.name] = RR(
                    grade=cached.get("grade", "C"),
                    score=cached.get("score", 0.6),
                    confidence=cached.get("confidence", 0.5),
                    findings=cached.get("findings", []),
                    recommendations=cached.get("recommendations", []),
                    model=cached.get("model", provider.model),
                    provider=provider.name,
                    cost_usd=0.0,  # cached = free
                )
                continue
        to_run.append(provider)

    # Filter providers that exceed budget
    if budget:
        allowed: list[Any] = []
        for p in to_run:
            if budget.check():
                allowed.append(p)
            else:
                log.warning("Budget exceeded, skipping %s (%s)", p.name, p.model)
        to_run = allowed

    # Run cache misses
    if parallel and len(to_run) > 1:
        with ThreadPoolExecutor(max_workers=len(to_run)) as pool:
            futures = {
                pool.submit(_run_provider, p, system, user): p
                for p in to_run
            }
            for future in as_completed(futures):
                provider = futures[future]
                try:
                    result = future.result()
                    results[provider.name] = result
                    if budget:
                        budget.record(result.cost_usd)
                    _cache_result(cache, dimension, context, provider, result)
                except Exception as exc:
                    log.warning("%s review failed: %s", provider.name, exc)
    else:
        for provider in to_run:
            if budget and not budget.check():
                log.warning("Budget exceeded, skipping %s (%s)", provider.name, provider.model)
                continue
            try:
                result = provider.review(system, user)
                results[provider.name] = result
                if budget:
                    budget.record(result.cost_usd)
                _cache_result(cache, dimension, context, provider, result)
            except Exception as exc:
                log.warning("%s review failed: %s", provider.name, exc)

    if not results:
        return {
            "consensus_grade": "--", "consensus_score": 0.0, "agreement": 0.0,
            "error": "All providers failed", "provider_results": {},
            "total_cost_usd": 0.0,
        }

    # Calculate consensus
    scores = [r.score for r in results.values() if r.score > 0]
    avg_score = 0.0 if not scores else sum(scores) / len(scores)

    # Agreement: 1.0 when all scores are identical, drops with spread
    if len(scores) >= 2:
        spread = max(scores) - min(scores)
        agreement = max(0.0, 1.0 - spread * 2)  # 0.5 spread = 0 agreement
    else:
        agreement = 0.5  # single provider = uncertain agreement

    # Merge findings (dedup by normalized text)
    merged_findings: list[str] = []
    seen: set[str] = set()
    for result in results.values():
        for f in result.findings:
            norm = f.lower().strip().rstrip(".")
            if norm not in seen:
                seen.add(norm)
                merged_findings.append(f)

    total_cost = sum(r.cost_usd for r in results.values())

    return {
        "consensus_grade": score_to_grade(avg_score),
        "consensus_score": round(avg_score, 3),
        "agreement": round(agreement, 3),
        "provider_results": {
            name: {
                "grade": r.grade,
                "score": r.score,
                "confidence": r.confidence,
                "findings": r.findings,
                "model": r.model,
                "cost_usd": r.cost_usd,
                "latency_ms": round(r.latency_ms, 1),
            }
            for name, r in results.items()
        },
        "merged_findings": merged_findings,
        "recommendations": _merge_recommendations(results),
        "total_cost_usd": round(total_cost, 6),
        "providers_run": len(results),
        "cache_hits": cache_hits,
        "cache_misses": len(to_run),
    }


def _run_provider(provider: Any, system: str, user: str) -> ReviewResult:
    """Run a single provider review (used in thread pool)."""
    return provider.review(system, user)


def _cache_result(
    cache: ReviewCache | None,
    dimension: str,
    context: str,
    provider: Any,
    result: ReviewResult,
) -> None:
    """Cache a provider result if cache is available."""
    if cache is None or not result.grade:
        return
    key = cache.make_key(dimension, context, provider.name, provider.model)
    cache.put(
        key=key,
        dimension=dimension,
        provider=provider.name,
        model=provider.model,
        result={
            "grade": result.grade,
            "score": result.score,
            "confidence": result.confidence,
            "findings": result.findings,
            "recommendations": result.recommendations,
            "model": result.model,
        },
        cost_usd=result.cost_usd,
    )


def _merge_recommendations(results: dict[str, ReviewResult]) -> list[str]:
    """Merge and dedup recommendations across providers."""
    recs: list[str] = []
    seen: set[str] = set()
    for result in results.values():
        for r in result.recommendations:
            norm = r.lower().strip().rstrip(".")
            if norm not in seen:
                seen.add(norm)
                recs.append(r)
    return recs
