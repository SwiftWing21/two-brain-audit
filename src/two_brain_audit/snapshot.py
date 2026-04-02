"""Snapshot writer — timestamped sanitized audit exports."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from two_brain_audit.sanitizer import SanitizeConfig, load_config, sanitize, sanitize_text

if TYPE_CHECKING:
    from two_brain_audit.engine import AuditEngine

log = logging.getLogger("two_brain_audit")

_FORMAT_EXT = {"json": "json", "csv": "csv", "markdown": "md"}


def export_snapshot(
    engine: AuditEngine,
    output_dir: str | Path = "audit-snapshots",
    fmt: str = "json",
    sanitize_output: bool = True,
) -> Path:
    """Write a timestamped, optionally sanitized export to *output_dir*.

    Args:
        engine: Initialized AuditEngine with scores.
        output_dir: Directory for snapshots (created if needed).
        fmt: Export format — ``"json"``, ``"csv"``, or ``"markdown"``.
        sanitize_output: Whether to run the sanitizer on the output.

    Returns:
        Path to the written snapshot file.
    """
    from two_brain_audit.exporters import export_csv, export_json, export_markdown

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ext = _FORMAT_EXT.get(fmt, fmt)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{ts}.{ext}"
    filepath = out / filename

    exporters = {"json": export_json, "csv": export_csv, "markdown": export_markdown}
    exporter = exporters[fmt]
    raw_output = exporter(engine)

    config: SanitizeConfig | None = None
    if sanitize_output:
        config = load_config() or SanitizeConfig()

    if sanitize_output and fmt == "json":
        data = json.loads(raw_output)
        data = sanitize(data, config)
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    elif sanitize_output:
        content = sanitize_text(raw_output, config)
    else:
        content = raw_output

    filepath.write_text(content, encoding="utf-8")
    log.info("Snapshot written: %s", filepath)

    # Build manifest entry
    health = engine.health_check()
    scores = engine.latest_scores()
    entry: dict[str, Any] = {
        "file": filename,
        "format": fmt,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "overall_grade": health.get("grade", "?"),
        "overall_score": health.get("score", 0.0),
        "dimensions_count": len(scores),
        "sanitized": sanitize_output,
    }
    update_manifest(out, entry)

    return filepath


def update_manifest(output_dir: Path, entry: dict[str, Any]) -> None:
    """Append *entry* to the manifest file in *output_dir*."""
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Corrupt manifest at %s, starting fresh", manifest_path)
            manifest = {"snapshots": []}
    else:
        manifest = {"snapshots": []}

    manifest["snapshots"].append(entry)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    log.info("Manifest updated: %s", manifest_path)


def list_snapshots(output_dir: str | Path = "audit-snapshots") -> list[dict[str, Any]]:
    """Read and return snapshot entries from the manifest."""
    manifest_path = Path(output_dir) / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest.get("snapshots", [])
    except Exception:
        log.warning("Failed to read manifest at %s", manifest_path)
        return []
