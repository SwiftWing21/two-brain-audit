"""JSON report exporter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from two_brain_audit.engine import AuditEngine


def export_json(engine: AuditEngine, path: str | Path | None = None) -> str:
    """Export latest scores + health as a JSON report.

    If path is given, writes to file. Always returns the JSON string.
    """
    scores = engine.latest_scores()
    health = engine.health_check()

    report = {
        "health": health,
        "dimensions": [
            {
                "name": s.name,
                "auto_score": s.auto_score,
                "auto_confidence": s.auto_confidence,
                "manual_grade": s.manual_grade,
                "divergent": s.divergent,
                "tier": s.tier,
                "timestamp": s.timestamp,
            }
            for s in scores
        ],
        "feedback": engine.feedback_summary(),
    }

    output = json.dumps(report, indent=2, ensure_ascii=False)
    if path:
        Path(path).write_text(output + "\n", encoding="utf-8")
    return output
