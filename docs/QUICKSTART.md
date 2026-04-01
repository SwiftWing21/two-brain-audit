# Quickstart

Get a working audit system in under 5 minutes.

---

## 1. Install

```bash
pip install two-brain-audit
```

For the web dashboard:
```bash
pip install two-brain-audit[dashboard]
```

For all integrations (GitHub, semgrep, PyPI):
```bash
pip install two-brain-audit[all]
```

---

## 2. Initialize

```bash
two-brain-audit init
```

This creates:
- `audit.db` — SQLite database for scores and feedback
- `audit_baseline.json` — JSON file for manual grades (the "right brain")

---

## 3. Register Dimensions

Pick a preset that matches your project type:

```bash
# Python project (test coverage, lint, types, deps, security, complexity, docs, imports)
two-brain-audit register --preset python

# REST API (endpoints, latency, errors, auth, schema, rate limits, CORS, TLS)
two-brain-audit register --preset api

# Database (schema, indexes, queries, backups, replication, pool, migrations)
two-brain-audit register --preset database

# Infrastructure (uptime, certs, resources, config drift, secrets, DNS, CDN, containers)
two-brain-audit register --preset infrastructure

# ML Pipeline (model freshness, data drift, latency, accuracy, features, GPU, experiments)
two-brain-audit register --preset ml_pipeline
```

Or register custom dimensions in Python:

```python
from two_brain_audit import AuditEngine, Dimension, Tier

engine = AuditEngine()

engine.register(Dimension(
    name="test_coverage",
    check=my_pytest_checker,    # any callable returning (float, dict)
    confidence=0.95,            # how much to trust the auto score
    tier=Tier.LIGHT,            # when to run (light/medium/daily/weekly)
))
```

---

## 4. Run Your First Audit

```bash
# Light tier — fast, deterministic counts (~2s)
two-brain-audit run light

# Medium tier — adds health probes and analysis (~10s)
two-brain-audit run medium

# See results
two-brain-audit status
```

Output:
```
Dimension                  Auto   Grade  Manual  Status
-----------------------------------------------------------------
  test_coverage            0.930      A      —   ok
  lint_score               1.000      S      —   ok
  type_coverage            0.720     B-      —   ok
  security                 0.500      D      —   ok

Overall: B+ (0.788)
```

---

## 5. Add Manual Grades (Right Brain)

Edit `audit_baseline.json` directly:

```json
{
  "version": "0.1.0",
  "dimensions": {
    "test_coverage": {
      "grade": "A",
      "source": "human",
      "updated": "2026-04-01",
      "notes": "Good coverage, few edge cases missing"
    },
    "security": {
      "grade": "A-",
      "source": "human",
      "updated": "2026-04-01",
      "notes": "Reviewed by security team, 2 low-priority items remaining"
    }
  },
  "ratchets": {}
}
```

Now the system compares both brains. If they disagree by more than 15% (and auto-confidence is high enough), a **divergence** is flagged:

```bash
two-brain-audit status
```
```
  security                 0.500      D     A-   DIVERGED
```

This means: "Auto says D, you said A-. Someone is wrong — investigate."

---

## 6. Resolve Divergences

Three options:

**A. Update your manual grade** — if auto is right:
```json
"security": { "grade": "D", "notes": "Auto was right, scanner found real issues" }
```

**B. Acknowledge** — you disagree with auto but don't want to be nagged:
```bash
# CLI
two-brain-audit acknowledge security

# Or via dashboard button
```

**C. Re-audit** — re-run the check to see if it resolves:
```bash
two-brain-audit run daily
```

---

## 7. Set Ratchets (Prevent Regression)

Add to `audit_baseline.json`:

```json
{
  "ratchets": {
    "test_coverage": "A",
    "security": "B+"
  }
}
```

If `test_coverage` drops below A (0.90), the system flags a warning. Ratchets are advisory by default — they warn but don't block.

---

## 8. Web Dashboard

```bash
two-brain-audit dashboard
# Opens at http://localhost:8484/audit/
```

The dashboard shows:
- **Grade ring** — overall score with letter grade
- **Stat cards** — dimensions, passing, divergences, failing, feedback count
- **Score table** — per-dimension bars with auto score, manual grade, status, confidence
- **Action buttons** — run any tier on demand
- **Feedback widget** — star rating + free text

Auto-refreshes every 30 seconds. Zero external dependencies.

---

## 9. Export Reports

```bash
# Markdown (great for PRs and docs)
two-brain-audit export markdown -o audit_report.md

# JSON (for CI pipelines)
two-brain-audit export json -o audit_report.json

# CSV (for spreadsheets)
two-brain-audit export csv -o audit_report.csv
```

---

## 10. CI Integration

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: Audit health check
  run: |
    pip install two-brain-audit
    two-brain-audit health
```

Exit code 0 = healthy, 1 = failing dimensions or unresolved divergences.

The JSON output is machine-readable:
```json
{
  "ok": false,
  "grade": "B+",
  "score": 0.788,
  "divergences": 1,
  "failing": ["security"]
}
```

---

## Python API

For programmatic use:

```python
from two_brain_audit import AuditEngine, Dimension, Tier

# Create engine
engine = AuditEngine(db_path="audit.db", baseline_path="audit_baseline.json")

# Register dimensions
engine.register(Dimension(
    name="uptime",
    check=lambda: (1.0 if ping_ok() else 0.0, {"host": "prod"}),
    confidence=0.95,
    tier=Tier.LIGHT,
))

# Run
results = engine.run_tier("daily")

# Check health
health = engine.health_check()
if not health["ok"]:
    alert_oncall(health)

# Record feedback
engine.record_feedback(score=0.8, text="Dashboard feels snappy today")

# Export
from two_brain_audit.exporters import export_markdown
print(export_markdown(engine))
```

---

## Flask Integration

Drop the dashboard into any existing Flask app:

```python
from flask import Flask
from two_brain_audit import AuditEngine
from two_brain_audit.dashboard import create_blueprint

app = Flask(__name__)
engine = AuditEngine()

# Mount at /audit/
app.register_blueprint(create_blueprint(engine), url_prefix="/audit")
```

---

## How It Works

```
  LEFT BRAIN (Auto)              RIGHT BRAIN (Manual)
  ─────────────────              ────────────────────
  pytest pass rate    ──┐    ┌── Human grade (A)
  ruff lint score     ──┤    ├── LLM review findings
  mypy type coverage  ──┤    ├── User feedback (4.2/5)
  semgrep scan        ──┘    └── Team notes
                        │    │
                        ▼    ▼
                    ┌──────────┐
                    │RECONCILER│
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Aligned    Diverged    Failing
           (green)    (yellow)     (red)
```

**Tiers** control depth — higher tiers include everything from lower:
```
weekly ⊃ daily ⊃ medium ⊃ light
```

**Divergence** is flagged when `|auto - manual| > 0.15` AND auto-confidence is above 50%. Low-confidence dimensions (like UX at 30%) can't trigger divergence because the auto score isn't trustworthy enough to argue with a human.

---

## File Reference

| File | What it is |
|------|-----------|
| `audit.db` | SQLite — scores history + user feedback (auto-created) |
| `audit_baseline.json` | Manual grades + ratchets (git-track this!) |

The sidecar is the only file you edit by hand. Everything else is managed by the engine.

---

## Next Steps

- Read [STANDARDS.md](STANDARDS.md) for what we measure and why (OWASP, SRE, DORA, etc.)
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
- Check `examples/biged/` for a 12-dimension reference implementation
- Browse `presets/` to see how dimensions are defined
- Browse `integrations/` to add external data sources
