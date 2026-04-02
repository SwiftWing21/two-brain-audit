"""Tests for the dashboard Flask blueprint."""


import pytest

from two_brain_audit import AuditEngine, Dimension, Tier
from two_brain_audit.dashboard import create_blueprint


@pytest.fixture
def app(tmp_path):
    from flask import Flask

    engine = AuditEngine(
        db_path=str(tmp_path / "test.db"),
        baseline_path=str(tmp_path / "baseline.json"),
    )
    engine.register(Dimension(
        name="alpha", check=lambda: (0.85, {"ok": True}),
        confidence=0.90, tier=Tier.LIGHT,
    ))
    engine.register(Dimension(
        name="beta", check=lambda: (0.60, {"ok": False}),
        confidence=0.75, tier=Tier.MEDIUM,
    ))
    engine.run_tier("medium")

    app = Flask("test")
    app.register_blueprint(create_blueprint(engine), url_prefix="/audit")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDashboardScores:
    def test_scores_returns_list(self, client):
        resp = client.get("/audit/scores")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        names = {d["name"] for d in data}
        assert names == {"alpha", "beta"}

    def test_scores_include_manual_fields(self, client):
        resp = client.get("/audit/scores")
        data = resp.get_json()
        for d in data:
            assert "manual_source" in d
            assert "manual_updated" in d


class TestDashboardHistory:
    def test_history_default(self, client):
        resp = client.get("/audit/scores/history")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_history_with_dimension(self, client):
        resp = client.get("/audit/scores/history?dimension=alpha&days=7")
        assert resp.status_code == 200

    def test_history_bad_days(self, client):
        resp = client.get("/audit/scores/history?days=abc")
        assert resp.status_code == 200  # falls back to 30


class TestDashboardTrigger:
    def test_trigger_light(self, client):
        resp = client.post("/audit/trigger/light")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_trigger_invalid_tier(self, client):
        resp = client.post("/audit/trigger/bogus")
        assert resp.status_code == 400
        assert "Invalid tier" in resp.get_json()["error"]


class TestDashboardFeedback:
    def test_submit_feedback(self, client):
        resp = client.post("/audit/feedback", json={"score": 0.8, "text": "good"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_feedback_missing_score(self, client):
        resp = client.post("/audit/feedback", json={"text": "no score"})
        assert resp.status_code == 400

    def test_feedback_out_of_range(self, client):
        resp = client.post("/audit/feedback", json={"score": 5.0})
        assert resp.status_code == 400

    def test_feedback_summary(self, client):
        client.post("/audit/feedback", json={"score": 0.8})
        resp = client.get("/audit/feedback/summary")
        assert resp.status_code == 200
        assert resp.get_json()["count"] >= 1


class TestDashboardOther:
    def test_health(self, client):
        resp = client.get("/audit/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ok" in data
        assert "grade" in data

    def test_baseline(self, client):
        resp = client.get("/audit/baseline")
        assert resp.status_code == 200

    def test_divergences(self, client):
        resp = client.get("/audit/divergences")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_acknowledge(self, client):
        resp = client.post("/audit/acknowledge/alpha")
        assert resp.status_code == 200

    def test_meta(self, client):
        resp = client.get("/audit/meta")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "db_path" in data

    def test_index_html(self, client):
        resp = client.get("/audit/")
        assert resp.status_code == 200
        assert b"Two-Brain" in resp.data
