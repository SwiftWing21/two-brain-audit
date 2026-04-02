"""Optional Flask dashboard blueprint for the audit system.

Requires: pip install two-brain-audit[dashboard]

Serves both the JSON API and a single-page HTML dashboard at the root.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Blueprint

    from two_brain_audit.engine import AuditEngine


def create_blueprint(engine: AuditEngine, url_prefix: str = "/audit") -> Blueprint:
    """Create a Flask blueprint wired to the given AuditEngine.

    Endpoints:
        GET  /                — HTML dashboard UI
        GET  /scores          — latest score per dimension (JSON)
        GET  /scores/history  — time series (JSON)
        GET  /divergences     — active unacknowledged divergences (JSON)
        POST /acknowledge/<dim> — dismiss a divergence
        POST /trigger/<tier>  — run an on-demand audit tier
        GET  /baseline        — current manual grades from sidecar (JSON)
        POST /feedback        — submit user feedback
        GET  /feedback/summary — aggregated feedback stats (JSON)
        GET  /health          — quick health check for CI (JSON)
    """
    from flask import Blueprint, jsonify, request

    from two_brain_audit.dashboard.ui import render_dashboard

    bp = Blueprint("two_brain_audit", __name__, url_prefix=url_prefix)

    @bp.route("/")
    def index():
        return render_dashboard()

    @bp.route("/scores")
    def scores():
        results = engine.latest_scores()
        baseline = engine.sidecar.load()
        dims = baseline.get("dimensions", {})
        out = []
        for r in results:
            d = _result_dict(r)
            meta = dims.get(r.name, {})
            d["manual_source"] = meta.get("source")
            d["manual_updated"] = meta.get("updated")
            d["manual_notes"] = meta.get("notes")
            out.append(d)
        return jsonify(out)

    @bp.route("/scores/history")
    def scores_history():
        dim = request.args.get("dimension")
        try:
            days = max(1, min(365, int(request.args.get("days", 30))))
        except (ValueError, TypeError):
            days = 30
        return jsonify(engine.db.score_history(dimension=dim, days=days))

    @bp.route("/divergences")
    def divergences():
        include_ack = request.args.get("include_acknowledged", "").lower() == "true"
        results = engine.get_divergences(include_acknowledged=include_ack)
        return jsonify([_result_dict(r) for r in results])

    @bp.route("/acknowledge/<dimension>", methods=["POST"])
    def acknowledge(dimension: str):
        engine.acknowledge(dimension)
        return jsonify({"ok": True, "dimension": dimension})

    @bp.route("/trigger/<tier>", methods=["POST"])
    def trigger(tier: str):
        if tier not in ("light", "medium", "daily", "weekly"):
            return jsonify({"error": "Invalid tier"}), 400
        results = engine.run_tier(tier)
        return jsonify([_result_dict(r) for r in results])

    @bp.route("/baseline")
    def baseline():
        return jsonify(engine.sidecar.load())

    @bp.route("/feedback", methods=["POST"])
    def feedback():
        data = request.get_json(silent=True)
        if not data or "score" not in data:
            return jsonify({"error": "JSON body with 'score' field required"}), 400
        try:
            score = float(data["score"])
        except (ValueError, TypeError):
            return jsonify({"error": "score must be a number"}), 400
        if not 0.0 <= score <= 1.0:
            return jsonify({"error": "score must be between 0.0 and 1.0"}), 400
        row_id = engine.record_feedback(
            score=score,
            scope=data.get("scope", "overall"),
            text=data.get("text"),
            session_id=data.get("session_id"),
            actor=data.get("actor"),
        )
        return jsonify({"ok": True, "id": row_id})

    @bp.route("/feedback/summary")
    def feedback_summary():
        return jsonify(engine.feedback_summary())

    @bp.route("/health")
    def health():
        return jsonify(engine.health_check())

    @bp.route("/meta")
    def meta():
        import os
        return jsonify({
            "db_path": os.path.abspath(engine.db_path),
            "baseline_path": os.path.abspath(engine.baseline_path),
        })

    return bp


def _result_dict(r) -> dict:
    """Convert a DimensionResult to a JSON-safe dict."""
    return {
        "name": r.name,
        "auto_score": r.auto_score,
        "auto_detail": r.auto_detail,
        "auto_confidence": r.auto_confidence,
        "manual_grade": r.manual_grade,
        "manual_score": r.manual_score,
        "divergent": r.divergent,
        "acknowledged": r.acknowledged,
        "tier": r.tier,
        "timestamp": r.timestamp,
    }
