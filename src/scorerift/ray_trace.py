"""
Evidence Ray Tracing — Monte Carlo scoring through dimension interaction graphs.

Casts "evidence rays" from each dimension through a configured interaction graph.
Each ray carries energy that decays at each bounce based on edge weight and the
receiving dimension's score. Produces per-dimension interaction deltas that
enhance (not replace) existing auto_scores.

Design decisions (council-reviewed 2026-04-05):
  D1: Fixed max_bounces=5 for cross-dimension comparability
  D2: Ray allocation scales by out-degree (not bounce count)
  D3: Two views only — individual (auto) + connection (combined)
  D4: Bootstrap 95% CIs implemented (not TODO)
  D5: Convergence check every 50 rays
  D6: delta_cap=0.15 labeled as PRIOR (sensitivity-test before production)
  D7: Edge weights labeled as priors with provenance field
  D8: Single source of truth (ScoreRift owns, BigEd imports)
  D9: Default seed=0 for compliance reproducibility
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

__all__ = [
    "Interaction",
    "InteractionGraph",
    "EvidenceRay",
    "RayTraceResult",
    "RayTraceReport",
    "build_graph",
    "cast_ray",
    "ray_trace",
]

# ── Constants (D6: labeled as priors) ─────────────────────────────────────

DELTA_CAP_PRIOR = 0.15
CONVERGENCE_EPSILON = 0.005
ABSORPTION_THRESHOLD = 0.01
DEFAULT_BASE_RAYS = 200
DEFAULT_MAX_BOUNCES = 5
BOOTSTRAP_SAMPLES = 500
CONVERGENCE_CHECK_INTERVAL = 50


# ── Data Structures ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Interaction:
    """A directed edge in the dimension interaction graph."""
    source: str
    target: str
    weight: float            # 0.0-1.0, strength of coupling
    polarity: float          # +1.0 = amplifying, -1.0 = dampening
    label: str = ""          # human-readable reason
    provenance: str = "prior"  # "prior" | "calibrated" | "empirical"


@dataclass
class InteractionGraph:
    """Weighted directed graph of dimension interactions."""
    edges: list[Interaction]
    _adjacency: dict[str, list[Interaction]] = field(default_factory=dict, repr=False)
    _out_degree: dict[str, int] = field(default_factory=dict, repr=False)


@dataclass
class EvidenceRay:
    """A single ray's traversal path through the interaction graph."""
    path: list[tuple[str, float]]  # [(dimension, energy_at_step), ...]
    final_energy: float
    polarity: float


@dataclass
class RayTraceResult:
    """Per-dimension result from ray tracing."""
    dimension: str
    auto_score: float                    # individual scope (unchanged)
    interaction_delta: float             # connection scope modifier
    combined_score: float                # connection scope (clamped to [0, 1])
    rays_received: int
    top_paths: list[EvidenceRay]         # top 3 by |energy|
    ci_95: tuple[float, float]           # bootstrap 95% CI for combined_score


@dataclass
class RayTraceReport:
    """Complete ray tracing output for all dimensions."""
    results: dict[str, RayTraceResult]
    individual_overall: float            # mean of auto_scores
    connection_overall: float            # mean of combined_scores
    total_rays_cast: int
    converged_at: int
    seed: int | None
    delta_cap: float
    epsilon: float
    graph_edges: int


# ── Graph Construction ───────────────────────────────────────────────────

def build_graph(edges: list[Interaction]) -> InteractionGraph:
    """Build an InteractionGraph from a list of edges."""
    adjacency: dict[str, list[Interaction]] = {}
    out_degree: dict[str, int] = {}

    for edge in edges:
        adjacency.setdefault(edge.source, []).append(edge)
        out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
        # Ensure target appears in out_degree (may be 0)
        out_degree.setdefault(edge.target, 0)

    return InteractionGraph(
        edges=edges,
        _adjacency=adjacency,
        _out_degree=out_degree,
    )


# ── Ray Casting ──────────────────────────────────────────────────────────

def cast_ray(
    start: str,
    energy: float,
    graph: InteractionGraph,
    scores: dict[str, float],
    max_bounces: int,
    rng: random.Random,
) -> EvidenceRay:
    """Cast a single evidence ray from a starting dimension.

    The ray traverses the interaction graph, losing energy at each bounce
    based on the edge weight and the receiving dimension's score.
    """
    current = start
    path = [(current, energy)]
    last_polarity = 1.0

    for _ in range(max_bounces):
        neighbors = graph._adjacency.get(current, [])
        if not neighbors:
            break

        # Weighted random neighbor selection
        total_w = sum(e.weight for e in neighbors)
        r = rng.random() * total_w
        chosen = neighbors[0]
        for e in neighbors:
            r -= e.weight
            if r <= 0:
                chosen = e
                break

        receiver_score = scores.get(chosen.target, 0.5)
        gate_factor = receiver_score if chosen.polarity > 0 else (1.0 - receiver_score)
        energy = energy * chosen.weight * gate_factor
        last_polarity = chosen.polarity

        if energy < ABSORPTION_THRESHOLD:
            break

        current = chosen.target
        path.append((current, energy))

    return EvidenceRay(path=path, final_energy=energy, polarity=last_polarity)


# ── Bootstrap CI ─────────────────────────────────────────────────────────

def _bootstrap_ci(
    contributions: list[float],
    auto: float,
    delta_cap: float,
    rng: random.Random,
    samples: int = BOOTSTRAP_SAMPLES,
) -> tuple[float, float]:
    """Bootstrap 95% CI for combined_score by resampling ray contributions."""
    if not contributions:
        return (auto, auto)
    n = len(contributions)
    combined_samples = []
    for _ in range(samples):
        resample = [contributions[rng.randrange(n)] for _ in range(n)]
        delta = max(-delta_cap, min(delta_cap, sum(resample) / n))
        combined_samples.append(max(0.0, min(1.0, auto + delta)))
    combined_samples.sort()
    lo = combined_samples[int(0.025 * samples)]
    hi = combined_samples[int(0.975 * samples)]
    return (lo, hi)


# ── Main Entry Point ────────────────────────────────────────────────────

def ray_trace(
    scores: dict[str, float],
    graph: InteractionGraph,
    base_rays: int = DEFAULT_BASE_RAYS,
    max_bounces: int = DEFAULT_MAX_BOUNCES,
    delta_cap: float = DELTA_CAP_PRIOR,
    epsilon: float = CONVERGENCE_EPSILON,
    seed: int | None = 0,
) -> RayTraceReport:
    """Cast evidence rays through a dimension interaction graph.

    Args:
        scores: dimension name -> auto_score (0.0-1.0)
        graph: InteractionGraph built via build_graph()
        base_rays: base number of rays per dimension (scaled by out-degree)
        max_bounces: fixed bounce cap per ray (D1)
        delta_cap: maximum |interaction_delta| (D6 prior)
        epsilon: convergence threshold (D5)
        seed: fixed seed for reproducibility (D9). None for stochastic.

    Returns:
        RayTraceReport with per-dimension results + overall scores.
    """
    rng = random.Random(seed)

    # Ray allocation scaled by out-degree (D2)
    rays_per_dim = {
        d: base_rays * (1 + graph._out_degree.get(d, 0))
        for d in scores
    }

    contributions: dict[str, list[float]] = {d: [] for d in scores}
    ray_counts: dict[str, int] = {d: 0 for d in scores}
    top_paths: dict[str, list[EvidenceRay]] = {d: [] for d in scores}
    total_rays = 0

    # Convergence tracking (D5)
    prev_deltas: dict[str, float] = {d: 0.0 for d in scores}
    converged_at: int | None = None

    for start_dim in scores:
        for _ray_idx in range(rays_per_dim[start_dim]):
            ray = cast_ray(
                start_dim, scores[start_dim], graph, scores,
                max_bounces=max_bounces, rng=rng,
            )
            total_rays += 1

            if len(ray.path) < 2:
                continue  # leaf, no contribution

            terminal_dim = ray.path[-1][0]
            contribution = ray.final_energy * ray.polarity
            contributions[terminal_dim].append(contribution)
            ray_counts[terminal_dim] += 1

            # Keep top 3 paths by |energy| per terminal dimension
            top_paths[terminal_dim].append(ray)
            top_paths[terminal_dim].sort(
                key=lambda r: abs(r.final_energy), reverse=True,
            )
            top_paths[terminal_dim] = top_paths[terminal_dim][:3]

            # Convergence check every N rays (D5)
            if (
                converged_at is None
                and total_rays % CONVERGENCE_CHECK_INTERVAL == 0
                and total_rays > base_rays
            ):
                current_deltas = {
                    d: (sum(contributions[d]) / len(contributions[d])
                        if contributions[d] else 0.0)
                    for d in scores
                }
                max_change = max(
                    abs(current_deltas[d] - prev_deltas[d]) for d in scores
                )
                if max_change < epsilon:
                    converged_at = total_rays
                prev_deltas = current_deltas

    if converged_at is None:
        converged_at = total_rays

    # Compute deltas, clamp, build results (D3: two views only)
    results: dict[str, RayTraceResult] = {}
    for d, auto in scores.items():
        contribs = contributions[d]
        raw_delta = sum(contribs) / len(contribs) if contribs else 0.0
        delta = max(-delta_cap, min(delta_cap, raw_delta))
        combined = max(0.0, min(1.0, auto + delta))
        ci = _bootstrap_ci(contribs, auto, delta_cap, rng)

        results[d] = RayTraceResult(
            dimension=d,
            auto_score=auto,
            interaction_delta=delta,
            combined_score=combined,
            rays_received=ray_counts[d],
            top_paths=top_paths[d],
            ci_95=ci,
        )

    individual_overall = sum(r.auto_score for r in results.values()) / len(results)
    connection_overall = sum(r.combined_score for r in results.values()) / len(results)

    return RayTraceReport(
        results=results,
        individual_overall=individual_overall,
        connection_overall=connection_overall,
        total_rays_cast=total_rays,
        converged_at=converged_at,
        seed=seed,
        delta_cap=delta_cap,
        epsilon=epsilon,
        graph_edges=len(graph.edges),
    )
