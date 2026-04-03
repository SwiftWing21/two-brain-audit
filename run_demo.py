"""Quick demo — launches dashboard in a native window with sample dimensions."""
import sys
sys.path.insert(0, "src")

from scorerift import AuditEngine, Dimension, Tier

engine = AuditEngine(db_path="demo_audit.db", baseline_path="demo_baseline.json")

# Register some demo dimensions with real-ish scores
engine.register(Dimension(name="test_coverage", check=lambda: (0.93, {"passed": 93, "failed": 7}), confidence=0.95, tier=Tier.LIGHT, description="pytest pass rate"))
engine.register(Dimension(name="lint_score", check=lambda: (1.0, {"errors": 0}), confidence=0.90, tier=Tier.LIGHT, description="ruff clean"))
engine.register(Dimension(name="type_coverage", check=lambda: (0.72, {"errors": 28}), confidence=0.85, tier=Tier.MEDIUM, description="mypy coverage"))
engine.register(Dimension(name="security", check=lambda: (0.85, {"findings": 2}), confidence=0.60, tier=Tier.DAILY, description="semgrep scan"))
engine.register(Dimension(name="documentation", check=lambda: (0.78, {"stale_refs": 3}), confidence=0.80, tier=Tier.MEDIUM, description="doc freshness"))
engine.register(Dimension(name="performance", check=lambda: (0.91, {"p95_ms": 142}), confidence=0.85, tier=Tier.MEDIUM, description="endpoint latency"))
engine.register(Dimension(name="reliability", check=lambda: (0.88, {"healthy": 7, "total": 8}), confidence=0.85, tier=Tier.MEDIUM, description="agent health"))
engine.register(Dimension(name="architecture", check=lambda: (0.82, {"large_files": 2}), confidence=0.75, tier=Tier.MEDIUM, description="LOC scan"))

# Set some manual grades to show divergence
engine.sidecar.init()
engine.sidecar.set_grade("test_coverage", "A", source="human", notes="Good coverage, few edge cases missing")
engine.sidecar.set_grade("security", "A+", source="human", notes="Full review done by security team")  # will diverge with 0.85 auto
engine.sidecar.set_grade("documentation", "A", source="human", notes="Recently updated all docstrings")
engine.sidecar.set_grade("performance", "A-", source="llm_review", notes="Claude review: p95 within SLA")

# Run a scan to seed the DB
engine.run_tier("medium")
print("Seeded DB with scores")

# Launch in native window (falls back to browser if pywebview missing)
from scorerift.app import launch
launch(engine)
