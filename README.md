# Two-Brain Audit

A dual-layer audit system that combines automated quantitative scoring (**left brain**) with manual qualitative grading (**right brain**) and reconciles them automatically.

```
  LEFT BRAIN (Auto)              RIGHT BRAIN (Manual)
  ─────────────────              ────────────────────
  pytest pass rate    ──┐    ┌── Human grade (A)
  ruff lint score     ──┤    ├── LLM review findings
  semgrep scan        ──┤    ├── User feedback (4.2/5)
  endpoint health     ──┘    └── Team notes
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

## Why Two Brains?

| Scenario | Auto catches it | Manual catches it |
|----------|:-:|:-:|
| Test coverage drops silently | Yes | Maybe |
| "Feels slow" but metrics are fine | No | Yes |
| Stale manual grade after major refactor | Yes (divergence) | No |
| Security vuln in dependency | Yes (scanner) | No |
| UX regression that tests can't express | No | Yes |
| Reviewer optimism ("looks good to me") | Yes (cross-validation) | No |

## Quick Start

```bash
pip install two-brain-audit

two-brain-audit init                      # create DB + baseline sidecar
two-brain-audit register --preset python  # 8 dimensions for Python projects
two-brain-audit run light                 # first scan (~2s)
two-brain-audit status                    # view scores + divergences
```

```
Dimension                  Auto   Grade  Manual  Status
-----------------------------------------------------------------
  test_coverage            0.930      A      —   ok
  lint_score               1.000      S      —   ok
  type_coverage            0.720     B-      —   ok
  security                 0.500      D      —   ok

Overall: B+ (0.788)
```

### Web Dashboard

```bash
pip install two-brain-audit[dashboard]
two-brain-audit dashboard                 # http://localhost:8484/audit/
```

Dark-mode UI with grade ring, score bars, divergence alerts, tier triggers, and a feedback widget. Zero external dependencies.

**[Full walkthrough with examples &#8594; docs/QUICKSTART.md](docs/QUICKSTART.md)**

## Features

- **12-grade scale** (S through F) with automatic score-to-grade conversion
- **4 audit tiers** — light (CI), medium (on-demand), daily (scheduled), weekly (deep scan)
- **Divergence detection** — auto vs manual disagreement surfaces automatically
- **Ratchet rules** — prevent silent score regression per dimension
- **User feedback** — star rating + free text, optionally classified by LLM
- **5 presets** — Python, REST API, Database, Infrastructure, ML Pipeline
- **4 integrations** — GitHub, semgrep, PyPI, Ollama (pluggable)
- **3 exporters** — JSON, CSV, Markdown reports
- **Web dashboard** — self-contained Flask blueprint, embed anywhere
- **CLI** — `init`, `run`, `status`, `health`, `export`, `dashboard`
- **CI-friendly** — `two-brain-audit health` returns exit code 0/1 + JSON

## Python API

```python
from two_brain_audit import AuditEngine, Dimension, Tier

engine = AuditEngine(db_path="audit.db", baseline_path="audit_baseline.json")

engine.register(Dimension(
    name="test_coverage",
    check=lambda: (passed / total, {"passed": passed, "total": total}),
    confidence=0.95,
    tier=Tier.LIGHT,
))

results = engine.run_tier("daily")
health = engine.health_check()        # {"ok": True, "grade": "A", ...}
engine.record_feedback(score=0.8, text="Looking good")
```

## Flask Integration

```python
from two_brain_audit.dashboard import create_blueprint
app.register_blueprint(create_blueprint(engine), url_prefix="/audit")
```

## Presets

| Preset | Dimensions | Best for |
|--------|-----------|----------|
| `python` | test coverage, lint, types, deps, docs, security, complexity, imports | Python repos |
| `api` | endpoint health, latency, errors, auth, schema, rate limits, CORS, TLS | REST APIs |
| `database` | schema, indexes, queries, backups, replication, pool, migrations | Databases |
| `infrastructure` | uptime, certs, resources, config drift, secrets, DNS, CDN, containers | DevOps |
| `ml_pipeline` | model freshness, data drift, latency, accuracy, features, GPU, experiments | ML workflows |

## Docs

- **[Quickstart Guide](docs/QUICKSTART.md)** — step-by-step with examples
- **[Standards Reference](docs/STANDARDS.md)** — what we measure and why (OWASP, SRE, DORA, Clean Code, etc.)
- **[Architecture](docs/ARCHITECTURE.md)** — design decisions and data flow
- **[examples/biged/](examples/biged/)** — 12-dimension reference implementation

## Origin

Extracted from [BigEd CC](https://github.com/maxtheman/Education) after production use on a 125-skill AI fleet with 12 audit dimensions, 4 tiers, and automated daily/weekly scheduling.

## License

MIT
