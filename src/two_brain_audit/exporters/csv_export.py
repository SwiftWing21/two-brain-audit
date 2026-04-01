"""CSV report exporter."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from two_brain_audit.engine import AuditEngine


def export_csv(engine: AuditEngine, path: str | Path | None = None) -> str:
    """Export latest scores as CSV.

    If path is given, writes to file. Always returns the CSV string.
    """
    scores = engine.latest_scores()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "dimension", "auto_score", "auto_confidence",
        "manual_grade", "divergent", "tier", "timestamp",
    ])
    for s in scores:
        writer.writerow([
            s.name, f"{s.auto_score:.3f}", f"{s.auto_confidence:.2f}",
            s.manual_grade or "", s.divergent, s.tier, s.timestamp,
        ])

    output = buf.getvalue()
    if path:
        Path(path).write_text(output, encoding="utf-8")
    return output
