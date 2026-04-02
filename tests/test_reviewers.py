"""Tests for the reviewer system (cache, JSON parsing, providers)."""


from two_brain_audit.reviewers.cache import ReviewCache
from two_brain_audit.reviewers.providers import (
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
