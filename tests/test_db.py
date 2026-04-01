"""Tests for the audit database layer."""

import pytest

from two_brain_audit.db import AuditDB


@pytest.fixture
def db(tmp_path):
    return AuditDB(str(tmp_path / "test.db"))


class TestAuditDB:
    def test_schema_created(self, db):
        counts = db.row_count()
        assert counts["audit_scores"] == 0
        assert counts["user_feedback"] == 0

    def test_write_and_read_feedback(self, db):
        row_id = db.write_feedback(score=0.8, scope="overall", text="Nice work")
        assert row_id > 0
        summary = db.feedback_summary()
        assert summary["count"] == 1
        assert summary["avg_score"] == 0.8

    def test_score_history_empty(self, db):
        history = db.score_history(days=30)
        assert history == []

    def test_acknowledge_missing_dimension(self, db):
        # Should not raise
        db.acknowledge("nonexistent")
        assert db.is_acknowledged("nonexistent") is False
