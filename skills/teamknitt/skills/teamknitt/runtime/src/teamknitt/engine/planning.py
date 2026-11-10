"""Compile selectable designs into inspectable, nonexecuting skeleton plans."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .config import ConfigurationError, load_config, load_design, merge, project_file, validate_config
from .persistence import resolve_execution, scientist_graph

PROFILES = ("preset", "none", "low", "intermediate", "high", "wisdom_only")
STATISTICAL_APPROACHES = ("frequentist",)
PRIME_PHASES = {
    "independent_framing", "independent_positions", "independent_proposals",
    "parallel_episodes", "parallel_tests", "discriminating_test",
}
VERIFICATION_PHASES = {"verification", "independent_verification"}
COORDINATION_PHASES = {
    "optional_handoff", "translation_workshop", "framework_revision", "paired_challenge",
    "track_charters", "hub_review", "scoped_handoffs", "peer_roundtable", "task_adoption",
    "evidence_review",
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def resolve_sharing(config: dict, design: dict) -> dict:
    requested = config["communication"]
    profile = requested["profile"]
    if profile == "preset":
        recommended = design["communication"]["recommended"]
        detail = recommended["detail"]
        wisdom = recommended["wisdom"]["enabled"]
    else:
        detail = "none" if profile == "wisdom_only" else profile
        wisdom = profile == "wisdom_only"
    if requested["wisdom"] is not None:
        if profile == "wisdom_only" and requested["wisdom"] is False:
            raise ConfigurationError("wisdom_only cannot disable wisdom")
        wisdom = requested["wisdom"]
    effective = ("wisdom_only" if wisdom else "none") if detail == "none" else detail + ("+wisdom" if wisdom else "")
    horizontal_files = ([f"{detail}.md"] if detail != "none" else []) + (["wisdom.md"] if wisdom else [])
    content = {"none": "no_peer_research", "low": "notable_dead_ends",
               "intermediate": "compact_findings", "high": "detailed_findings"}[detail]
    if effective == "wisdom_only":
        content = "conditional_abstractions_only"
    return {
        "requested_profile": profile, "effective_profile": effective,
        "detail": detail, "wisdom": wisdom, "files": horizontal_files,
        "research_exchange": bool(horizontal_files), "content_limit": content,
        "cadence": requested["cadence"], "max_read_words": requested["max_read_words"],
        "child_policy": "inherit_or_restrict", "exposure_log_required": True,
        "hidden_peer_updates_allowed": False,
    }


def resolve_roles(config: dict, design: dict) -> list[dict]:
    overrides = config["teams"]["role_instances"]
    known = {persona["id"] for persona in design["personas"]}
    if unknown := set(overrides) - known:
        raise ConfigurationError(f"unknown persona overrides: {sorted(unknown)}")
    roles = []
    for persona in design["personas"]:
        count = overrides.get(persona["id"], 1)
        for index in range(count):
            roles.append({**persona, "instance_id": f"{persona['id']}.{index + 1}",
                          "model_binding": "shared_model", "horizontal_policy": "resolved_mission_policy"})
    if not any(role["role"] == "prime" for role in roles):
        raise ConfigurationError("effective design needs at least one prime instance")
    return roles


def compile_work_graph(design: dict, roles: list[dict], sharing: dict) -> list[dict]:
    """One structural episode DAG; dependencies order work, never grant data access."""
    nodes = [{"id": "qualify_domain", "kind": "qualification", "actors": ["system:domain"],
              "depends_on": [], "input_contract": "mission", "output_contract": "evaluation_receipt",
              "read_scope": "declared_qualification_inputs", "research_activity": "planned"}]
    previous = nodes[:]
    primes = [role["instance_id"] for role in roles if role["role"] == "prime"]
    coordinators = [role["instance_id"] for role in roles if role["role"] == "coordinator"]
    for number, phase in enumerate(design["collaboration"]["phases"], 1):
        current = []
        if phase in PRIME_PHASES:
            for actor in primes:
                local = [node["id"] for node in previous if node["actors"] == [actor]]
                deps = local or [node["id"] for node in previous]
                current.append({"id": f"{number}:{phase}:{actor}", "kind": "research_episode",
                                "actors": [actor], "depends_on": deps,
                                "input_contract": "mission" if phase.startswith("independent_") else "experiment",
                                "output_contract": "research_event",
                                "read_scope": "own_team_and_permitted_snapshot", "research_activity": "planned"})
        else:
            verification = phase in VERIFICATION_PHASES
            kind = "verification" if verification else ("coordination" if phase in COORDINATION_PHASES else "unbound_extension")
            actors = ["system:verification"] if verification else (coordinators or primes)
            activity = "planned"
            if not verification:
                activity = "operational_only" if not sharing["research_exchange"] else sharing["content_limit"]
            if kind == "unbound_extension":
                activity = "requires_procedure_binding"
            current.append({"id": f"{number}:{phase}", "kind": kind, "actors": actors,
                            "depends_on": [node["id"] for node in previous],
                            "input_contract": "experiment" if verification else "research_event",
                            "output_contract": "evaluation_receipt" if verification else "research_event",
                            "read_scope": "protected_confirmation" if verification else "recipient_filtered_inputs",
                            "research_activity": activity})
        nodes.extend(current)
        previous = current
    seen = set()
    for node in nodes:
        if node["id"] in seen or not set(node["depends_on"]) <= seen:
            raise ConfigurationError("compiled work graph has duplicate IDs or invalid dependencies")
        seen.add(node["id"])
    return nodes


def binding_hashes(project: Path) -> dict[str, str]:
    bindings = {}
    package = Path(__file__).resolve().parent
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json", ".yaml"}:
            bindings[f"package/{path.relative_to(package).as_posix()}"] = digest(path.read_bytes())
    for folder in ("prompts", "templates/records"):
        for path in sorted((project / folder).rglob("*")):
            if path.is_file():
                relative = path.relative_to(project).as_posix()
                safe = project_file(project, relative)
                bindings[relative] = digest(safe.read_bytes())
    return bindings


def compile_plan(project: Path, config_path: str = "configs/lab.yaml", *,
                 design_file: str | None = None, profile: str | None = None,
                 wisdom: bool | None = None, statistical_approach: str | None = None,
                 config_overrides: dict | None = None, persistence: str | None = None,
                 sequences: int | None = None, effort_mode: str | None = None,
                 sequence_context: str | None = None) -> dict:
    project = project.resolve()
    config = load_config(project, config_path)
    if config_overrides is not None:
        config = merge(config, config_overrides)
    if design_file is not None:
        config["lab"]["design_file"] = design_file
    if profile is not None:
        config["communication"]["profile"] = profile
    if wisdom is not None:
        config["communication"]["wisdom"] = wisdom
    if statistical_approach is not None:
        config["statistics"]["approach"] = statistical_approach
    for key, value in (("persistence", persistence), ("sequences", sequences),
                       ("effort_mode", effort_mode), ("context_policy", sequence_context)):
        if value is not None:
            config["single_scientist"][key] = value
    config = validate_config(config)
    design, design_text = load_design(project, config["lab"]["design_file"])
    roles = resolve_roles(config, design)
    sharing = resolve_sharing(config, design)
    delegation = deepcopy(design["delegation"])
    for field in ("max_depth", "max_children_per_agent"):
        if config["teams"][field] is not None:
            delegation[field] = config["teams"][field]
    delegation["max_active_descendants"] = config["teams"]["max_active_descendants"]
    delegation["budget"] = "inherited"
    execution = resolve_execution(config, design, roles, delegation)
    if execution["kind"] != "single_scientist" and any(
            value is not None for value in (persistence, sequences, effort_mode, sequence_context)):
        raise ConfigurationError("Persistence and sequence overrides require the single-scientist design.")
    meeting = deepcopy(design["meetings"])
    meeting["enabled"] = meeting.pop("recommended")
    for field, value in config["meetings"].items():
        if value is not None:
            meeting[field] = value
    meeting["research_content_limit"] = sharing["content_limit"]
    meeting["operational_only"] = meeting["enabled"] and not sharing["research_exchange"]
    search = deepcopy(config["search"])
    search["independent_paths"] = search["independent_paths"] or sum(role["role"] == "prime" for role in roles)
    notes = ["Structural plan only: no LLM, specialist, agent, experiment, or evaluator is executed.",
             "Work-graph edges represent readiness dependencies; read_scope controls information exposure.",
             "The user selects and changes lab settings; no automated lab optimization or promotion is defined.",
             "Configuration snapshots record settings for traceability; they do not lock user choices.",
             "Style and communication comparisons are user-run later; no preset is selected by performance here."]
    recommendation = design["communication"]["recommended"]
    if sharing["detail"] != recommendation["detail"] or sharing["wisdom"] != recommendation["wisdom"]["enabled"]:
        notes.append("User communication overrides the preset; collaboration content is restricted to the effective profile.")
    if len([role for role in roles if role["role"] == "prime"]) < 2:
        notes.append("Single-prime variant: multi-party prime collaboration is inactive.")
    if not coordinators_present(design, roles):
        notes.append("A preset coordinator is disabled; the structural phase uses permitted prime roles. No leadership claim is inferred.")
    if execution["kind"] == "single_scientist":
        notes.append("One scientist executes sequences in order; all work shares the selected budgets. Confirmation is after all sequences.")
    snapshot_payload = {
        "design_sha256": digest(design_text.encode()), "resolved_config": config,
        "bindings": binding_hashes(project), "personas": roles,
    }
    snapshot_hash = digest(json.dumps(snapshot_payload, sort_keys=True, allow_nan=False).encode())
    return {
        "schema_version": 1, "status": "structural_plan", "runtime_execution": "not_started",
        "configuration_snapshot": {"id": f"config-{snapshot_hash[:20]}", "purpose": "audit_only",
                                   "sha256": snapshot_hash, **snapshot_payload},
        "configuration_control": {"authority": "user", "settings_editable": True,
                                  "changes_recorded_at": "explicit_effective_boundary",
                                  "previous_exposure_preserved": True},
        "design": {"id": design["id"], "name": design["name"], "file": config["lab"]["design_file"],
                   "governance": design["governance"], "procedure": design["collaboration"]["procedure"]},
        "personas": roles, "delegation": delegation, "resources": config["resources"], "execution": execution,
        "budget": config["budget"], "search": search, "communication": sharing,
        "statistics": {**config["statistics"], "application": "when_needed", "status": "interface_only",
                       "protocol_owner": "domain_adapter", "silent_approach_switch_allowed": False},
        "meetings": meeting, "decision_service": {**config["decisions"], "caller_scope": "permitted_evidence_only",
                                                 "shadow_visible_to_caller": False, "fallback": "same_llm_within_budget"},
        "memory_layers": ["immutable_evidence", "scoped_operational_playbooks", "recipient_filtered_views"],
        "work_graph": scientist_graph(roles[0]["instance_id"], execution) if execution["kind"] == "single_scientist"
                      else compile_work_graph(design, roles, sharing),
        "planned_run_layout": ["configuration/snapshots/", "configuration/changes/", "mission.json", "events/", "work/", "evidence/",
                               "playbooks/", "communication/snapshots/", "communication/reads/",
                               "verification/", "assets/"],
        "notes": notes,
    }


def coordinators_present(design: dict, roles: list[dict]) -> bool:
    required = {persona["id"] for persona in design["personas"] if persona["role"] == "coordinator"}
    actual = {role["id"] for role in roles}
    return required <= actual


def catalogue(project: Path) -> list[dict]:
    rows = []
    for path in sorted((project / "lab_designs").glob("*.md")):
        if path.name in {"README.md", "_template.md"}:
            continue
        relative = path.relative_to(project).as_posix()
        design, _ = load_design(project, relative)
        rows.append({"id": design["id"], "name": design["name"], "file": relative,
                     "governance": design["governance"]})
    if not rows:
        raise ConfigurationError("no lab-design presets found")
    return rows
