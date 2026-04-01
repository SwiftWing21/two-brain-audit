"""BigEd CC's 12 audit dimensions — reference implementation.

These dimensions demonstrate the full range of check types:
- Deterministic counts (testing, module/plugin)
- Health probes (performance, reliability)
- Code analysis (architecture, code_quality)
- External scans (security via semgrep + manual)
- Hybrid auto+manual (usability_ux, dynamic_abilities)
- User feedback-weighted (data_hitl)

Auto-confidence per dimension:

    testing:           0.95  — pytest is highly reliable
    module_plugin:     0.90  — DB count is deterministic
    documentation:     0.85  — doc_freshness is mechanical
    performance:       0.85  — latency probes are objective
    reliability:       0.85  — health monitors are trustworthy
    observability:     0.80  — SSE/log checks are binary
    architecture:      0.75  — LOC scan is a proxy
    code_quality:      0.75  — ruff + grep are proxies
    security:          0.60  — auto catches surface, not depth
    dynamic_abilities: 0.60  — table existence != capability
    data_hitl:         0.55  — reachability != quality
    usability_ux:      0.30  — scales up with feedback volume
"""

from __future__ import annotations

from two_brain_audit import Dimension, Tier

# ── Confidence Map ───────────────────────────────────────────────────

AUTO_CONFIDENCE = {
    "testing": 0.95,
    "module_plugin": 0.90,
    "documentation": 0.85,
    "performance": 0.85,
    "reliability": 0.85,
    "observability": 0.80,
    "architecture": 0.75,
    "code_quality": 0.75,
    "security": 0.60,
    "dynamic_abilities": 0.60,
    "data_hitl": 0.55,
    "usability_ux": 0.30,
}


def _stub(name: str) -> tuple[float, dict]:
    """Placeholder — real checks live in fleet/audit_scorer.py."""
    return 0.5, {"note": f"Stub: wire to fleet/audit_scorer._check_{name}()"}


# ── Dimension Definitions ────────────────────────────────────────────

BIGED_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="testing",
        check=lambda: _stub("testing"),
        confidence=AUTO_CONFIDENCE["testing"],
        tier=Tier.LIGHT,
        description="pytest pass rate + smoke test results",
    ),
    Dimension(
        name="security",
        check=lambda: _stub("security"),
        confidence=AUTO_CONFIDENCE["security"],
        tier=Tier.DAILY,
        description="Ruff security rules + path traversal smoke + RBAC + semgrep (weekly)",
    ),
    Dimension(
        name="performance",
        check=lambda: _stub("performance"),
        confidence=AUTO_CONFIDENCE["performance"],
        tier=Tier.MEDIUM,
        description="Endpoint response times under threshold",
    ),
    Dimension(
        name="reliability",
        check=lambda: _stub("reliability"),
        confidence=AUTO_CONFIDENCE["reliability"],
        tier=Tier.MEDIUM,
        description="Agent health + circuit breaker status",
    ),
    Dimension(
        name="observability",
        check=lambda: _stub("observability"),
        confidence=AUTO_CONFIDENCE["observability"],
        tier=Tier.MEDIUM,
        description="SSE broadcaster + audit log + /api/health",
    ),
    Dimension(
        name="architecture",
        check=lambda: _stub("architecture"),
        confidence=AUTO_CONFIDENCE["architecture"],
        tier=Tier.MEDIUM,
        description="Key files under LOC threshold",
    ),
    Dimension(
        name="code_quality",
        check=lambda: _stub("code_quality"),
        confidence=AUTO_CONFIDENCE["code_quality"],
        tier=Tier.MEDIUM,
        description="Ruff clean + no raw sqlite3 + no bare excepts",
    ),
    Dimension(
        name="module_plugin",
        check=lambda: _stub("module_plugin"),
        confidence=AUTO_CONFIDENCE["module_plugin"],
        tier=Tier.LIGHT,
        description="ModuleHub registered module count",
    ),
    Dimension(
        name="documentation",
        check=lambda: _stub("documentation"),
        confidence=AUTO_CONFIDENCE["documentation"],
        tier=Tier.MEDIUM,
        description="Doc freshness — stale reference detection",
    ),
    Dimension(
        name="usability_ux",
        check=lambda: _stub("usability_ux"),
        confidence=AUTO_CONFIDENCE["usability_ux"],
        tier=Tier.DAILY,
        description="Pages load without error + user feedback aggregate",
    ),
    Dimension(
        name="dynamic_abilities",
        check=lambda: _stub("dynamic_abilities"),
        confidence=AUTO_CONFIDENCE["dynamic_abilities"],
        tier=Tier.DAILY,
        description="ML router + experiment framework + billing tables with recent rows",
    ),
    Dimension(
        name="data_hitl",
        check=lambda: _stub("data_hitl"),
        confidence=AUTO_CONFIDENCE["data_hitl"],
        tier=Tier.DAILY,
        description="HF ingest sources reachable + HITL table has recent entries",
    ),
]
