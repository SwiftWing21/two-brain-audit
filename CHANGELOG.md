# Changelog

## v1.0.0 (2026-04-02)

**Production release.** Framework is complete, self-tested, and field-validated.

- **API key safety**: `__repr__` masks keys, format validation on init, `raw_response` disabled by default
- **BudgetGuard**: per-session cost cap ($1 default) prevents runaway API spend
- **CLI persistence**: `register` writes `.scorerift.json`, `run` auto-loads it
- **Integration exports**: `from scorerift.integrations import GitHubIntegration`
- **156 tests** across 14 test modules (was 117 in v0.4.0)
- **CHANGELOG.md** added
- **Classifier**: `Development Status :: 5 - Production/Stable`

## v0.4.0 (2026-04-02)

10 fixes from dogfooding (TBR auditing itself — 4 divergences found):

- **Thread safety**: `_chdir_lock` prevents concurrent `run_tier()` CWD races
- **Atomic sidecar writes**: temp file + `os.replace()` prevents corruption on kill
- **Broken-check fallback**: 0.0 changed to 0.5 (unknown, not failing) for transient errors
- **CLI auto-load**: reads preset from `.scorerift.json` before running
- **classify_status()** wired into engine (was orphaned in reconciler)
- **review_dimension()** return types unified (always dict)
- **AuditDB.close()** method (engine.close no longer breaks abstraction)
- **Dimension name validation**: `[a-z0-9_-]{1,64}` on acknowledge endpoint
- **ARCHITECTURE.md**: file layout corrected for moved presets/integrations/reviewers
- 99 to 117 tests: DB roundtrip, CLI run/register, reviewer cache/parse

## v0.3.1 (2026-04-02)

- **`--target` flag**: `scorerift run light --target /path/to/project`
- `AuditEngine(target_path="...")` for Python API
- `os.chdir` to target before running dimension checks, restore after
- Found via Gemini Code Assist field test (couldn't point audit at a different directory)

## v0.3.0 (2026-04-02)

LLM reviewer system — the "right brain on demand":

- **3 provider clients**: Claude, Gemini, OpenAI with per-call cost tracking
- **OSS swarm review**: 4 specialized lenses (security auditor, performance engineer, architect, compliance auditor) with cross-validated findings
- **Multi-provider consensus**: parallel execution, agreement scoring, merged findings
- **Local review cache**: SQLite-backed, 7-day TTL, prevents redundant API calls
- **`engine.review_dimension()`**: single/swarm/consensus modes, auto-writes to sidecar
- **Three layers of gap detection**: auto vs manual, LLM vs auto, LLM vs LLM

## v0.2.2 (2026-04-01)

- **"Wrap Your Existing Tools"** README section: SonarQube, Datadog, pylint examples
- Reframes project as "the layer that sits on top of your existing tools"

## v0.2.1 (2026-04-01)

- **README rewrite**: "The product isn't the scoring. It's watching the gap."
- Divergence-as-product framing, real-world scenario table

## v0.2.0 (2026-04-01)

Major production hardening (7-phase plan):

- **Package fix**: presets/ and integrations/ moved into `src/scorerift/` (was broken for pip users)
- **All 8 Python preset checks implemented**: dep_freshness, doc_coverage, security, complexity, import_hygiene (was 5/8 stubs)
- **Security hardening**: input validation on dashboard API, path traversal protection on sidecar, thread-safe DB schema init
- **Ratchet enforcement**: wired into `run_tier()` via `check_ratchet()` from reconciler
- **`close()` method** on AuditEngine for clean DB disconnect
- **`run_scheduled()`** for cron/scheduler integration
- **99 tests** (was 69): dashboard, exporters, presets coverage added
- **CLI `--verbose`** flag for debug logging
- **NullHandler** on package logger (library best practice)

## v0.1.2 (2026-04-01)

- **STANDARDS.md**: maps dimensions to OWASP, SRE, DORA, Clean Code
- **DB path display** in dashboard header
- Lint fixes for CI green

## v0.1.1 (2026-04-01)

- Self-audit dogfood: scored S-tier (0.969)
- 48 to 69 tests: added test_tiers.py, test_feedback.py, test_cli.py

## v0.1.0 (2026-04-01)

Initial release:

- Core engine: AuditEngine, Dimension, DimensionResult
- 12-grade scale (S through F), divergence detection, reconciliation
- 4 audit tiers: light, medium, daily, weekly
- SQLite storage (audit_scores, user_feedback)
- JSON sidecar for manual grades + ratchet targets
- CLI: init, register, run, status, health, export, dashboard
- Flask dashboard blueprint (self-contained HTML, zero CDN deps)
- 5 presets: Python, API, Database, Infrastructure, ML Pipeline
- 4 integrations: GitHub, semgrep, PyPI, Ollama
- 3 exporters: JSON, CSV, Markdown
- 48 tests
