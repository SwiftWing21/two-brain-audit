"""Tests for the reviewer system (cache, JSON parsing, providers)."""

import logging

from two_brain_audit.reviewers.budget import BudgetGuard
from two_brain_audit.reviewers.cache import ReviewCache
from two_brain_audit.reviewers.providers import (
    ClaudeProvider,
    GeminiProvider,
    OpenAIProvider,
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
