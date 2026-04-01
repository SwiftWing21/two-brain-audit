"""Tests for feedback helpers."""

from two_brain_audit.feedback import NullClassifier, slider_to_score, star_to_score


class TestStarToScore:
    def test_1_star(self):
        assert star_to_score(1) == 0.2

    def test_5_stars(self):
        assert star_to_score(5) == 1.0

    def test_0_clamps(self):
        assert star_to_score(0) == 0.0

    def test_6_clamps(self):
        assert star_to_score(6) == 1.0


class TestSliderToScore:
    def test_100_percent(self):
        assert slider_to_score(100) == 1.0

    def test_50_percent(self):
        assert slider_to_score(50) == 0.5

    def test_1_percent_minimum(self):
        assert slider_to_score(0) == 0.01


class TestNullClassifier:
    def test_returns_empty(self):
        clf = NullClassifier()
        result = clf.classify("some text", ["testing", "security"])
        assert result == []
