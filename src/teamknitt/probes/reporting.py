"""Capability-conditioned task means; missing cells remain unknown, never zero-filled."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import statistics

from teamknitt.engine.config import ConfigurationError

from .config import DIMENSIONS, digest, validate
from .metrics import dynamics
from .scenarios import suite


def _interval(samples):
    values = sorted(samples)
    def quantile(p):
        index = (len(values) - 1) * p
        lo, hi = math.floor(index), math.ceil(index)
        return values[lo] + (values[hi] - values[lo]) * (index - lo)
    return [quantile(.025), quantile(.975)]


def aggregate(result):
    config = result["plan"]["configuration"]
    protocol = config["protocol"]
    index = {}
    expected = {(s.id, condition, seed) for s in suite(config)
                for condition, seed in [("alone", protocol["seeds"][0]), ("baseline", protocol["seeds"][0]),
                                        *(("test", seed) for seed in protocol["seeds"])]}
    scenario_dimensions = {s.id: s.dimension for s in suite(config)}
    for ep in result["episodes"]:
        if ep.get("dimension") != scenario_dimensions.get(ep.get("task_id")):
            raise ConfigurationError("Episode dimension does not match its declared task instance.")
        key = (ep["task_id"], ep["condition"], ep["seed"])
        if key in index or key not in expected:
            raise ConfigurationError("Duplicate or unexpected episode cell in the saved study.")
        if ep["status"] == "completed":
            outcome = ep.get("outcome")
            if (not isinstance(outcome, dict) or type(outcome.get("score")) not in (int, float)
                    or not math.isfinite(outcome["score"]) or not 0 <= outcome["score"] <= 1
                    or type(outcome.get("passed")) is not bool):
                raise ConfigurationError("A completed episode needs a finite code-checker outcome.")
        index[key] = ep

    def completed(key):
        row = index.get(key)
        return row if row and row["status"] == "completed" else None

    tasks = []
    grouped = defaultdict(list)
    for scenario in suite(config):
        alone = completed((scenario.id, "alone", protocol["seeds"][0]))
        baseline = completed((scenario.id, "baseline", protocol["seeds"][0]))
        tests = [completed((scenario.id, "test", seed)) for seed in protocol["seeds"]]
        eligibility = "unknown_alone_incomplete" if alone is None else "eligible" if alone["outcome"]["passed"] else "excluded_alone_failed"
        complete = eligibility == "eligible" and baseline is not None and all(t is not None for t in tests)
        task = {"task_id": scenario.id, "dimension": scenario.dimension, "eligibility": eligibility,
                "complete": complete, "test_repetitions_expected": len(tests),
                "test_repetitions_completed": sum(t is not None for t in tests),
                "alone_score": 100 * alone["outcome"]["score"] if alone else None,
                "baseline_score": 100 * baseline["outcome"]["score"] if baseline and eligibility == "eligible" else None,
                "test_score": 100 * statistics.mean(t["outcome"]["score"] for t in tests) if complete else None}
        task["drop_points"] = task["baseline_score"] - task["test_score"] if complete else None
        tasks.append(task)
        grouped[scenario.dimension].append(task)
    dimensions = []
    for dim in protocol["dimensions"]:
        rows = grouped[dim]
        eligible = [t for t in rows if t["eligibility"] == "eligible"]
        complete = [t for t in eligible if t["complete"]]
        unknown = sum(t["eligibility"] == "unknown_alone_incomplete" for t in rows)
        usable = len(eligible) > 0 and len(complete) == len(eligible) and unknown == 0
        dimensions.append({"id": dim, "label": DIMENSIONS[dim], "tasks": len(rows),
                           "eligible_tasks": len(eligible), "excluded_alone_failed": len(rows) - len(eligible) - unknown,
                           "unknown_alone_incomplete": unknown, "complete_eligible_tasks": len(complete),
                           "test_score": statistics.mean(t["test_score"] for t in complete) if usable else None,
                           "baseline_score": statistics.mean(t["baseline_score"] for t in complete) if usable else None,
                           "drop_points": statistics.mean(t["drop_points"] for t in complete) if usable else None,
                           "ci95": None})
    overall = statistics.mean(d["test_score"] for d in dimensions) if all(d["test_score"] is not None for d in dimensions) else None
    baseline = statistics.mean(d["baseline_score"] for d in dimensions) if overall is not None else None
    interval_reason = "Descriptive statistics selected by the user."
    overall_ci = None
    if config["statistics"]["method"] == "task_bootstrap":
        interval_reason = "At least two complete eligible tasks in every selected dimension are required."
        if overall is not None and all(d["eligible_tasks"] >= 2 for d in dimensions):
            rng = random.Random(config["statistics"]["seed"])
            samples = {d["id"]: [] for d in dimensions}
            macro = []
            for _ in range(config["statistics"]["resamples"]):
                means = []
                for d in dimensions:
                    cluster = [t["test_score"] for t in grouped[d["id"]] if t["eligibility"] == "eligible"]
                    value = statistics.mean(rng.choices(cluster, k=len(cluster)))
                    samples[d["id"]].append(value)
                    means.append(value)
                macro.append(statistics.mean(means))
            overall_ci = _interval(macro)
            for d in dimensions:
                d["ci95"] = _interval(samples[d["id"]])
            interval_reason = "Stratified task-cluster percentile bootstrap; repeats are averaged within each task, not treated as independent tasks."
    return {"overall_score": overall, "baseline_score": baseline,
            "drop_points": baseline - overall if overall is not None else None,
            "ci95": overall_ci, "interval_note": interval_reason, "dimensions": dimensions, "tasks": tasks,
            "eligible_tasks": sum(t["eligibility"] == "eligible" for t in tasks),
            "task_count": len(tasks), "expected_episode_count": len(expected),
            "completed_episode_count": sum(e["status"] == "completed" for e in index.values()),
            "missing_or_failed_episode_count": len(expected) - sum(e["status"] == "completed" for e in index.values()),
            "aggregation": "Equal dimension weights; within dimension equal task weights; test seeds averaged within task. Eligibility uses the single full-information alone trial, never the baseline."}


def report(result):
    c = validate(result["plan"]["configuration"])
    if digest(c) != result["configuration_sha256"]:
        raise ConfigurationError("Saved configuration identity does not match its snapshot.")
    scores = aggregate(result)
    episodes = []
    for ep in result["episodes"]:
        # Export trace metadata only. No natural-language message or private fact values.
        clean = {k: deepcopy(v) for k, v in ep.items() if k not in {"events", "rounds"}}
        clean["events"] = [{k: deepcopy(v) for k, v in event.items() if k != "content"} for event in ep["events"]]
        clean["dynamics"] = dynamics(ep, c)
        episodes.append(clean)
    live = result["mode"] == "live"
    return {"schema_version": 1, "run_id": result["run_id"], "name": c["name"],
            "status": result["status"], "mode": result["mode"], "fixture_policy": result.get("fixture_policy"),
            "started_at": result["started_at"], "finished_at": result.get("finished_at"),
            "teamknitt_version": result["teamknitt_version"], "configuration_sha256": digest(c),
            "implementation_sha256": result.get("implementation_sha256"), "python_version": result.get("python_version"),
            "evidence_label": "Live synthetic protocol probes — not a CIB score" if live else
                              "Offline fixture — illustrative software behavior, not model evidence",
            "team": c["team"], "protocol": c["protocol"], "communication": c["communication"],
            "perturbations": c["perturbations"], "budget": c["budget"], "statistics": c["statistics"],
            "provider_bindings": {m["id"]: {"provider": m.get("provider"),
                "model": c["providers"][m["provider"]]["model"] if m["kind"] == "model" else "Controlled script"}
                for m in c["team"]["members"]},
            "usage": result["usage"], "scores": scores, "episodes": episodes,
            "limitations": ["Original, public arithmetic/ledger micro-worlds; not the 240-task Collaborative Intelligence Benchmark.",
                "Structured acts are narrow proxies; they do not validate empathy, honesty, respect or scientific competence.",
                "One alone trial determines eligibility, with full-information versus distributed-information differences.",
                "Missing/incomplete cells are unknown, not silently excluded or counted as behavioral failures.",
                "Counts, entropy, reciprocity and task-state return are descriptive; no causal coupling, attractor, fractal or synchrony inference.",
                "No automatic team redesign, model switching, delegation, retries or budget increases."]}


def load_run(path: Path):
    if path.is_dir():
        path = path / "run.json"
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ConfigurationError("Saved run exceeds the local report size limit.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        report(value)
        return value
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError("Saved run does not match the Teamknitt run format.") from error
