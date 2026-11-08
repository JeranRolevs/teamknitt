"""Configuration and process evidence, not a teammate leaderboard or latent cognition score."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from labtune.config import ConfigurationError
from .config import PERSPECTIVES, digest, resource


def plan_report(plan):
    base, c = plan["labtune_plan"], plan["configuration"]["cognition"]
    topology = deepcopy(plan["topology"])
    if plan["schema_version"] == 3:
        topology["positions"] = json.loads(resource("topology-layouts.json").read_text())[topology["kind"]][str(len(topology["members"]))]
    else:
        topology["positions"] = []
    record = {"schema_version": 3, "name": plan["name"], "mode": "configuration", "status": "planned_not_executed",
            "evidence_label": "Configuration only — no members, model calls or task execution started",
            "configuration_sha256": plan["configuration_sha256"],
            "labtune_configuration_sha256": plan["labtune_configuration_sha256"],
            "labtune_variant": plan["labtune_variant"], "design": base["design"],
            "team_schema_version": plan["schema_version"], "mission": plan["configuration"].get("mission", {"purpose": "research", "brief_file": plan["mission_binding"]["path"], "deliverable": "Research contributions for review", "review": "user_review"}),
            "topology": topology, "observation_settings": plan["observations"],
            "goal_achieved": None, "task_review": "not_started",
            "personas": base["personas"], "communication": base["communication"],
            "budget": base["budget"], "resources": base["resources"], "delegation": base["delegation"],
            "statistics": base["statistics"], "generation_provider": {
                key: base["generation_provider"][key] for key in ("model", "adapter", "max_output_tokens")},
            "decision_service": {key: base["decision_service"][key] for key in ("mode", "specialist", "max_calls_per_episode")},
            "cognition": c, "perspective_notes": {p: PERSPECTIVES[p] for p in c["perspectives"]},
            "dynamics": plan["configuration"]["dynamics"], "waves": plan["waves"],
            "source_bindings": plan["source_bindings"], "run_id": None,
            "snapshots": [], "events": [], "versions": [], "handoffs": [], "temporal_models": {},
            "usage": {"provider_requests": 0}, "current_operations": [], "scientific_quality_score": None, "observations": {"enabled": plan["observations"]["enabled"], "dimensions": [], "aggregate_score": None}}


    from .observations import observe
    record["observations"] = observe(record)
    return record


def coordination_stability(snapshots, dynamics):
    span = dynamics["stable_waves"]
    stable = []
    for i in range(len(snapshots) - span + 1):
        window = snapshots[i:i + span]
        if all(s["handoff_coordination_ready"] for s in window) and window[-1]["wave"] - window[0]["wave"] == span - 1:
            stable.append({"from_wave": window[0]["wave"], "through_wave": window[-1]["wave"]})
    observations = []
    for p in dynamics["perturbations"]:
        start, end = p["at_wave"], p["at_wave"] + p["duration"] - 1
        observed = any(s["wave"] == start for s in snapshots)
        before = [s for s in snapshots if s["wave"] < start]
        established = len(before) >= span and all(s["handoff_coordination_ready"] for s in before[-span:])
        return_window = next((w for w in stable if w["from_wave"] >= end), None)
        observations.append({"intervention": p["id"], "status": "not_observed" if not observed else
            "baseline_not_established" if not established else "right_censored" if return_window is None else "observed_return_or_maintenance",
            "return_delay_waves": return_window["from_wave"] - end if observed and established and return_window else None,
            "first_stable_attainment_after_end": return_window["from_wave"] - end if observed and return_window else None,
            "other_interventions_in_observation_window": [q["id"] for q in dynamics["perturbations"] if q["id"] != p["id"] and
                q["at_wave"] <= (snapshots[-1]["wave"] if snapshots else end) and q["at_wave"] + q["duration"] - 1 >= start]})
    return {"span": span, "stable_windows": stable, "perturbation_observations": observations,
            "definition": "Consecutive waves with all due handoff contracts acknowledged or published without an acknowledgement requirement. Not task truth, latent cognition or an attractor estimate."}


def _read(path):
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ConfigurationError("Saved record exceeds the local report size bound.")
    return json.loads(path.read_text(encoding="utf-8"))


def current_operations(root, status):
    path = root / "activity.jsonl"
    if not path.is_file() or path.is_symlink():
        return [], 0
    pending = {}
    with path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - 512_000))
        raw = stream.read().decode("utf-8", errors="replace")
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # A writer can be between bytes; never invent an active event.
        request = event.get("request_id")
        if not isinstance(request, str) or not request:
            continue
        if event.get("kind") == "provider_request":
            actor = event.get("actor") or {}
            pending[request] = {"request_id": request, "actor": actor.get("id"), "node": event.get("node"),
                "provider": event.get("provider"), "model": event.get("model"), "started_at": event.get("time")}
        elif event.get("kind") in {"provider_response", "provider_error"}:
            pending.pop(request, None)
    return list(pending.values()) if status == "running" else [], len(pending) if status != "running" else 0


def build_report(run_directory: Path):
    root = run_directory.resolve()
    try:
        identity = _read(root / "team-run.json")
        plan = _read(root / "team-plan.json")
        state = _read(root / "cognition-state.json")
        summary = _read(root / "summary.json")
        telemetry = _read(root / "team-telemetry.json") if (root / "team-telemetry.json").is_file() else {}
        heartbeat = _read(root / "activity-heartbeat.json") if (root / "activity-heartbeat.json").is_file() else {}
        binding = plan["labtune_plan"]["configuration_snapshot"]["cognition_binding"]
        if digest(binding) != identity["configuration_sha256"] or plan["configuration_sha256"] != identity["configuration_sha256"]:
            raise ConfigurationError("Saved cognition configuration identity does not match its binding.")
        if binding["cognition"] != plan["configuration"]:
            raise ConfigurationError("Saved team controls changed without a new configuration identity.")
        report = plan_report(plan)
        report.update(mode=identity["mode"], run_id=identity["run_id"], status=summary["status"],
            fixture_policy=identity.get("fixture_policy"), implementation_sha256=identity["implementation_sha256"],
            evidence_label="Offline fixture — representation and coordination demonstration, not a model or scientific evaluation"
                           if identity["mode"] == "offline_fixture" else "Team task execution — contributions require user review; monitoring is not proof of goal achievement",
            usage={"provider_requests": telemetry.get("provider_requests", summary.get("provider_post_requests", 0)), "elapsed_seconds": telemetry.get("elapsed_seconds", summary.get("elapsed_seconds")), **telemetry.get("usage", summary.get("usage", {}))},
            snapshots=state["snapshots"], handoffs=state["handoffs"], temporal_models=state["temporal_models"],
            skipped_episodes=state["skipped_episodes"],
            verification_status=summary["verification_status"], task_review="awaiting_user_review" if summary["status"] != "running" else "in_progress",
            last_telemetry=telemetry.get("last_updated"), heartbeat_at=heartbeat.get("time"), deliverable_file="deliverable.md")
        # Only reference/version metadata. No source text, generated note text, prompts or private credentials.
        report["current_operations"], report["unresolved_requests_at_end"] = current_operations(root, summary["status"])
        report["versions"] = [{"representation": ref, **{k: deepcopy(v[k]) for k in ("version", "author", "wave", "uses")}}
                              for ref, versions in state["versions"].items() for v in versions]
        report["events"] = [{k: deepcopy(v) for k, v in e.items() if k not in {"content", "summary"}} for e in state["events"]]
        from .observations import observe
        report["observations"] = observe(report)
        if report["observation_settings"]["enabled"] and "perturbation" in report["observation_settings"]["dimensions"]:
            report["coordination_stability"] = coordination_stability(state["snapshots"], report["dynamics"])
        report["limitations"] = [
            "The handbook provides multiple perspectives, not a single universal prescription or an agent benchmark.",
            "Configured roles/capabilities are assignments, not validated human-like expertise or diversity.",
            "Exposure, acknowledgement and citation do not establish comprehension, agreement or truth.",
            "Pairwise agreement compares explicit temporal reports, not latent mental models; matching each other differs from matching the reference.",
            "Perceived alignment is self-report, recorded separately from reported-plan agreement and task outcomes.",
            "Observed interaction and perturbation traces do not establish causal coupling, attractors, power laws or improved science.",
            "No automated model choice, team redesign, statistical approach switch or budget increase is performed."]
        return report
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError("This is not a valid Teamknitt cognition run. Use 'teamknitt probes' for older optional probe records.") from error
