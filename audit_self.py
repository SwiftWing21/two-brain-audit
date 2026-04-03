"""Self-audit — scorerift auditing itself."""
import subprocess
import sys
import re
from pathlib import Path

sys.path.insert(0, "src")

from scorerift import AuditEngine, Dimension, Tier

ROOT = Path(__file__).parent
engine = AuditEngine(db_path="self_audit.db", baseline_path="self_baseline.json", target_path=str(ROOT))


def check_tests() -> tuple[float, dict]:
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--tb=no", "-q"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = result.stdout + result.stderr
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", output)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", output)) else 0
    total = passed + failed
    return (passed / total if total else 0.0), {"passed": passed, "failed": failed, "total": total}


def check_lint() -> tuple[float, dict]:
    result = subprocess.run(
        ["ruff", "check", "src/", "tests/", "--statistics", "-q"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )
    if result.returncode == 0:
        return 1.0, {"errors": 0}
    errors = len([line for line in result.stdout.strip().splitlines() if line.strip()])
    return max(0.0, 1.0 - errors * 0.03), {"errors": errors}


def check_type_coverage() -> tuple[float, dict]:
    py_typed = (ROOT / "src" / "scorerift" / "py.typed").exists()
    py_files = list((ROOT / "src").rglob("*.py"))
    annotated = total_funcs = 0
    for f in py_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        total_funcs += len(re.findall(r"def \w+\(", content))
        annotated += len(re.findall(r"def \w+\([^)]*:.*\)", content))
    ratio = annotated / total_funcs if total_funcs else 0.0
    return 0.5 * (1.0 if py_typed else 0.0) + 0.5 * ratio, {"py_typed": py_typed, "annotated": annotated, "total_funcs": total_funcs, "ratio": round(ratio, 2)}


def check_docs() -> tuple[float, dict]:
    expected = ["README.md", "docs/QUICKSTART.md", "docs/ARCHITECTURE.md", "LICENSE"]
    found = [f for f in expected if (ROOT / f).exists()]
    missing = [f for f in expected if f not in found]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sections = ["Quick Start", "Features", "Python API", "Presets", "License"]
    found_sections = [s for s in sections if s in readme]
    return 0.6 * len(found) / len(expected) + 0.4 * len(found_sections) / len(sections), {
        "files_found": found, "files_missing": missing,
        "sections_found": found_sections,
    }


def check_security() -> tuple[float, dict]:
    issues = []
    py_files = list((ROOT / "src").rglob("*.py"))
    for f in py_files:
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if re.search(r'(password|secret|token)\s*=\s*["\'][^"\']{8,}', line, re.I):
                issues.append(f"{f.name}:{i}: possible hardcoded secret")
    return max(0.0, 1.0 - len(issues) * 0.2), {"issues": issues, "files_scanned": len(py_files)}


def check_packaging() -> tuple[float, dict]:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    checks = {k: (v in content) for k, v in {
        "name": "name =", "version": "version =", "description": "description =",
        "license": "license =", "python_requires": "requires-python",
        "readme": "readme =", "scripts": "[project.scripts]",
        "classifiers": "classifiers", "urls": "[project.urls]",
        "optional_deps": "[project.optional-dependencies]",
    }.items()}
    n = sum(checks.values())
    return n / len(checks), {"checks": checks, "missing": [k for k, v in checks.items() if not v]}


def check_test_depth() -> tuple[float, dict]:
    modules = ["engine", "db", "sidecar", "grades", "reconciler", "tiers", "feedback", "cli"]
    test_files = {f.stem.replace("test_", "") for f in (ROOT / "tests").glob("test_*.py")}
    covered = [m for m in modules if m in test_files]
    uncovered = [m for m in modules if m not in test_files]
    return len(covered) / len(modules), {"covered": covered, "uncovered": uncovered}


def check_ci() -> tuple[float, dict]:
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    publish = ROOT / ".github" / "workflows" / "publish.yml"
    checks = {"ci_exists": ci.exists(), "publish_exists": publish.exists()}
    if ci.exists():
        content = ci.read_text(encoding="utf-8")
        checks["multi_os"] = "matrix" in content and "windows" in content
        checks["multi_python"] = "python-version" in content
        checks["lint_step"] = "ruff" in content
        checks["test_step"] = "pytest" in content
    return sum(checks.values()) / len(checks), {"checks": checks}


# ── Register ─────────────────────────────────────────────────────────

engine.register(Dimension(name="testing", check=check_tests, confidence=0.95, tier=Tier.LIGHT))
engine.register(Dimension(name="lint", check=check_lint, confidence=0.90, tier=Tier.LIGHT))
engine.register(Dimension(name="type_coverage", check=check_type_coverage, confidence=0.75, tier=Tier.MEDIUM))
engine.register(Dimension(name="documentation", check=check_docs, confidence=0.85, tier=Tier.MEDIUM))
engine.register(Dimension(name="security", check=check_security, confidence=0.60, tier=Tier.DAILY))
engine.register(Dimension(name="packaging", check=check_packaging, confidence=0.90, tier=Tier.LIGHT))
engine.register(Dimension(name="test_depth", check=check_test_depth, confidence=0.85, tier=Tier.MEDIUM))
engine.register(Dimension(name="ci", check=check_ci, confidence=0.90, tier=Tier.MEDIUM))


if __name__ == "__main__":
    print("Running self-audit (medium tier)...\n")
    results = engine.run_tier("medium")

    from scorerift.grades import score_to_grade

    print(f"{'Dimension':20s}  {'Score':>6s}  {'Grade':>5s}  Detail")
    print("-" * 75)
    for r in results:
        grade = score_to_grade(r.auto_score)
        d = r.auto_detail
        detail = ""
        if "passed" in d:
            detail = f"{d['passed']}/{d['total']} tests"
        elif "errors" in d:
            detail = f"{d['errors']} errors"
        elif "missing" in d:
            detail = f"missing: {', '.join(d['missing']) or 'none'}"
        elif "uncovered" in d:
            detail = f"uncovered: {', '.join(d['uncovered']) or 'none'}"
        elif "checks" in d:
            detail = f"{sum(v for v in d['checks'].values() if isinstance(v, bool))}/{len(d['checks'])}"
        print(f"  {r.name:20s}  {r.auto_score:6.3f}  {grade:>5s}  {detail}")

    overall = engine.overall_score()
    print(f"\nOverall: {score_to_grade(overall)} ({overall:.3f})")

    print("\nLaunching dashboard...")
    from scorerift.app import launch
    launch(engine, title="ScoreRift - Self-Audit")
