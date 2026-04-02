"""CLI entry point — two-brain-audit command."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from two_brain_audit.engine import AuditEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="two-brain-audit",
        description="Dual-layer audit: automated scoring + manual grading + reconciliation.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command")

    # ── init ──────────────────────────────────────────────────────────
    p_init = sub.add_parser("init", help="Initialize audit DB and baseline sidecar")
    p_init.add_argument("--db", default="audit.db", help="SQLite DB path (default: audit.db)")
    p_init.add_argument("--baseline", default="audit_baseline.json", help="Sidecar path")

    # ── register ─────────────────────────────────────────────────────
    p_reg = sub.add_parser("register", help="Register a preset dimension set")
    p_reg.add_argument(
        "--preset", required=True,
        choices=["python", "api", "database", "infrastructure", "ml_pipeline"],
    )
    p_reg.add_argument("--db", default="audit.db")
    p_reg.add_argument("--baseline", default="audit_baseline.json")
    p_reg.add_argument("--target", "-t", default=".", help="Target project directory (default: CWD)")

    # ── run ───────────────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Run an audit tier")
    p_run.add_argument("tier", choices=["light", "medium", "daily", "weekly"])
    p_run.add_argument("--db", default="audit.db")
    p_run.add_argument("--baseline", default="audit_baseline.json")
    p_run.add_argument("--target", "-t", default=".", help="Target project directory (default: CWD)")

    # ── status ────────────────────────────────────────────────────────
    p_status = sub.add_parser("status", help="Show latest scores and divergences")
    p_status.add_argument("--db", default="audit.db")
    p_status.add_argument("--baseline", default="audit_baseline.json")
    p_status.add_argument("--json", action="store_true", help="Output as JSON")
    p_status.add_argument("--target", "-t", default=".", help="Target project directory (default: CWD)")

    # ── health ────────────────────────────────────────────────────────
    p_health = sub.add_parser("health", help="Quick health check (CI-friendly)")
    p_health.add_argument("--db", default="audit.db")
    p_health.add_argument("--baseline", default="audit_baseline.json")
    p_health.add_argument("--target", "-t", default=".", help="Target project directory (default: CWD)")

    # ── export ────────────────────────────────────────────────────────
    p_export = sub.add_parser("export", help="Export scores as JSON/CSV/Markdown")
    p_export.add_argument("format", choices=["json", "csv", "markdown"])
    p_export.add_argument("--output", "-o", help="Output file path (default: stdout)")
    p_export.add_argument("--db", default="audit.db")
    p_export.add_argument("--baseline", default="audit_baseline.json")

    # ── dashboard ─────────────────────────────────────────────────────
    p_dash = sub.add_parser("dashboard", help="Start the web dashboard")
    p_dash.add_argument("--port", type=int, default=8484)
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--native", action="store_true", help="Open in a native PyWebView window instead of browser")
    p_dash.add_argument("--db", default="audit.db")
    p_dash.add_argument("--baseline", default="audit_baseline.json")

    args = parser.parse_args(argv)

    # Configure logging
    level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    if not args.command:
        parser.print_help()
        return 0

    # ── Dispatch ─────────────────────────────────────────────────────
    from two_brain_audit import AuditEngine

    if args.command == "init":
        return _cmd_init(args)

    target = getattr(args, "target", ".")
    engine = AuditEngine(db_path=args.db, baseline_path=args.baseline, target_path=target)

    # Auto-load preset from saved project config (if exists)
    _auto_load_preset(engine, target)

    if args.command == "register":
        return _cmd_register(engine, args)
    elif args.command == "run":
        return _cmd_run(engine, args)
    elif args.command == "status":
        return _cmd_status(engine, args)
    elif args.command == "health":
        return _cmd_health(engine, args)
    elif args.command == "export":
        return _cmd_export(engine, args)
    elif args.command == "dashboard":
        return _cmd_dashboard(engine, args)

    return 0


def _auto_load_preset(engine: AuditEngine, target: str) -> None:
    """Auto-register dimensions from saved .two-brain-audit.json config."""
    import json
    from pathlib import Path

    config_path = Path(target).resolve() / ".two-brain-audit.json"
    if not config_path.exists():
        return
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        preset_name = config.get("preset")
        if preset_name and not engine.dimensions:
            from two_brain_audit.presets import PRESETS
            dims = PRESETS.get(preset_name, [])
            if dims:
                engine.register_many(dims)
    except Exception:  # noqa: S110
        pass


def _cmd_init(args: argparse.Namespace) -> int:
    from two_brain_audit.db import AuditDB
    from two_brain_audit.sidecar import Sidecar

    db = AuditDB(args.db)
    sidecar = Sidecar(args.baseline)
    sidecar.init()
    counts = db.row_count()
    print(f"Initialized: {args.db} ({counts['audit_scores']} scores, {counts['user_feedback']} feedback)")
    print(f"Sidecar: {sidecar.path}")
    return 0


def _cmd_register(engine: AuditEngine, args: argparse.Namespace) -> int:
    from two_brain_audit.presets import PRESETS

    dims = PRESETS.get(args.preset)
    if not dims:
        print(f"Unknown preset: {args.preset}", file=sys.stderr)
        return 1
    engine.register_many(dims)
    print(f"Registered {len(dims)} dimensions from '{args.preset}' preset:")
    for d in dims:
        print(f"  {d.name} ({d.tier.value}, confidence={d.confidence})")
    import json
    from pathlib import Path
    target = getattr(args, "target", ".")
    config_path = Path(target).resolve() / ".two-brain-audit.json"
    config = {"preset": args.preset, "created": True}
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return 0


def _cmd_run(engine: AuditEngine, args: argparse.Namespace) -> int:
    results = engine.run_tier(args.tier)
    if not results:
        print("No dimensions registered. Use 'register --preset <name>' first.")
        return 1
    print(f"Ran {args.tier} tier — {len(results)} dimensions scored:")
    for r in results:
        status = "DIVERGED" if r.divergent else "ok"
        manual = r.manual_grade or "—"
        print(f"  {r.name:25s}  auto={r.auto_score:.3f}  manual={manual:3s}  [{status}]")
    return 0


def _cmd_status(engine: AuditEngine, args: argparse.Namespace) -> int:
    scores = engine.latest_scores()
    if not scores:
        print("No scores yet. Run 'two-brain-audit run light' first.")
        return 0

    if args.json:
        import json
        data = [{"name": s.name, "auto_score": s.auto_score, "manual_grade": s.manual_grade,
                 "divergent": s.divergent, "tier": s.tier} for s in scores]
        print(json.dumps(data, indent=2))
        return 0

    from two_brain_audit.grades import score_to_grade

    print(f"{'Dimension':25s}  {'Auto':>6s}  {'Grade':>5s}  {'Manual':>6s}  Status")
    print("-" * 65)
    for s in scores:
        grade = score_to_grade(s.auto_score)
        manual = s.manual_grade or "—"
        status = "DIVERGED" if s.divergent else ("ack" if s.acknowledged else "ok")
        print(f"  {s.name:25s}  {s.auto_score:6.3f}  {grade:>5s}  {manual:>6s}  {status}")

    overall = engine.overall_score()
    print(f"\nOverall: {engine.overall_grade()} ({overall:.3f})")

    divergences = engine.get_divergences()
    if divergences:
        print(f"Active divergences: {len(divergences)}")
    return 0


def _cmd_health(engine: AuditEngine, args: argparse.Namespace) -> int:
    import json
    health = engine.health_check()
    print(json.dumps(health, indent=2))
    return 0 if health["ok"] else 1


def _cmd_export(engine: AuditEngine, args: argparse.Namespace) -> int:
    from two_brain_audit.exporters import export_csv, export_json, export_markdown

    exporters = {"json": export_json, "csv": export_csv, "markdown": export_markdown}
    output = exporters[args.format](engine, path=args.output)
    if not args.output:
        print(output)
    else:
        print(f"Exported to {args.output}")
    return 0


def _cmd_dashboard(engine: AuditEngine, args: argparse.Namespace) -> int:
    if args.native:
        from two_brain_audit.app import launch
        launch(engine, port=args.port)
        return 0

    try:
        from flask import Flask

        from two_brain_audit.dashboard import create_blueprint
    except ImportError:
        print("Dashboard requires Flask: pip install two-brain-audit[dashboard]", file=sys.stderr)
        return 1

    import threading
    import webbrowser

    app = Flask("two_brain_audit")
    app.register_blueprint(create_blueprint(engine))

    url = f"http://{args.host}:{args.port}/audit/"
    print(f"Dashboard: {url}")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
