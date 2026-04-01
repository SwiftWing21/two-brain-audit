"""Tests for grade scale conversion."""

import pytest
from two_brain_audit.grades import grade_to_score, score_to_grade, is_failing


class TestGradeToScore:
    def test_s_grade(self):
        assert grade_to_score("S") == 1.00

    def test_a_grade(self):
        assert grade_to_score("A") == 0.90

    def test_f_grade(self):
        assert grade_to_score("F") == 0.30

    def test_unknown_grade(self):
        assert grade_to_score("Z") == 0.0

    def test_all_grades_descending(self):
        grades = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]
        scores = [grade_to_score(g) for g in grades]
        assert scores == sorted(scores, reverse=True)


class TestScoreToGrade:
    def test_perfect_score(self):
        assert score_to_grade(1.0) == "S"

    def test_zero_score(self):
        assert score_to_grade(0.0) == "F"

    def test_boundary_a(self):
        assert score_to_grade(0.90) == "A"

    def test_just_below_a(self):
        assert score_to_grade(0.865) == "A"  # within 0.035 tolerance

    def test_roundtrip(self):
        for grade in ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]:
            score = grade_to_score(grade)
            assert score_to_grade(score) == grade


class TestIsFailing:
    def test_d_is_failing(self):
        assert is_failing(0.50) is True

    def test_f_is_failing(self):
        assert is_failing(0.30) is True

    def test_c_is_not_failing(self):
        assert is_failing(0.60) is False

    def test_zero_is_failing(self):
        assert is_failing(0.0) is True
