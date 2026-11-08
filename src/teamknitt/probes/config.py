"""Explicit team experiments. Loading and planning never connect to a provider."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from labtune.config import ConfigurationError, parse_yaml, project_file
from labtune.providers.configuration import generation_settings
from labtune.providers.http import ProviderError

DIMENSIONS = {
    "unsafe_pressure": "Resisting unsafe pressure",
    "misconduct": "Reporting misconduct",
    "information": "Sharing and seeking information",
    "emotional_support": "Emotional intelligence (structured proxy)",
    "goal_alignment": "Keeping the team on track",
    "conflict": "Handling conflict",
    "initiative": "Taking initiative",
    "taking_over": "Taking over",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def resource(name):
    return files("teamknitt.resources").joinpath({"team.yaml": "probe.yaml", "WORKSPACE.md": "PROBES_WORKSPACE.md", "observatory.html": "probes-observatory.html"}.get(name, name))


def validate(config):
    schema = json.loads(resource("probes.schema.json").read_text())
    try:
        json.dumps(config, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ConfigurationError("Team settings must contain finite JSON data.") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(config),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        e = errors[0]
        raise ConfigurationError(f"{'.'.join(map(str, e.absolute_path)) or 'team'}: {e.message}")
    c = deepcopy(config)
    roster = {row["id"]: row for row in c["team"]["members"]}
    if len(roster) != len(c["team"]["members"]):
        raise ConfigurationError("Team member IDs must be unique.")
    team = c["team"]
    for field in ("subject", "scripted", "accountable"):
        if team[field] not in roster:
            raise ConfigurationError(f"team.{field} must name a roster member.")
    if len({team[x] for x in ("subject", "scripted", "accountable")}) != 3:
        raise ConfigurationError("Subject, scripted teammate and accountable partner must be distinct.")
    if roster[team["subject"]]["kind"] != "model" or roster[team["accountable"]]["kind"] != "model":
        raise ConfigurationError("The subject and accountable partner must be model members.")
    if [m["id"] for m in roster.values() if m["kind"] == "scripted"] != [team["scripted"]]:
        raise ConfigurationError("Declare exactly one controlled scripted teammate.")
    try:
        c["providers"] = {key: generation_settings(value) for key, value in c["providers"].items()}
    except ProviderError as error:
        raise ConfigurationError(str(error)) from None
    used = set()
    for member in roster.values():
        if member["kind"] == "model":
            if member.get("provider") not in c["providers"]:
                raise ConfigurationError("Every model member must explicitly name a declared provider.")
            used.add(member["provider"])
        elif "provider" in member:
            raise ConfigurationError("Scripted teammates do not have a provider.")
    if used != set(c["providers"]):
        raise ConfigurationError("Remove unused provider declarations; there is no automatic model selection.")
    for key, p in c["providers"].items():
        # The protocol owns the experimental seeds, not a hidden provider override.
        if "seed" in p["request_options"]:
            raise ConfigurationError(f"providers.{key}: use protocol.seeds, not request_options.seed.")
    links = c["communication"]["links"]
    if c["communication"]["topology"] == "explicit" and not links:
        raise ConfigurationError("Explicit topology needs directed links.")
    if c["communication"]["topology"] == "full" and links:
        raise ConfigurationError("Full topology must not also declare explicit links.")
    seen = set()
    for link in links:
        pair = (link["source"], link["target"])
        if pair[0] not in roster or pair[1] not in roster or pair[0] == pair[1] or pair in seen:
            raise ConfigurationError("Links must be unique, directed pairs of distinct roster IDs.")
        seen.add(pair)
    rounds = c["protocol"]["rounds"]
    interventions = c["perturbations"]
    if sum(p["kind"] == "task_pressure" for p in interventions) != 1:
        raise ConfigurationError("Declare exactly one task_pressure intervention for the challenged condition.")
    if len({p["id"] for p in interventions}) != len(interventions):
        raise ConfigurationError("Perturbation IDs must be unique.")
    for p in interventions:
        if p["at_round"] + p["duration"] - 1 > rounds:
            raise ConfigurationError("Perturbations must end inside the declared round horizon.")
        if p["kind"] == "link_dropout":
            if set(p) != {"id", "kind", "at_round", "duration", "source", "target"}:
                raise ConfigurationError("A link_dropout needs only source and target in addition to its schedule.")
            if p["source"] not in roster or p["target"] not in roster or p["source"] == p["target"]:
                raise ConfigurationError("Link dropouts need distinct roster IDs.")
            if c["communication"]["topology"] == "explicit" and (p["source"], p["target"]) not in seen:
                raise ConfigurationError("A dropout must refer to a configured link.")
        elif p["kind"] == "member_unavailable":
            if set(p) != {"id", "kind", "at_round", "duration", "member"} or p["member"] not in roster:
                raise ConfigurationError("member_unavailable needs exactly one valid member ID.")
        elif set(p) != {"id", "kind", "at_round", "duration"}:
            raise ConfigurationError("task_pressure has only an ID, kind and schedule.")
    if c["dynamics"]["stable_rounds"] > rounds:
        raise ConfigurationError("The stability window must fit inside the round horizon.")
    return c


def load(workspace: Path):
    root = workspace.resolve()
    c = validate(parse_yaml(project_file(root, "team.yaml").read_text(encoding="utf-8")))
    for p in c["providers"].values():
        if not (root / p["env_file"]).resolve().is_relative_to(root):
            raise ConfigurationError("Private env files must stay inside the workspace.")
    return c


def links(config):
    if config["communication"]["topology"] == "explicit":
        return [(link["source"], link["target"]) for link in config["communication"]["links"]]
    ids = [member["id"] for member in config["team"]["members"]]
    return [(a, b) for a in ids for b in ids if a != b]


def plan(config):
    c = validate(config)
    protocol = c["protocol"]
    task_count = len(protocol["dimensions"]) * protocol["instances_per_dimension"]
    models = sum(m["kind"] == "model" for m in c["team"]["members"])
    upper = task_count * protocol["rounds"] * (1 + models * (1 + len(protocol["seeds"])))
    subject = next(m for m in c["team"]["members"] if m["id"] == c["team"]["subject"])
    return {
        "schema_version": 1, "name": c["name"], "configuration_sha256": digest(c),
        "team": c["team"], "directed_links": links(c), "protocol": protocol,
        "perturbations": c["perturbations"], "dynamics": c["dynamics"],
        "statistics": c["statistics"], "budget": c["budget"],
        "task_count": task_count, "episode_count": task_count * (2 + len(protocol["seeds"])),
        "provider_request_upper_bound": upper,
        "budget_covers_request_upper_bound": upper <= c["budget"]["max_requests"],
        "provider_bindings": {m["id"]: m.get("provider", "scripted") for m in c["team"]["members"]},
        "configuration": c, "api_calls": 0, "research_started": False,
        "output_token_upper_bound": task_count * protocol["rounds"] * (
            c["providers"][subject["provider"]]["max_output_tokens"]
            + (1 + len(protocol["seeds"])) * sum(c["providers"][m["provider"]]["max_output_tokens"] for m in c["team"]["members"] if m["kind"] == "model")),
        "scope": "Original synthetic protocol probes, not the Collaborative Intelligence Benchmark.",
        "automatic_team_redesign": False,
    }
