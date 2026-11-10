"""Distributed-problem-solving controls layered on an actual teamknitt study variant.

teamknitt remains authoritative for organization, generation/decision models, sharing,
delegation, statistics and budgets. This module never reads credentials or calls models.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from teamknitt.engine.config import ConfigurationError, parse_yaml, project_file, merge
from .topology import links as topology_links, TOPOLOGIES
from .compat import normalize_team_config
from teamknitt.engine.study import load_study, plans

PERSPECTIVES = {
    "distributed_problem_solving": {"tradition": "Distributed problem-solving", "sources": ["hutchins_1995", "mcneese_2021"], "focus": "People, representations, technology, work and context as the unit of analysis."},
    "information_processing": {"tradition": "Team information processing", "sources": ["mcneese_2021"], "focus": "Task type, information distribution, interaction and coordination requirements."},
    "shared_mental_models": {"tradition": "Shared mental models", "sources": ["cannon_bowers_1993", "mathieu_2000", "mcneese_2021"], "focus": "Taskwork, teamwork and timework; explicit reported-plan agreement is not latent mental-model similarity, accuracy or perceived alignment."},
    "transactive_memory": {"tradition": "Transactive memory", "sources": ["wegner_1987", "lewis_2003", "kozlowski_klein_2000", "mcneese_2021"], "focus": "Differentiated/compilational organization: complementary knowledge and an explicit directory of assigned holders, not measured expertise or an effectiveness score."},
    "coaction": {"tradition": "Coaction and affordances", "sources": ["mcneese_2021"], "focus": "Action opportunities depend on actor capacities and available informational structures."},
    "interactive_dynamics": {"tradition": "Complexity science and team dynamics", "sources": ["holland_1995", "mitchell_2009", "gorman_2017"], "focus": "Interdependence, feedback and interaction through time; team-focused dynamical work is one part of a broader complexity-science tradition."},
}


def resource(name):
    return files("teamknitt.resources").joinpath(name)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def validate(value):
    value = normalize_team_config(value)
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ConfigurationError("Cognition settings must contain finite JSON data.") from error
    schema_name = "research.schema.json" if isinstance(value, dict) and value.get("schema_version") == 2 else "team.schema.json"
    schema = json.loads(resource(schema_name).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(list(e.absolute_path)))
    if errors:
        error = errors[0]
        raise ConfigurationError(f"{'.'.join(map(str, error.absolute_path)) or 'team'}: {error.message}")
    c = deepcopy(value)
    if c["schema_version"] == 3:
        topology_links(c["team"])
    for section in ("roles", "representations", "work", "handoffs", "affordances"):
        rows = c["cognition"][section]
        key = "actor" if section == "roles" else "id"
        if len({r[key] for r in rows}) != len(rows):
            raise ConfigurationError(f"cognition.{section}: duplicate {key}.")
    ids = [p["id"] for p in c["dynamics"]["perturbations"]]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("Perturbation IDs must be unique.")
    return c


def load(workspace: Path):
    return validate(parse_yaml(project_file(workspace, "team.yaml").read_text(encoding="utf-8")))


def waves(graph):
    pending = {n["id"]: n for n in graph}
    if len(pending) != len(graph):
        raise ConfigurationError("Duplicate teamknitt workflow node.")
    complete, result = set(), []
    while pending:
        ready = [n for n in pending.values() if set(n["depends_on"]) <= complete]
        if not ready:
            raise ConfigurationError("Invalid teamknitt dependency graph.")
        result.append(ready)
        for n in ready:
            complete.add(n["id"])
            del pending[n["id"]]
    return result


def engine_study(workspace, config, *, study_path="study.yaml"):
    """Translate explicit teamknitt task/count/sharing settings into the teamknitt engine; never alter models or budgets."""
    study = load_study(workspace, study_path)
    if config["schema_version"] == 2:
        return study, config["engine"]["variant"]
    selected = config["engine"]["variant"]
    variant = next((v for v in study["variants"] if v["id"] == selected), None)
    if variant is None:
        raise ConfigurationError("engine.variant must name an existing engine study variant.")
    brief = project_file(workspace, config["mission"]["brief_file"])
    if brief.stat().st_size > 100_000 or brief.name.startswith(".env") or any(part in {".git", ".venv", "trials", "runs", "setup", "results", "local-reference"} for part in Path(config["mission"]["brief_file"]).parts):
        raise ConfigurationError("The user brief must be bounded task text, not a credential or private runtime path.")
    study["problem_file"] = config["mission"]["brief_file"]
    overrides = merge(variant["overrides"], {"lab": {"design_file": config["engine"]["design_file"]},
        "communication": {"profile": config["communication"]["profile"], "wisdom": config["communication"]["wisdom"],
                          "max_read_words": config["communication"]["max_read_words"]}})
    overrides.setdefault("teams", {})["role_instances"] = {"member": config["team"]["members"]}
    # Explicit member-count authority is the teamknitt setting, not leftover engine persona counts.
    study["base_overrides"].setdefault("teams", {}).pop("role_instances", None)
    variant["overrides"] = overrides
    return study, selected


def compile_plan(workspace: Path, config=None, *, study_path="study.yaml"):
    """Resolve explicit cognitive controls against—not alongside—a teamknitt plan."""
    root = workspace.resolve()
    c = validate(config) if config is not None else load(root)
    study, selected = engine_study(root, c, study_path=study_path)
    resolved = plans(root, study, workspace=root)
    if selected not in resolved:
        raise ConfigurationError("teamknitt.engine.variant must name a variant in study.yaml.")
    base = resolved[selected]
    actors = {p["instance_id"] for p in base["personas"]}
    routes = set(topology_links(c["team"])) if c["schema_version"] == 3 else {(a, b) for a in actors for b in actors if a != b}
    if any(a not in actors or b not in actors for a, b in routes):
        raise ConfigurationError("Topology links must resolve to the engine's configured team members.")
    roles = {r["actor"]: r for r in c["cognition"]["roles"]}
    if set(roles) != actors:
        raise ConfigurationError("Cognition role bindings must match the resolved teamknitt persona instance IDs exactly; edit bindings explicitly after changing a design/count.")
    reps = {r["id"]: r for r in c["cognition"]["representations"]}
    work = {w["id"]: w for w in c["cognition"]["work"]}
    handoffs = {h["id"]: h for h in c["cognition"]["handoffs"]}
    phases = {n["id"].split(":")[1] for n in base["work_graph"] if ":" in n["id"]}
    phase_actors = {phase: {a for n in base["work_graph"] if ":" in n["id"] and n["id"].split(":")[1] == phase for a in n["actors"]} for phase in phases}
    mode = c["cognition"]["task"]["interaction"]
    sharing = base["communication"]
    if mode == "independent" and sharing["research_exchange"]:
        raise ConfigurationError("Independent interaction requires explicitly disabled teamknitt peer research exchange.")
    if mode == "limited_exchange" and sharing["detail"] == "high":
        raise ConfigurationError("Limited exchange cannot silently coexist with teamknitt high-detail sharing; choose controls explicitly.")
    if mode == "deliberative" and not sharing["research_exchange"]:
        raise ConfigurationError("Deliberative interaction requires an explicitly enabled teamknitt sharing channel.")
    if not set(c["cognition"]["temporal_reference"]["order"]) <= phases:
        raise ConfigurationError("Temporal reference must name phases in the selected teamknitt design.")
    source_bindings = {}
    for r in reps.values():
        if not set(r["readers"]) <= actors or not set(r["writers"]) <= actors:
            raise ConfigurationError("Representation readers/writers must be resolved teamknitt actors.")
        if not set(r["writers"]) <= set(r["readers"]):
            raise ConfigurationError("Representation writers must also be readers.")
        if r["kind"] == "source":
            if r["writers"] or not r.get("path"):
                raise ConfigurationError("Sources are immutable inputs with a workspace-relative path and no writers.")
            p = project_file(root, r["path"])
            if any(part in {".git", ".venv", "runs", "trials", "setup", "results", "local-reference"} for part in Path(r["path"]).parts) or p.name.startswith(".env") or p.name == "private_splits.json":
                raise ConfigurationError("Private runtime/credential paths cannot be declared as source representations.")
            if p.stat().st_size > 100_000:
                raise ConfigurationError("Source representation exceeds the 100 KB text-input bound.")
            text = p.read_text(encoding="utf-8")
            source_bindings[r["id"]] = {"path": r["path"], "sha256": hashlib.sha256(text.encode()).hexdigest()}
        elif "path" in r or not r["writers"]:
            raise ConfigurationError("Workspace representations are append-only run records with writers, not arbitrary filesystem paths.")
        if r["kind"] == "workspace" and len(set(r["readers"]) | set(r["writers"])) > 1 and base["communication"]["detail"] != "high":
            raise ConfigurationError("Shared writable representations require teamknitt high-detail sharing; a cognition overlay cannot widen the lab's communication policy.")
    for w in work.values():
        if w["phase"] not in phases or not set(w["actors"]) <= phase_actors[w["phase"]]:
            raise ConfigurationError("Work must bind explicitly to an existing teamknitt phase and its participating actors.")
        if not set(w["inputs"] + w["outputs"]) <= reps.keys() or not set(w["depends_on"]) <= work.keys():
            raise ConfigurationError("Work references unknown representations or predecessors.")
        for actor in w["actors"]:
            if any(actor not in reps[ref]["readers"] for ref in w["inputs"]) or any(actor not in reps[ref]["writers"] for ref in w["outputs"]):
                raise ConfigurationError("Work bindings must respect representation read/write permissions.")
    work_graph = [{"id": w["id"], "depends_on": w["depends_on"]} for w in work.values()]
    waves(work_graph)
    base_waves = waves(base["work_graph"])
    phase_wave = {n["id"].split(":")[1]: i for i, wave in enumerate(base_waves, 1) for n in wave if ":" in n["id"]}
    for w in work.values():
        if any(phase_wave[work[p]["phase"]] >= phase_wave[w["phase"]] for p in w["depends_on"]):
            raise ConfigurationError("Work prerequisites must precede the consuming phase in the selected teamknitt graph.")
    for h in handoffs.values():
        if h["producer"] not in actors or h["consumer"] not in actors or h["producer"] == h["consumer"] or h["representation"] not in reps:
            raise ConfigurationError("Handoffs need distinct declared actors and a representation.")
        if (h["producer"], h["consumer"]) not in routes:
            raise ConfigurationError("A handoff cannot bypass the selected communication topology.")
        r = reps[h["representation"]]
        if h["producer"] not in r["writers"] or h["consumer"] not in r["readers"]:
            raise ConfigurationError("Handoff roles must have the declared representation permissions.")
        if h["due_phase"] not in phases or h["consumer"] not in phase_actors[h["due_phase"]]:
            raise ConfigurationError("A handoff deadline must be a phase in which its consumer participates.")
    for entry in c["cognition"]["expertise_directory"]:
        if not set(entry["holders"]) <= actors:
            raise ConfigurationError("Expertise directory must name configured actors, not inferred experts.")
    for a in c["cognition"]["affordances"]:
        if not set(a["actors"]) <= actors or not set(a["requires"]) <= reps.keys():
            raise ConfigurationError("Affordance has unknown actors or informational requirements.")
        if a["operation"] == "publish" and a["target"] not in reps or a["operation"] == "acknowledge" and a["target"] not in handoffs:
            raise ConfigurationError("Affordance target must name the relevant representation or handoff.")
        for actor in a["actors"]:
            if a["capability"] not in roles[actor]["capabilities"]:
                raise ConfigurationError("Available action opportunities must match explicitly configured actor capabilities.")
            if a["operation"] == "publish" and actor not in reps[a["target"]]["writers"]:
                raise ConfigurationError("A publication affordance cannot grant undeclared write access.")
            if a["operation"] == "acknowledge" and actor != handoffs[a["target"]]["consumer"]:
                raise ConfigurationError("An acknowledgement affordance belongs to the declared handoff consumer.")
    horizon = len(base_waves)
    if c["cognition"]["temporal_reference"]["deadline_wave"] > horizon or c["dynamics"]["stable_waves"] > horizon:
        raise ConfigurationError("Temporal reference and stability span must fit the actual teamknitt wave horizon.")
    for p in c["dynamics"]["perturbations"]:
        if p["at_wave"] + p["duration"] - 1 > horizon:
            raise ConfigurationError("A perturbation must end within the resolved teamknitt workflow.")
        if p["kind"] == "representation_unavailable" and (p.get("representation") not in reps or set(p) != {"id", "kind", "at_wave", "duration", "representation"}):
            raise ConfigurationError("Representation interruption needs exactly one declared representation.")
        if p["kind"] == "actor_unavailable" and (p.get("actor") not in actors or set(p) != {"id", "kind", "at_wave", "duration", "actor"}):
            raise ConfigurationError("Actor interruption needs exactly one declared actor.")
        if p["kind"] == "link_dropout" and (p.get("source") not in actors or p.get("target") not in actors or p["source"] == p["target"] or set(p) != {"id", "kind", "at_wave", "duration", "source", "target"}):
            raise ConfigurationError("Link interruption needs one directed pair of distinct actors.")
        if p["kind"] == "link_dropout" and (p["source"], p["target"]) not in routes:
            raise ConfigurationError("A link interruption must refer to a configured topology link.")
    mission_binding = {"path": study["problem_file"], "sha256": hashlib.sha256(project_file(root, study["problem_file"]).read_bytes()).hexdigest()}
    bound = {"engine_sha256": base["configuration_snapshot"]["sha256"], "cognition": c, "sources": source_bindings, "mission": mission_binding}
    combined = digest(bound)
    compiled = deepcopy(base)
    compiled["configuration_snapshot"].update(id="team-" + combined[:20], sha256=combined,
                                               engine_sha256=bound["engine_sha256"], cognition_binding=bound)
    compiled["cognition"] = c["cognition"]
    compiled["teamknitt_dynamics"] = c["dynamics"]
    main_episodes = sum(len(n["actors"]) for n in base["work_graph"]
                        if n["kind"] not in {"qualification", "verification"} and n["research_activity"] != "operational_only")
    return {"schema_version": c["schema_version"], "name": c["name"], "status": "team_task_plan" if c["schema_version"] == 3 else "distributed_problem_solving_plan",
            "configuration_sha256": combined, "engine_variant": selected,
            "engine_configuration_sha256": bound["engine_sha256"], "configuration": c,
            "engine_plan": compiled, "source_bindings": source_bindings, "mission_binding": mission_binding,
            "engine_configuration": study,
            "topology": {"kind": c["team"]["topology"] if c["schema_version"] == 3 else "fully_connected",
                "members": sorted(actors), "links": [{"source": a, "target": b} for a, b in sorted(routes)],
                "description": TOPOLOGIES[c["team"]["topology"]] if c["schema_version"] == 3 else "Explicit advanced research configuration; full peer routes within the selected engine sharing ceiling."},
            "observations": c.get("observations", {"enabled": True, "dimensions": ["local_global", "perturbation", "coupling"]}),
            "waves": [{"wave": i, "nodes": [n["id"] for n in wave], "actors": sorted({a for n in wave for a in n["actors"] if a in actors})}
                      for i, wave in enumerate(base_waves, 1)],
            "budget_authority": "User-selected engine settings in study.yaml; teamknitt does not change budgets",
            "provider_request_cap": base["budget"]["max_llm_calls"],
            "reference_request_case": {"one_final_per_main_episode": main_episodes,
                "cap_covers_that_case": main_episodes <= base["budget"]["max_llm_calls"],
                "note": "A reference case, not a promise or currency estimate. Tools, decisions, correction and delegation can consume additional requests within the same unchanged cap."}, "api_calls": 0, "research_started": False,
            "automatic_team_redesign": False, "scientific_quality_score": None}
