"""Two approach families and focused team overviews, not three interchangeable quality scores.

Only metadata is projected. Opening a lens never changes a team or evaluates a model.
Representative sources situate wider traditions; no single work defines a tradition.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from teamknitt.engine.config import ConfigurationError

SOURCES = {
    "hutchins_1995": {"citation": "Hutchins, E. (1995). Cognition in the Wild.", "tradition": "Distributed problem-solving"},
    "mcneese_2021": {"citation": "McNeese, M. D., Salas, E., & Endsley, M. R. (Eds.). (2021). Foundations and Theoretical Perspectives of Distributed Team Cognition.", "tradition": "Perspectives on distributed problem-solving"},
    "cannon_bowers_1993": {"citation": "Cannon-Bowers, J. A., Salas, E., & Converse, S. (1993). Shared mental models in expert team decision making.", "tradition": "Shared mental models"},
    "wegner_1987": {"citation": "Wegner, D. M. (1987). Transactive memory: A contemporary analysis of the group mind.", "tradition": "Transactive memory"},
    "wu_2026": {"citation": "Wu et al. (2026). Measuring AI Agents as Teammates with Collaborative Intelligence.", "tradition": "Capability-conditioned teammate evaluation", "url": "https://doi.org/10.48550/arXiv.2611.02633"},
    "holland_1995": {"citation": "Holland, J. H. (1995). Hidden Order: How Adaptation Builds Complexity.", "tradition": "Complex adaptive systems"},
    "mitchell_2009": {"citation": "Mitchell, M. (2009). Complexity: A Guided Tour.", "tradition": "Complexity science"},
    "gorman_2017": {"citation": "Gorman, J. C., Dunbar, T. A., Grimm, D., & Gipson, C. L. (2017). Understanding and Modeling Teams As Dynamical Systems.", "tradition": "Team dynamics", "url": "https://doi.org/10.3389/fpsyg.2017.01053"},
}
COMPLEXITY_SOURCES = ("holland_1995", "mitchell_2009", "gorman_2017")
COMPLEXITY_TRADITION = "Complexity science, complex adaptive systems and team dynamics"

GROUPS = {
    "standard": {
        "label": "Standard", "subtitle": "Individual / component-centered",
        "question": "What do members bring, report and contribute as teammates?",
        "scope": "Member attributes, reported knowledge and behavior, and decomposed member-to-member relationships. Standard approaches can also study interactions; this is an explanatory emphasis, not a claim that all their models are linear.",
        "views": ["collaborative_intelligence", "shared_models"],
    },
    "complexity": {
        "label": "Complexity", "subtitle": "Interaction / system-centered",
        "question": "How is problem-solving produced across interacting agents, artifacts and time?",
        "scope": "Interaction, interdependence and system-level organization. Distributed problem-solving, team dynamics and coordination ask related questions here; not every distributed problem-solving account assumes nonlinear dynamics.",
        "views": ["distributed_problem_solving", "team_dynamics", "interaction_coordination"],
    },
}

VIEWS = {
    "collaborative_intelligence": {
        "group": "standard", "label": "Collaborative intelligence", "question": "What does a member contribute as a teammate, beyond being able to solve the task alone?",
        "scope": "The Standard group's behavioral view is informed by Measuring AI Agents as Teammates with Collaborative Intelligence. Optional, explicitly selected saved probe evidence remains a separate protocol context.",
        "sources": ["wu_2026"], "boundary": "No official CIB score or automatic evaluation. Task telemetry cannot establish a member's teammate capabilities, emotional traits or ethical competence.",
    },
    "shared_models": {
        "group": "standard", "label": "Shared models & member reports", "question": "How do members' explicit plans and perceived alignment compare?",
        "scope": "Member-centered reports and similarities provide one Standard perspective. Reported-plan agreement, reference conformity and perceived alignment are separate observables, not the whole problem-solving system.",
        "sources": ["cannon_bowers_1993", "mcneese_2021"], "boundary": "No inferred latent mental model, validated expertise or correctness. Agreeing with each other differs from agreeing with a declared reference; either can be wrong.",
    },
    "distributed_problem_solving": {
        "group": "complexity", "label": "Distributed problem-solving", "question": "How do agents, representations, tools and work dependencies jointly support problem-solving?",
        "scope": "Inspect complementary inputs, externalized work, expertise directories, transformations and handoffs across the configured system. This is teamknitt's product term for this perspective; original scholarly publication titles are retained.",
        "sources": ["hutchins_1995", "mcneese_2021", "wegner_1987"], "boundary": "Permissions are not exposure; exposure is not understanding. Work distribution, tool availability and handoff receipts do not establish a solved task or an emergent cognitive capacity.",
    },
    "team_dynamics": {
        "group": "complexity", "label": "Teams as dynamical systems", "question": "How do interaction and coordination change through time and around disturbances?",
        "scope": "Complexity science and complex adaptive systems, including the Santa Fe tradition, motivate temporal trajectories, feedback, stability and adaptation questions. Gorman et al. is one team-focused reference, not the umbrella theory.",
        "sources": list(COMPLEXITY_SOURCES), "boundary": "Santa Fe is a research tradition, not an endorsement or a validated team model. Short, uneven traces do not establish emergence, adaptation, attractors, synchrony or fractals.",
    },
    "interaction_coordination": {
        "group": "complexity", "label": "Interactions & coordination", "question": "Which contributions are encountered, transformed and acknowledged across members and artifacts?",
        "scope": "Observe directed artifact exposure, version-specific handoffs and cross-level records. Separate configured routes from recorded information flow; coordination is a process across the system.",
        "sources": ["hutchins_1995", "mcneese_2021", "gorman_2017"], "boundary": "Artifact exposure counts are not causal coupling or every message. Acknowledgement is not understanding or agreement, and missing observations are not zeros.",
    },
}

LEGACY_VIEWS = {
    "cognition": "distributed_problem_solving", "complexity": "team_dynamics",
}


def resolve_view(group=None, section=None, legacy=None):
    notice = None
    if legacy is not None:
        if group is not None or section is not None:
            raise ConfigurationError("Choose --group/--section or the legacy --lens flag, not both.")
        section = LEGACY_VIEWS.get(legacy, legacy)
        if legacy == "cognition":
            notice = "The former cognition overview is split: distributed problem-solving is under Complexity; shared-plan reports are under Standard. No team setting changed."
        else:
            notice = "Legacy --lens selection mapped to the grouped team views; use --group and --section."
    if section is not None:
        if section not in VIEWS:
            raise ConfigurationError("Choose a supported team-view section.")
        expected = VIEWS[section]["group"]
        if group is not None and group != expected:
            raise ConfigurationError("The selected section belongs to a different approach group.")
        group = expected
    if group is not None:
        if group not in GROUPS:
            raise ConfigurationError("Choose Standard or Complexity.")
        section = section or GROUPS[group]["views"][0]
    return group, section, notice


TEAMWORK = {
    "unsafe_pressure": {"label": "Resisting unsafe pressure", "question": "Does the member preserve the safety boundary when another member pushes against it?"},
    "misconduct": {"label": "Reporting misconduct", "question": "Does the member make suspected wrongdoing visible to an appropriate reviewer?"},
    "information": {"label": "Sharing and seeking information", "question": "Does the member obtain and contribute information needed by others?"},
    "emotional_support": {"label": "Emotional intelligence", "question": "How does the member respond to a teammate's expressed concerns? Structured probes cannot establish empathy."},
    "goal_alignment": {"label": "Keeping the team on track", "question": "Does the member attend to the stated objective and constraints when attention drifts?"},
    "conflict": {"label": "Handling conflict", "question": "How does the member handle incompatible proposals without assuming consensus is correctness?"},
    "initiative": {"label": "Taking initiative", "question": "Does the member act on an unmet need within its explicitly permitted scope?"},
    "taking_over": {"label": "Taking over", "question": "Does the member check inherited work and disclose unresolved problems?"},
}


def catalogue():
    return {"groups": deepcopy(GROUPS), "views": deepcopy(VIEWS), "representative_sources": deepcopy(SOURCES),
            "classification_note": "Two explanatory orientations, not an exhaustive or mutually exclusive partition of team research. Statistical methods are not theories of teams.",
            "switching_changes_configuration": False, "automatic_evaluation": False, "api_calls": 0}


def load_probe_summary(path: Path):
    """Read one explicitly selected saved protocol, once; export no messages or facts.

    This is a separate-context comparison, never a binding to current team members.
    The browser cannot select paths or cause a protocol run.
    """
    from .probes.reporting import load_run, report
    selected = Path(path)
    if selected.is_symlink() or selected.is_dir() and (selected / "run.json").is_symlink():
        raise ConfigurationError("Select a regular saved probe record, not a symlink.")
    r = report(load_run(selected))
    scores = r["scores"]
    fields = ("id", "label", "tasks", "eligible_tasks", "excluded_alone_failed", "unknown_alone_incomplete",
              "complete_eligible_tasks", "test_score", "baseline_score", "drop_points", "ci95")
    return {"scope": "separate_protocol_record", "run_id": r["run_id"], "mode": r["mode"], "status": r["status"],
            "evidence_label": r["evidence_label"], "configuration_sha256": r["configuration_sha256"],
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "coverage": {k: scores[k] for k in ("task_count", "eligible_tasks", "expected_episode_count", "completed_episode_count", "missing_or_failed_episode_count")},
            "dimensions": [{k: deepcopy(d[k]) for k in fields} for d in scores["dimensions"]],
            "aggregation": scores["aggregation"], "interval_note": scores["interval_note"],
            "binding": "Separate protocol context only; not evidence that this task team, its members or its topology have these capabilities."}


def build_views(report, probe_summary=None):
    result = deepcopy(VIEWS)
    c = report["cognition"]
    snapshots = report["snapshots"]
    last = snapshots[-1] if snapshots else None
    result["shared_models"].update(status="descriptive_only" if last else "configuration_only", signals={
        "configured_roles": len(c["roles"]), "representations": len(c["representations"]),
        "expertise_assignments": len(c["expertise_directory"]), "handoff_contracts": len(c["handoffs"]),
        "latest_wave": last["wave"] if last else None,
        "temporal_reports": last["temporal_reports"] if last else None,
        "fresh_temporal_reports": last.get("fresh_temporal_reports") if last else None,
        "reported_plan_pair_agreement": last["reported_plan_pair_agreement"] if last else None,
        "reported_plans_matching_reference": last["reported_plans_matching_reference"] if last else None,
        "perceived_in_sync_reports": last["perceived_in_sync_reports"] if last else None,
        "perceived_in_sync_despite_reported_disagreement": len(last["perceived_in_sync_despite_reported_disagreement"]) if last else None,
    })
    attached = {d["id"]: d for d in probe_summary["dimensions"]} if probe_summary else {}
    dimensions = []
    for key, definition in TEAMWORK.items():
        evidence = deepcopy(attached.get(key))
        status = "not_evaluated" if probe_summary is None else "not_selected" if evidence is None else (
            "fixture_only" if probe_summary["mode"] != "live" else "incomplete_or_ineligible" if evidence["test_score"] is None else "separate_protocol_only")
        dimensions.append({"id": key, **definition, "status": status, "protocol_evidence": evidence})
    result["distributed_problem_solving"].update(status="descriptive_only" if last else "configuration_only", signals={
        "configured_roles": len(c["roles"]), "representations": len(c["representations"]),
        "source_inputs": sum(r["kind"] == "source" for r in c["representations"]),
        "expertise_assignments": len(c["expertise_directory"]), "work_units": len(c["work"]),
        "handoff_contracts": len(c["handoffs"]),
        "artifact_versions": len(report["versions"]) if last else None,
        "acknowledged_due_handoffs": last["acknowledged_due_handoffs"] if last else None,
    })
    result["collaborative_intelligence"].update(
        status="not_evaluated" if probe_summary is None else "separate_protocol_attached", dimensions=dimensions,
        probe_summary=deepcopy(probe_summary), team_capability_score=None,
        process_context={"artifact_exposures": sum(e["kind"] == "representation_exposed" for e in report["events"]),
                         "acknowledgements": sum(e["kind"] == "handoff_acknowledged" for e in report["events"]),
                         "note": "Activity counts supply context only; they do not score information sharing or other teammate capabilities."})
    result["team_dynamics"].update(status="disabled" if not report["observations"]["enabled"] else "descriptive_only" if last else "not_observed",
        observations=deepcopy(report["observations"]), conceptual_questions=[
            {"concept": "Feedback and interdependence", "question": "Which permitted contributions are encountered in later waves?", "status": "exposure_metadata_only"},
            {"concept": "Emergence and adaptation", "question": "Would repeated, independently evaluated trajectories support a system-level explanation?", "status": "not_estimated"},
            {"concept": "History and path dependence", "question": "How do prior exposures and interruptions relate to later recorded coordination?", "status": "descriptive_only" if last else "not_observed"},
        ])
    result["interaction_coordination"].update(
        status=result["team_dynamics"]["status"],
        observations={**deepcopy(report["observations"]), "dimensions": [deepcopy(d) for d in report["observations"]["dimensions"] if d["id"] in {"coupling", "cross_level"}]},
        handoffs=deepcopy(report["handoffs"]),
    )
    result["team_dynamics"]["observations"]["dimensions"] = [d for d in result["team_dynamics"]["observations"]["dimensions"] if d["id"] not in {"coupling", "cross_level"}]
    return result


def with_views(report, probe_summary=None):
    return {**report, "team_views": build_views(report, probe_summary), "view_groups": deepcopy(GROUPS), "view_sources": deepcopy(SOURCES)}
