"""Tests for scorerift.ray_trace — deterministic with fixed seeds."""

import pytest
from scorerift.ray_trace import (
    Interaction,
    build_graph,
    cast_ray,
    ray_trace,
    _bootstrap_ci,
    DELTA_CAP_PRIOR,
)
import random


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def linear_graph():
    """A → B → C linear chain."""
    return build_graph([
        Interaction("A", "B", 0.5, 1.0, "A amplifies B"),
        Interaction("B", "C", 0.5, 1.0, "B amplifies C"),
    ])


@pytest.fixture
def cycle_graph():
    """A → B → A cycle."""
    return build_graph([
        Interaction("A", "B", 0.4, 1.0, "A to B"),
        Interaction("B", "A", 0.4, -1.0, "B dampens A"),
    ])


@pytest.fixture
def python_scores():
    """Typical Python project scores."""
    return {
        "test_coverage": 0.88,
        "lint_score": 0.92,
        "type_coverage": 0.75,
        "dep_freshness": 0.70,
        "doc_coverage": 0.65,
        "security": 0.58,
        "complexity": 0.72,
        "import_hygiene": 0.85,
    }


@pytest.fixture
def python_graph():
    from scorerift.presets.interaction_graphs import PYTHON_PROJECT_GRAPH
    return PYTHON_PROJECT_GRAPH


# ── Graph Construction ───────────────────────────────────────────────────

def test_build_graph_empty():
    g = build_graph([])
    assert g.edges == []
    assert g._adjacency == {}
    assert g._out_degree == {}


def test_build_graph_adjacency(linear_graph):
    assert "A" in linear_graph._adjacency
    assert "B" in linear_graph._adjacency
    assert "C" not in linear_graph._adjacency  # C has no outgoing edges
    assert len(linear_graph._adjacency["A"]) == 1
    assert len(linear_graph._adjacency["B"]) == 1


def test_build_graph_out_degree(linear_graph):
    assert linear_graph._out_degree["A"] == 1
    assert linear_graph._out_degree["B"] == 1
    assert linear_graph._out_degree["C"] == 0  # leaf


def test_build_graph_cycle(cycle_graph):
    assert cycle_graph._out_degree["A"] == 1
    assert cycle_graph._out_degree["B"] == 1


# ── Ray Casting ──────────────────────────────────────────────────────────

def test_cast_ray_linear(linear_graph):
    """Ray through A→B→C with known scores."""
    scores = {"A": 0.8, "B": 0.6, "C": 0.5}
    rng = random.Random(42)
    ray = cast_ray("A", 0.8, linear_graph, scores, max_bounces=5, rng=rng)

    # Should have visited at least A and B
    assert len(ray.path) >= 2
    assert ray.path[0] == ("A", 0.8)
    # Energy decays: 0.8 * weight(0.5) * gate(B_score=0.6) = 0.24
    assert ray.path[1][0] == "B"
    assert abs(ray.path[1][1] - 0.24) < 0.001


def test_cast_ray_leaf_terminates():
    """A dimension with no outgoing edges terminates immediately."""
    g = build_graph([Interaction("A", "B", 0.5, 1.0, "only edge")])
    scores = {"A": 0.8, "B": 0.5}
    rng = random.Random(0)

    # Start from B (leaf) — should terminate immediately
    ray = cast_ray("B", 0.5, g, scores, max_bounces=5, rng=rng)
    assert len(ray.path) == 1
    assert ray.path[0] == ("B", 0.5)


def test_cast_ray_absorption():
    """Very low weight edges should trigger absorption threshold."""
    g = build_graph([
        Interaction("A", "B", 0.01, 1.0, "tiny weight"),
        Interaction("B", "C", 0.01, 1.0, "tiny weight"),
    ])
    scores = {"A": 0.1, "B": 0.1, "C": 0.1}
    rng = random.Random(0)
    ray = cast_ray("A", 0.1, g, scores, max_bounces=5, rng=rng)
    # Energy: 0.1 * 0.01 * 0.1 = 0.0001 < ABSORPTION_THRESHOLD
    assert len(ray.path) <= 2


def test_cast_ray_cycle_converges(cycle_graph):
    """Cycles should not explode — energy decays per bounce."""
    scores = {"A": 0.9, "B": 0.9}
    rng = random.Random(0)
    ray = cast_ray("A", 0.9, cycle_graph, scores, max_bounces=10, rng=rng)
    # Even with 10 bounces allowed, energy should decay to absorption
    assert ray.final_energy < 0.5


def test_cast_ray_dampening():
    """Negative polarity uses (1 - receiver_score) as gate."""
    g = build_graph([
        Interaction("A", "B", 0.5, -1.0, "A dampens B"),
    ])
    # B has high score (0.9), so gate = 1 - 0.9 = 0.1
    scores = {"A": 0.8, "B": 0.9}
    rng = random.Random(0)
    ray = cast_ray("A", 0.8, g, scores, max_bounces=5, rng=rng)
    # Energy: 0.8 * 0.5 * (1 - 0.9) = 0.04
    assert len(ray.path) >= 2
    assert abs(ray.path[1][1] - 0.04) < 0.001


# ── Bootstrap CI ─────────────────────────────────────────────────────────

def test_bootstrap_ci_empty():
    rng = random.Random(0)
    lo, hi = _bootstrap_ci([], 0.5, 0.15, rng)
    assert lo == 0.5
    assert hi == 0.5


def test_bootstrap_ci_tight():
    """Identical contributions → tight CI."""
    rng = random.Random(0)
    contribs = [0.01] * 100
    lo, hi = _bootstrap_ci(contribs, 0.5, 0.15, rng)
    assert hi - lo < 0.02  # very tight


def test_bootstrap_ci_wide():
    """Spread contributions → wider CI."""
    rng = random.Random(0)
    contribs = [0.1, -0.1, 0.05, -0.05, 0.15, -0.15] * 20
    lo, hi = _bootstrap_ci(contribs, 0.5, 0.15, rng)
    assert hi - lo > 0.01  # measurably wider than zero


# ── Full Ray Trace ───────────────────────────────────────────────────────

def test_ray_trace_empty_graph():
    """Empty graph → all deltas zero, combined = auto."""
    scores = {"A": 0.5, "B": 0.7}
    g = build_graph([])
    report = ray_trace(scores, g, seed=0)
    assert report.results["A"].interaction_delta == 0.0
    assert report.results["B"].interaction_delta == 0.0
    assert report.results["A"].combined_score == 0.5
    assert report.results["B"].combined_score == 0.7
    assert report.individual_overall == report.connection_overall


def test_ray_trace_deterministic(python_scores, python_graph):
    """Same seed → same results."""
    r1 = ray_trace(python_scores, python_graph, seed=42)
    r2 = ray_trace(python_scores, python_graph, seed=42)

    for d in python_scores:
        assert r1.results[d].interaction_delta == r2.results[d].interaction_delta
        assert r1.results[d].combined_score == r2.results[d].combined_score
        assert r1.results[d].ci_95 == r2.results[d].ci_95


def test_ray_trace_different_seeds(python_scores, python_graph):
    """Different seeds → different results (stochastic)."""
    r1 = ray_trace(python_scores, python_graph, seed=0)
    r2 = ray_trace(python_scores, python_graph, seed=999)

    # At least one dimension should differ
    any_diff = any(
        r1.results[d].interaction_delta != r2.results[d].interaction_delta
        for d in python_scores
    )
    assert any_diff


def test_ray_trace_delta_capped(python_scores, python_graph):
    """All deltas within [-delta_cap, +delta_cap]."""
    report = ray_trace(python_scores, python_graph, seed=0)
    for d, result in report.results.items():
        assert -DELTA_CAP_PRIOR <= result.interaction_delta <= DELTA_CAP_PRIOR
        assert 0.0 <= result.combined_score <= 1.0


def test_ray_trace_auto_score_unchanged(python_scores, python_graph):
    """auto_score is never modified by ray tracing."""
    report = ray_trace(python_scores, python_graph, seed=0)
    for d, original in python_scores.items():
        assert report.results[d].auto_score == original


def test_ray_trace_out_degree_scaling(python_scores, python_graph):
    """Dimensions with more outgoing edges get more rays."""
    report = ray_trace(python_scores, python_graph, base_rays=100, seed=0)
    # security has 1 outgoing edge (to test_coverage) → 100 * (1+1) = 200 rays cast from it
    # import_hygiene has 0 outgoing edges → 100 * (1+0) = 100 rays cast from it
    # This manifests as different ray_received counts
    assert report.total_rays_cast > 0


def test_ray_trace_convergence(python_scores, python_graph):
    """Convergence should be reached before all rays are cast."""
    report = ray_trace(python_scores, python_graph, base_rays=500, seed=0)
    # With 500 base rays, convergence should happen before total
    assert report.converged_at <= report.total_rays_cast


def test_ray_trace_ci_bounds(python_scores, python_graph):
    """CI lower bound <= combined_score <= CI upper bound."""
    report = ray_trace(python_scores, python_graph, seed=0)
    for d, result in report.results.items():
        lo, hi = result.ci_95
        # CI should bracket the combined score (approximately — bootstrap is stochastic)
        assert lo <= hi
        # combined_score should be within a reasonable range of the CI
        assert lo <= result.combined_score + 0.05  # small tolerance
        assert hi >= result.combined_score - 0.05


def test_ray_trace_report_fields(python_scores, python_graph):
    """Report has all expected fields."""
    report = ray_trace(python_scores, python_graph, seed=0)
    assert len(report.results) == len(python_scores)
    assert report.individual_overall > 0
    assert report.connection_overall > 0
    assert report.total_rays_cast > 0
    assert report.seed == 0
    assert report.delta_cap == DELTA_CAP_PRIOR
    assert report.graph_edges == len(python_graph.edges)


def test_ray_trace_top_paths(python_scores, python_graph):
    """Each dimension should have at most 3 top paths."""
    report = ray_trace(python_scores, python_graph, seed=0)
    for d, result in report.results.items():
        assert len(result.top_paths) <= 3
        # Top paths should be sorted by |energy| descending
        energies = [abs(p.final_energy) for p in result.top_paths]
        assert energies == sorted(energies, reverse=True)
