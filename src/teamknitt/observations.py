"""Optional descriptive observation through the dynamical-systems lens.

Complexity science and complex adaptive systems inform the observation lens;
Gorman et al. is one team-focused reference, not a psychometric checklist or score. Oscillatory/fractal/attractor inference is not fabricated.
"""
from copy import deepcopy
from collections import Counter
import statistics

from .views import COMPLEXITY_TRADITION, COMPLEXITY_SOURCES, SOURCES

DIMENSIONS = {
    "local_global": {"label": "Local variability / global stability", "kind": "descriptive", "meaning": "Member contribution activity alongside explicit handoff-state continuity; not a universal variability–performance law."},
    "perturbation": {"label": "Perturbation response", "kind": "descriptive", "meaning": "Observed interruption windows, return/maintenance or first attainment, and censoring."},
    "coupling": {"label": "Informational coupling", "kind": "descriptive", "meaning": "Directed, permission-filtered representation exposure and provenance; not causal influence."},
    "cross_level": {"label": "Cross-level observations", "kind": "descriptive", "meaning": "Member actions, artifact transformations and team coordination viewed together; no inferred cross-level causality or physiology."},
    "attractors": {"label": "Attractor structure", "kind": "not_estimated", "meaning": "A stable handoff window is not an estimated attractor. State-space modeling and suitable repeated observations are not implemented."},
    "synchronization": {"label": "Synchronization", "kind": "not_estimated", "meaning": "Reported temporal-plan agreement is not oscillatory synchronization. Suitable time series and a defined synchrony estimator are not available."},
    "fractals": {"label": "Fractals / scale structure", "kind": "not_estimated", "meaning": "Short, uneven dependency waves cannot establish scale invariance or long memory; no fractal estimator is implemented."},
}


def observe(report):
    settings = report["observation_settings"]
    result = {"enabled": settings["enabled"], "source": COMPLEXITY_TRADITION, "representative_sources": deepcopy([SOURCES[k] for k in COMPLEXITY_SOURCES]), "dimensions": [], "aggregate_score": None}
    if not settings["enabled"]:
        return result
    events, snapshots = report["events"], report["snapshots"]
    for key in settings["dimensions"]:
        item = {"id": key, **DIMENSIONS[key], "status": "not_estimated" if DIMENSIONS[key]["kind"] == "not_estimated" else "not_observed" if not snapshots else "descriptive_only"}
        if snapshots and key == "local_global":
            activity = [sum(e["wave"] == s["wave"] and e["kind"] in {"representation_published", "handoff_acknowledged"} for e in events) for s in snapshots]
            mean = statistics.mean(activity) if activity else 0
            item["data"] = {"actions_by_wave": activity, "mean": mean, "activity_cv": statistics.pstdev(activity) / mean if mean else None,
                            "handoff_ready_by_wave": [s["handoff_coordination_ready"] for s in snapshots],
                            "time_base": "Uneven dependency waves, including engine setup boundaries; not uniformly sampled clock time."}
        elif snapshots and key == "perturbation":
            from .reporting import coordination_stability
            item["data"] = coordination_stability(snapshots, report["dynamics"])
        elif snapshots and key == "coupling":
            edges = Counter((e["author"], e["actor"]) for e in events if e["kind"] == "representation_exposed" and e["author"] not in {e["actor"], "researcher", "user"})
            item["data"] = {"directed_exposure_edges": [{"source": a, "target": b, "exposure_events": n} for (a, b), n in sorted(edges.items())],
                            "note": "Counts explicit artifact exposure, not every natural-language implication in filtered peer views."}
        elif snapshots and key == "cross_level":
            item["data"] = {"member_actions": dict(Counter(e["actor"] for e in events if e["kind"] in {"representation_published", "handoff_acknowledged"})),
                "artifact_versions": len([v for v in report["versions"] if v["author"] not in {"researcher", "user"}]),
                "due_handoffs": snapshots[-1]["due_handoffs"], "acknowledged_due_handoffs": snapshots[-1]["acknowledged_due_handoffs"]}
        result["dimensions"].append(item)
    return result
