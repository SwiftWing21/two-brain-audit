"""
Default dimension interaction graphs for ScoreRift presets.

IMPORTANT: These weights are INITIAL PRIORS based on domain intuition about
how project health dimensions typically correlate. They are NOT empirically
calibrated. Before claiming statistical validity, calibrate against historical
audit outcomes. Each edge carries a provenance="prior" marker.
"""

from scorerift.ray_trace import Interaction, build_graph

# ── Python Project (8 dimensions) ────────────────────────────────────────

PYTHON_PROJECT_EDGES = [
    Interaction("security", "test_coverage", 0.3, -1.0,
                "security gaps suggest testing gaps", "prior"),
    Interaction("test_coverage", "complexity", 0.4, 1.0,
                "good tests enable managing complexity", "prior"),
    Interaction("lint_score", "import_hygiene", 0.5, 1.0,
                "clean lint correlates with clean imports", "prior"),
    Interaction("complexity", "security", 0.3, -1.0,
                "high complexity hides security issues", "prior"),
    Interaction("type_coverage", "security", 0.3, 1.0,
                "types catch certain vuln classes", "prior"),
    Interaction("doc_coverage", "complexity", 0.2, 1.0,
                "documented code is easier to understand", "prior"),
    Interaction("dep_freshness", "security", 0.5, 1.0,
                "fresh deps have security patches", "prior"),
    Interaction("test_coverage", "dep_freshness", 0.2, 1.0,
                "tests catch dep upgrade regressions", "prior"),
]

PYTHON_PROJECT_GRAPH = build_graph(PYTHON_PROJECT_EDGES)

# ── API Service (6 dimensions from api_service.py preset) ────────────────

API_SERVICE_EDGES = [
    Interaction("uptime", "latency", 0.4, 1.0,
                "reliable services maintain consistent latency", "prior"),
    Interaction("error_rate", "uptime", 0.5, -1.0,
                "high error rates degrade uptime", "prior"),
    Interaction("auth_coverage", "error_rate", 0.3, -1.0,
                "auth gaps increase error surface", "prior"),
    Interaction("rate_limiting", "latency", 0.3, 1.0,
                "rate limiting protects latency under load", "prior"),
    Interaction("docs_coverage", "auth_coverage", 0.2, 1.0,
                "documented APIs have better auth patterns", "prior"),
]

API_SERVICE_GRAPH = build_graph(API_SERVICE_EDGES)
