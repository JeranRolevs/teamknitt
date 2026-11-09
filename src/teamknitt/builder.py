"""A mechanical starter builder driven by explicit user choices, never performance."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from teamknitt.engine.config import ConfigurationError
from .topology import links, members

PURPOSES = {
    "task": "Produce the user-requested deliverable, noting dependencies and unresolved items.",
    "brainstorm": "Generate distinct ideas, connect promising alternatives and preserve useful disagreement before converging.",
    "goal": "Explore routes toward the user's goal and propose bounded next steps and review criteria.",
    "research": "Develop an evidence-grounded research proposal; empirical claims require independent evaluation.",
}
PHASES = ["independent_proposals", "task_adoption", "parallel_episodes", "evidence_review"]


def make_configuration(*, topology="fully_connected", count=3, communication="high", purpose="brainstorm",
                       max_read_words=700, custom_links=None, name="A team for your next idea", brief_file="mission/task.md"):
    ids = members(count)
    if communication not in {"none", "low", "intermediate", "high", "wisdom_only"} or purpose not in PURPOSES:
        raise ConfigurationError("Choose a supported communication profile and user-task purpose.")
    team = {"topology": topology, "members": count, "links": custom_links or []}
    routes = links(team)
    shared = communication == "high"
    roles, reps, work, handoffs, opportunities, directory = [], [], [], [], [], []
    reps.append({"id": "context", "kind": "source", "purpose": "User-supplied context for this task or goal.",
                 "format": "markdown", "path": "mission/context.md", "readers": ids, "writers": []})
    emphases = [
        ("Connect and synthesize", "Connect contributions and make assumptions explicit; do not force agreement."),
        ("Explore alternatives", "Seek diverse approaches and possibilities rather than merely echoing the first idea."),
        ("Challenge and make practical", "Explore constraints, counterexamples and workable next steps without prematurely closing ideas."),
    ]
    for i, actor in enumerate(ids):
        title, perspective = emphases[i % len(emphases)]
        note = f"notes-{i + 1}"
        roles.append({"actor": actor, "responsibilities": [title, PURPOSES[purpose]],
            "expertise": [], "perspective": perspective, "capabilities": ["contribute", "acknowledge"]})
        reps.append({"id": note, "kind": "workspace", "purpose": f"Externalized contribution from {actor} for the user's {purpose}.",
            "format": "structured_note", "readers": ids if shared else [actor], "writers": [actor]})
        work.append({"id": f"frame-{i+1}", "phase": PHASES[0], "actors": [actor], "goal": PURPOSES[purpose],
                     "inputs": ["context"], "outputs": [note], "depends_on": []})
        opportunities.append({"id": f"contribute-{i+1}", "actors": [actor], "capability": "contribute",
            "requires": ["context"], "operation": "publish", "target": note, "purpose": "Externalize a task contribution with input provenance."})
        directory.append({"topic": title, "holders": [actor], "basis": "User-editable role emphasis, not verified expertise or a model ranking."})
    if shared:
        for source, target in routes:
            ref = "notes-" + source.split(".")[-1]
            suffix = source.replace(".", "-") + "-to-" + target.replace(".", "-")
            h = "handoff-" + suffix
            handoffs.append({"id": h, "representation": ref, "producer": source, "consumer": target,
                             "due_phase": PHASES[2], "ack_required": True})
            opportunities.append({"id": "ack-" + suffix, "actors": [target], "capability": "acknowledge",
                "requires": [ref], "operation": "acknowledge", "target": h,
                "purpose": "Acknowledge the specific contribution encountered, without implying agreement."})
    return {"schema_version": 3, "name": name,
        "engine": {"variant": "team", "design_file": "designs/task-team.md"},
        "mission": {"purpose": purpose, "brief_file": brief_file,
            "deliverable": "A reviewable response to the user's task, ideas or goal, with open questions and next steps.",
            "success_criteria": ["Address the user's brief rather than a benchmark task.", "Keep sources, alternatives and unresolved items inspectable."],
            "review": "user_review"},
        "team": team,
        "communication": {"profile": communication, "wisdom": communication == "wisdom_only", "max_read_words": max_read_words},
        "cognition": {"perspectives": ["distributed_problem_solving", "information_processing", "transactive_memory", "shared_mental_models", "coaction", "interactive_dynamics"],
            "context": {"setting": "A user-directed team working on a task, brainstorming ideas or pursuing a chosen goal.",
                "tools": ["versioned_notes", "scoped_information_sharing", "explicit_handoffs"],
                "constraints": ["A role emphasis is not proof of expertise.", "A contribution or acknowledgement is not proof that the user's goal has been achieved."]},
            "task": {"structure": "divisible", "interaction": "independent" if communication == "none" else "deliberative" if shared else "limited_exchange",
                "goal": PURPOSES[purpose], "success_criteria": ["Retain traceable contributions and unresolved items for user review."]},
            "roles": roles, "representations": reps, "work": work, "handoffs": handoffs,
            "expertise_directory": directory, "temporal_reference": {"order": PHASES[:], "deadline_wave": 5},
            "affordances": opportunities, "memory": {"max_words_per_representation": 160}},
        "dynamics": {"stable_waves": 2, "perturbations": []},
        "observations": {"enabled": True, "dimensions": ["local_global", "perturbation", "coupling", "cross_level", "attractors", "synchronization", "fractals"]}}


def draft_configuration(current, **choices):
    if current.get("schema_version") != 3:
        raise ConfigurationError("The simple team builder uses schema 3. Keep the advanced research template separate or initialize a new task workspace.")
    c = make_configuration(topology=choices.get("topology") or current["team"]["topology"],
        count=choices.get("count") if choices.get("count") is not None else current["team"]["members"],
        communication=choices.get("communication") or current["communication"]["profile"],
        purpose=choices.get("purpose") or current["mission"]["purpose"],
        max_read_words=choices.get("max_read_words") if choices.get("max_read_words") is not None else current["communication"]["max_read_words"],
        custom_links=choices.get("custom_links") if choices.get("custom_links") is not None else current["team"]["links"] if (choices.get("topology") or current["team"]["topology"]) == "custom" else [],
        name=current["name"], brief_file=current["mission"]["brief_file"])
    c["engine"] = deepcopy(current["engine"])
    if c["communication"]["profile"] == current["communication"]["profile"]:
        c["communication"]["wisdom"] = current["communication"]["wisdom"]
    c["mission"] = {**deepcopy(current["mission"]), "purpose": c["mission"]["purpose"]}
    c["dynamics"] = deepcopy(current["dynamics"])
    c["observations"] = deepcopy(current["observations"])
    return c


def apply_configuration(workspace: Path, config, *, reset_cognition=False):
    """Explicit application only. Keep the previous config privately; never alter task text or engine budgets."""
    if not reset_cognition:
        raise ConfigurationError("Applying the builder requires --reset-bindings: it regenerates role/representation/work bindings. Your previous team.yaml is backed up; task text and engine settings are not changed.")
    from .config import compile_plan
    compiled = compile_plan(workspace, config)
    path = workspace / "team.yaml"
    if path.is_symlink():
        raise ConfigurationError("team.yaml cannot be a symlink for builder application.")
    import fcntl
    lock_path = workspace / ".run.lock"
    if lock_path.is_symlink():
        raise ConfigurationError("The engine run lock cannot be a symlink.")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(lock_fd, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ConfigurationError("A run owns this workspace. Drafting is allowed, but applying must wait until the run ends.") from None
        backup_root = workspace / "setup/teamknitt-config-backups"
        if (workspace / "setup").is_symlink() or backup_root.is_symlink():
            raise ConfigurationError("Configuration backups must remain inside the workspace.")
        backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = backup_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8] + ".json")
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(path.read_text())
        temporary = path.with_name(".team-" + uuid4().hex + ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(config, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
        return {"status": "team_configuration_applied", "backup": str(backup), "configuration_sha256": compiled["configuration_sha256"],
                "api_calls": 0, "engine_settings_changed": False, "task_text_changed": False}
