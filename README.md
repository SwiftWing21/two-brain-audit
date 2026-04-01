# Two-Brain Audit

A dual-layer audit system that combines automated quantitative scoring (**left brain**) with manual qualitative grading (**right brain**) and reconciles them automatically.

## Why Two Brains?

Neither automated scoring nor manual review alone is sufficient:

| Scenario | Auto catches it | Manual catches it |
|----------|:-:|:-:|
| Test coverage drops silently | Yes | Maybe (if reviewer checks) |
| "Feels slow" but metrics are fine | No | Yes |
| Stale manual grade after major refactor | Yes (divergence) | No (grade looks fine) |
| Security vuln in dependency | Yes (scanner) | No (invisible) |
| UX regression that tests can't express | No | Yes |
| Reviewer optimism ("looks good to me") | Yes (cross-validation) | No |

The two-brain pattern ensures every dimension is checked from both sides, and disagreements surface automatically.

## Quick Start

```bash
pip install two-brain-audit

# Initialize in your project
two-brain-audit init                          # creates audit_baseline.json + SQLite DB
two-brain-audit register --preset python      # register Python project dimensions
two-brain-audit run light                     # first scan
two-brain-audit status                        # view scores + divergences

# Optional web dashboard
pip install two-brain-audit[dashboard]
two-brain-audit dashboard                     # starts on http://localhost:8484
```

## Concepts

### Dimensions
What you're measuring. Each dimension has a **check function** (returns 0.0-1.0 score) and an **auto-confidence** rating. Examples: test coverage, security posture, documentation freshness.

### Tiers
How deep to check. Higher tiers include everything from lower tiers:

| Tier | Typical trigger | Latency | What it adds |
|------|----------------|---------|-------------|
| **Light** | Every CI run / smoke test | ~2s | Deterministic counts (test pass rate, file existence) |
| **Medium** | On-demand button/CLI | ~10s | Health probes, dependency checks, git diff analysis |
| **Daily** | Scheduled (3 AM) | ~20s | Reconciliation, stale grade detection, ratchet check |
| **Weekly** | Scheduled (Sunday) | ~45s | External scanners, version drift, API checks |

### Sidecar (`audit_baseline.json`)
JSON file for manual grades. Three source types:
- **human** — direct JSON edit by a reviewer
- **llm_review** — external LLM review (structured prompt, single API call)
- **user_feedback** — aggregated from the feedback system

### Reconciliation
Auto vs manual comparison runs on every daily+ tier. Divergence flagged when `abs(auto_score - manual_numeric) > 0.15` AND `auto_confidence >= 0.5`.

Three resolution paths:
1. **Update manual grade** — edit sidecar, divergence clears next run
2. **Acknowledge** — dismiss without changing grade (stays visible, dimmed)
3. **LLM review** — trigger external model review for deeper analysis

### Grade Scale

| Grade | Score | Meaning |
|-------|-------|---------|
| S | 1.00 | Production-grade, zero known gaps |
| A+ | 0.95 | Exceptional |
| A | 0.90 | Excellent |
| A- | 0.85 | Minor issues |
| B+ | 0.80 | Good, some gaps tracked |
| B | 0.75 | Adequate |
| B- | 0.70 | Functional, needs attention |
| C+ | 0.65 | Notable gaps |
| C | 0.60 | Significant gaps |
| D | 0.50 | Below expectations |
| F | 0.30 | Broken or missing |

### Ratchet Rules
Prevents silent score regression. Set a floor grade per dimension — if auto score drops below it, the system flags a warning. Ratchets are advisory by default; promote to hard-fail per-dimension.

### User Feedback
Rating widget (stars or slider) + free text. Text is optionally classified into dimensions via LLM. Aggregated into the sidecar's `user_feedback` field per dimension.

## Presets

| Preset | Dimensions | Best for |
|--------|-----------|----------|
| `python` | test coverage, type coverage, lint score, dep freshness, doc coverage, security, complexity, import hygiene | Python repos |
| `api` | endpoint health, p95 latency, error rate, auth coverage, schema validation, rate limiting, CORS, TLS expiry | REST APIs |
| `database` | schema completeness, index coverage, query perf, backup freshness, replication lag, pool utilization, migration currency | Databases |
| `infrastructure` | uptime, cert expiry, resource utilization, config drift, secret rotation, DNS propagation, CDN cache hit rate | DevOps/Infra |
| `ml_pipeline` | model freshness, data drift, inference latency, prediction accuracy, feature store currency, GPU utilization, experiment tracking | ML workflows |
| Custom | Your own | Anything |

## Integrations

| Integration | What it checks | Feeds dimension |
|-------------|---------------|-----------------|
| GitHub | CI status, open bugs, stale PRs | testing, code_quality, architecture |
| semgrep | SAST scanning (OWASP, SQL injection) | security |
| PyPI | Dependency version drift | reliability |
| Ollama | Model availability + freshness | performance |

Pluggable — implement the `Integration` protocol to add your own.

## Python API

```python
from two_brain_audit import AuditEngine, Dimension

engine = AuditEngine(db_path="audit.db", baseline_path="audit_baseline.json")

# Register dimensions with check functions
engine.register(Dimension(
    name="test_coverage",
    check=lambda: run_pytest_cov(),  # returns 0.0-1.0
    confidence=0.95,
    tier="light",
))

# Run a tier
results = engine.run_tier("daily")

# Get reconciliation status
divergences = engine.get_divergences()

# Record user feedback
engine.record_feedback(score=0.8, scope="overall", text="UI feels snappy")
```

## Dashboard

Optional Flask blueprint — drop into any existing Flask app or run standalone:

```python
from flask import Flask
from two_brain_audit.dashboard import create_blueprint

app = Flask(__name__)
app.register_blueprint(create_blueprint(engine), url_prefix="/audit")
```

## Self-Sustaining Maintenance

The audit system audits itself (6 layers):

| Layer | What it catches |
|-------|----------------|
| Functional test scoring | Grade inflation (scores from tests, not file existence) |
| Grade expiry | Stale optimism (manual grades expire after N days) |
| Cross-validation | Optimistic prose (divergence when manual >> auto) |
| Git diff detection | Silent drift (unreviewed changes since last grade) |
| External scanner | Blind spots (independent signal from semgrep, PyPI) |
| Ratchet rule | Backsliding (score can't drop below target without explicit edit) |

Additional self-checks:
- **Checker drift**: if checker configs haven't been updated in 6 months, flag for review
- **Self-pruning**: if a weekly check hasn't produced an actionable finding in 90 days, flag (either working perfectly or checking the wrong thing)

## Origin

Extracted from [BigEd CC](https://github.com/maxtheman/Education) after 30+ days of production use. Battle-tested on a 125-skill AI fleet with 12 audit dimensions.

## License

MIT
