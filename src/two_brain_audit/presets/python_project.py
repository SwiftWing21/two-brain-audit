"""Preset dimensions for generic Python projects.

Each dimension is a dict describing the check. The actual check functions
are created by the preset loader in the engine, which wires them to the
project's tools (pytest, ruff, mypy, etc.).

This file defines WHAT to check. The integration layer defines HOW.
"""

from __future__ import annotations

from two_brain_audit import Dimension, Tier

# ── Check function stubs ─────────────────────────────────────────────
# These are placeholder implementations. Real projects override them
# via engine.register() or by providing a project-specific checker module.


def _check_test_coverage() -> tuple[float, dict]:
    """Run pytest and return pass rate."""
    import subprocess
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=no", "-q"],  # noqa: S607
            capture_output=True, text=True, timeout=120,
        )
        import re
        passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", result.stdout)) else 0
        failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", result.stdout)) else 0
        total = passed + failed
        score = passed / total if total > 0 else 0.0
        return score, {"passed": passed, "failed": failed, "total": total}
    except Exception as e:
        return 0.0, {"error": str(e)}


def _check_lint_score() -> tuple[float, dict]:
    """Run ruff and score based on error count."""
    import subprocess
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--statistics", "-q"],  # noqa: S607
            capture_output=True, text=True, timeout=60,
        )
        errors = result.stdout.strip().count("\n") + (1 if result.stdout.strip() else 0)
        if result.returncode == 0:
            return 1.0, {"errors": 0}
        score = max(0.0, 1.0 - errors * 0.02)
        return score, {"errors": errors}
    except Exception as e:
        return 0.0, {"error": str(e)}


def _check_type_coverage() -> tuple[float, dict]:
    """Run mypy and score based on error count."""
    import subprocess
    try:
        result = subprocess.run(
            ["mypy", ".", "--no-error-summary"],  # noqa: S607
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return 1.0, {"errors": 0}
        errors = result.stdout.strip().count("\n")
        score = max(0.0, 1.0 - errors * 0.01)
        return score, {"errors": errors}
    except Exception as e:
        return 0.0, {"error": str(e)}


def _stub(name: str) -> tuple[float, dict]:
    """Placeholder — returns 0.5 with a note to implement."""
    return 0.5, {"note": f"{name} check not yet implemented"}


# ── Dimension Definitions ────────────────────────────────────────────

PYTHON_DIMENSIONS: list[Dimension] = [
    Dimension(
        name="test_coverage",
        check=_check_test_coverage,
        confidence=0.95,
        tier=Tier.LIGHT,
        description="Test pass rate from pytest",
    ),
    Dimension(
        name="lint_score",
        check=_check_lint_score,
        confidence=0.90,
        tier=Tier.LIGHT,
        description="Code lint quality via ruff",
    ),
    Dimension(
        name="type_coverage",
        check=_check_type_coverage,
        confidence=0.85,
        tier=Tier.MEDIUM,
        description="Type annotation coverage via mypy",
    ),
    Dimension(
        name="dep_freshness",
        check=lambda: _stub("dep_freshness"),
        confidence=0.85,
        tier=Tier.WEEKLY,
        description="Dependency version drift vs PyPI latest",
    ),
    Dimension(
        name="doc_coverage",
        check=lambda: _stub("doc_coverage"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="Documentation completeness (docstrings, README)",
    ),
    Dimension(
        name="security",
        check=lambda: _stub("security"),
        confidence=0.60,
        tier=Tier.WEEKLY,
        description="Security scanning via semgrep",
    ),
    Dimension(
        name="complexity",
        check=lambda: _stub("complexity"),
        confidence=0.80,
        tier=Tier.MEDIUM,
        description="Code complexity (radon or similar)",
    ),
    Dimension(
        name="import_hygiene",
        check=lambda: _stub("import_hygiene"),
        confidence=0.85,
        tier=Tier.LIGHT,
        description="Clean imports — no circular deps, no unused imports",
    ),
]
