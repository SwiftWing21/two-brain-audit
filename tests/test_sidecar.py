"""Tests for the JSON sidecar."""

import json
import pytest
from two_brain_audit.sidecar import Sidecar


@pytest.fixture
def sidecar(tmp_path):
    return Sidecar(tmp_path / "baseline.json")


class TestSidecar:
    def test_init_creates_file(self, sidecar):
        path = sidecar.init()
        assert path.exists()
        data = json.loads(path.read_text())
        assert "dimensions" in data
        assert "ratchets" in data

    def test_load_missing_returns_default(self, tmp_path):
        fresh = Sidecar(tmp_path / "nonexistent" / "baseline.json")
        data = fresh.load()
        assert data["dimensions"] == {}

    def test_set_and_get_grade(self, sidecar):
        sidecar.set_grade("testing", "A", source="human", notes="Good coverage")
        entry = sidecar.get_grade("testing")
        assert entry["grade"] == "A"
        assert entry["source"] == "human"

    def test_ratchet_lifecycle(self, sidecar):
        sidecar.init()
        assert sidecar.get_ratchet("security") is None
        sidecar.set_ratchet("security", "A-")
        assert sidecar.get_ratchet("security") == "A-"
        sidecar.remove_ratchet("security")
        assert sidecar.get_ratchet("security") is None

    def test_stale_grades(self, sidecar):
        sidecar.set_grade("old", "B", source="human")
        # Manually backdate
        data = sidecar.load()
        data["dimensions"]["old"]["updated"] = "2020-01-01"
        sidecar.save(data)
        stale = sidecar.stale_grades(max_age_days=30)
        assert "old" in stale

    def test_feedback_aggregate(self, sidecar):
        sidecar.init()
        sidecar.set_grade("ux", "B+")
        sidecar.update_feedback_aggregate(
            "ux", avg_score=0.76, sample_size=23, trend_7d=-0.04,
            recent_complaints=["slow load"],
        )
        entry = sidecar.get_grade("ux")
        assert entry["user_feedback"]["avg_score"] == 0.76
        assert entry["user_feedback"]["sample_size"] == 23
