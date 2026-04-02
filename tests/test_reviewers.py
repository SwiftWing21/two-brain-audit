"""Tests for the reviewer system (cache, JSON parsing, providers)."""

import logging

from two_brain_audit.reviewers.budget import BudgetGuard
from two_brain_audit.reviewers.cache import ReviewCache
from two_brain_audit.reviewers.providers import (
    ClaudeProvider,
    GeminiProvider,
    OpenAIProvider,
    ReviewResult,
    _calc_cost,
    _parse_review_json,
)


class TestReviewCache:
    def test_put_and_get(self, tmp_path):
        cache = ReviewCache(db_path=str(tmp_path / "cache.db"))
        key = cache.make_key("security", "context", "claude", "sonnet")
        cache.put(key, "security", "claude", "sonnet", {"grade": "A", "score": 0.9})
        result = cache.get(key)
        assert result is not None
        assert result["grade"] == "A"

    def test_cache_miss(self, tmp_path):
        cache = ReviewCache(db_path=str(tmp_path / "cache.db"))
        assert cache.get("nonexistent") is None

    def test_make_key_deterministic(self):
        k1 = ReviewCache.make_key("sec", "ctx", "claude", "sonnet")
        k2 = ReviewCache.make_key("sec", "ctx", "claude", "sonnet")
        assert k1 == k2

    def test_make_key_differs_by_provider(self):
        k1 = ReviewCache.make_key("sec", "ctx", "claude", "sonnet")
        k2 = ReviewCache.make_key("sec", "ctx", "gemini", "flash")
        assert k1 != k2

    def test_invalidate(self, tmp_path):
        cache = ReviewCache(db_path=str(tmp_path / "cache.db"))
        key = cache.make_key("sec", "ctx", "claude", "sonnet")
        cache.put(key, "sec", "claude", "sonnet", {"grade": "A"})
        count = cache.invalidate("sec")
        assert count == 1
        assert cache.get(key) is None

    def test_stats(self, tmp_path):
        cache = ReviewCache(db_path=str(tmp_path / "cache.db"))
        key = cache.make_key("sec", "ctx", "claude", "sonnet")
        cache.put(key, "sec", "claude", "sonnet", {"grade": "A"}, cost_usd=0.05)
        stats = cache.stats()
        assert stats["cached_reviews"] == 1
        assert stats["total_cost_saved_usd"] == 0.05


class TestParseReviewJson:
    def test_valid_json(self):
        result = _parse_review_json('{"grade": "A", "confidence": 0.8}', "test", "model")
        assert result["grade"] == "A"

    def test_markdown_wrapped_json(self):
        text = '```json\n{"grade": "B+", "confidence": 0.7}\n```'
        result = _parse_review_json(text, "test", "model")
        assert result["grade"] == "B+"

    def test_invalid_json_returns_fallback(self):
        result = _parse_review_json("not json at all", "test", "model")
        assert result["grade"] == "C"
        assert result["confidence"] == 0.3


class TestCalcCost:
    def test_known_model(self):
        cost = _calc_cost("claude-sonnet-4-6", 1000, 500)
        assert cost > 0

    def test_unknown_model(self):
        cost = _calc_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = _calc_cost("claude-sonnet-4-6", 0, 0)
        assert cost == 0.0


class TestProviderRepr:
    def test_claude_repr_masks_key(self):
        p = ClaudeProvider(api_key="sk-ant-api03-xxxxxxxxxxxxxxxxxxxx-yyyyyyyy")
        r = repr(p)
        assert "sk-ant-a" in r  # first 8 chars
        assert "yyyy" in r  # last 4 chars
        assert "xxxxxxxxxxxxxxxxxxxx" not in r

    def test_gemini_repr_masks_key(self):
        p = GeminiProvider(api_key="AIzaSyD-abcdefghijklmnop")
        r = repr(p)
        assert "AIzaSyD-" in r
        assert "abcdefghijklmnop" not in r

    def test_openai_repr_masks_key(self):
        p = OpenAIProvider(api_key="sk-proj-abcdefghijklmnop1234")
        r = repr(p)
        assert "sk-proj-" in r
        assert "abcdefghijklmnop" not in r

    def test_short_key_shows_stars(self):
        p = ClaudeProvider(api_key="short")
        r = repr(p)
        assert "***" in r
        assert "short" not in r


class TestKeyFormatWarning:
    def test_claude_warns_on_bad_prefix(self, caplog):
        with caplog.at_level(logging.WARNING, logger="two_brain_audit.reviewers"):
            ClaudeProvider(api_key="bad-key-format-xxxxxxxx")
        assert "unexpected format" in caplog.text

    def test_claude_no_warn_on_good_prefix(self, caplog):
        with caplog.at_level(logging.WARNING, logger="two_brain_audit.reviewers"):
            ClaudeProvider(api_key="sk-ant-valid-key-here")
        assert "unexpected format" not in caplog.text

    def test_gemini_warns_on_bad_prefix(self, caplog):
        with caplog.at_level(logging.WARNING, logger="two_brain_audit.reviewers"):
            GeminiProvider(api_key="bad-gemini-key-xxxxxx")
        assert "unexpected format" in caplog.text

    def test_openai_warns_on_bad_prefix(self, caplog):
        with caplog.at_level(logging.WARNING, logger="two_brain_audit.reviewers"):
            OpenAIProvider(api_key="bad-openai-key-xxxxxx")
        assert "unexpected format" in caplog.text

    def test_no_warn_on_empty_key(self, caplog):
        with caplog.at_level(logging.WARNING, logger="two_brain_audit.reviewers"):
            ClaudeProvider(api_key="")
        assert "unexpected format" not in caplog.text


class TestBudgetGuard:
    def test_check_allows_within_budget(self):
        bg = BudgetGuard(max_usd=1.0)
        assert bg.check(estimated_cost=0.50) is True

    def test_check_blocks_over_budget(self):
        bg = BudgetGuard(max_usd=1.0)
        bg.record(0.95)
        assert bg.check(estimated_cost=0.10) is False

    def test_record_tracks_spend(self):
        bg = BudgetGuard(max_usd=1.0)
        bg.record(0.30)
        bg.record(0.20)
        assert bg.spent_usd == 0.50

    def test_remaining_decreases(self):
        bg = BudgetGuard(max_usd=1.0)
        bg.record(0.60)
        assert bg.remaining == 0.40

    def test_remaining_never_negative(self):
        bg = BudgetGuard(max_usd=1.0)
        bg.record(1.50)
        assert bg.remaining == 0.0

    def test_exact_budget_allows(self):
        bg = BudgetGuard(max_usd=1.0)
        bg.record(0.95)
        assert bg.check(estimated_cost=0.05) is True

    def test_check_default_estimate(self):
        bg = BudgetGuard(max_usd=0.03)
        # default estimated_cost=0.05 exceeds 0.03
        assert bg.check() is False


# ── Cross-validation tests ──────────────────────────────────────────


class TestCrossValidation:
    """Test _cross_validate from oss_review."""

    def _make_result(self, findings: list[str], score: float = 0.8) -> ReviewResult:
        return ReviewResult(
            grade="B+",
            score=score,
            confidence=0.8,
            findings=findings,
            recommendations=[],
            model="test",
            provider="test",
        )

    def test_overlapping_findings_cross_validated(self):
        from two_brain_audit.reviewers.oss_review import _cross_validate

        lens_results = {
            "security_auditor": self._make_result(["SQL injection risk", "Missing auth"]),
            "performance_engineer": self._make_result(["SQL injection risk", "N+1 query"]),
        }
        cross, single = _cross_validate(lens_results)
        # "SQL injection risk" appears in both lenses
        normalized_cross = [f.lower().strip().rstrip(".") for f in cross]
        assert "sql injection risk" in normalized_cross
        assert len(cross) == 1
        # "Missing auth" and "N+1 query" are single-source
        single_findings = [s["finding"] for s in single]
        assert "Missing auth" in single_findings
        assert "N+1 query" in single_findings

    def test_single_source_has_lens_attribution(self):
        from two_brain_audit.reviewers.oss_review import _cross_validate

        lens_results = {
            "security_auditor": self._make_result(["Hardcoded secret"]),
            "software_architect": self._make_result(["High coupling"]),
        }
        cross, single = _cross_validate(lens_results)
        assert len(cross) == 0
        assert len(single) == 2
        lenses = {s["lens"] for s in single}
        assert "security_auditor" in lenses
        assert "software_architect" in lenses

    def test_normalized_dedup_case_insensitive(self):
        from two_brain_audit.reviewers.oss_review import _cross_validate

        lens_results = {
            "security_auditor": self._make_result(["SQL Injection Risk."]),
            "compliance_auditor": self._make_result(["sql injection risk"]),
        }
        cross, single = _cross_validate(lens_results)
        # Same finding after normalization -> cross-validated
        assert len(cross) == 1
        assert len(single) == 0

    def test_all_unique_findings(self):
        from two_brain_audit.reviewers.oss_review import _cross_validate

        lens_results = {
            "security_auditor": self._make_result(["Finding A"]),
            "performance_engineer": self._make_result(["Finding B"]),
            "software_architect": self._make_result(["Finding C"]),
        }
        cross, single = _cross_validate(lens_results)
        assert len(cross) == 0
        assert len(single) == 3


class TestConsensusReviewEdgeCases:
    """Test consensus_review with no providers."""

    def test_empty_providers_returns_error(self):
        from two_brain_audit.reviewers.consensus import consensus_review

        result = consensus_review("security", "some context", providers=[])
        assert result["consensus_score"] == 0.0
        assert "error" in result
        assert "No API keys" in result["error"]
        assert result["provider_results"] == {}
