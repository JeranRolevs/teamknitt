"""Frozen-round team execution with evidence scopes, explicit interventions and budgets.

Labtune's provider transport is reused from this distribution, not a remote/parent runtime.
The symbolic world never executes model-authored code or changes team organization.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
from importlib.resources import files
import os
import platform
from pathlib import Path
import time
from uuid import uuid4

from labtune.config import ConfigurationError
from labtune.providers.chat import ChatCompletionsClient
from labtune.providers.configuration import require_configured
from labtune.providers.http import ProviderError
from labtune.study import api_key

from teamknitt import __version__
from .actions import InvalidAction, SYSTEM, parse_action
from .config import digest, links, plan, validate
from .policies import fixture, scripted
from .scenarios import suite


class BudgetReached(RuntimeError):
    pass


def implementation_identity():
    names = ("actions.py", "config.py", "metrics.py", "policies.py", "reporting.py", "runtime.py", "scenarios.py")
    return digest({name: hashlib.sha256(files("teamknitt.probes").joinpath(name).read_bytes()).hexdigest() for name in names})


def now():
    return datetime.now(timezone.utc).isoformat()


def save_private(path, value):
    """Atomic private records; never overwrite a symlink or a non-file target."""
    if path.is_symlink() or path.exists() and not path.is_file():
        raise ConfigurationError("Record target must be a regular local file.")
    tmp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
    os.replace(tmp, path)


class Budget:
    def __init__(self, config):
        self.settings = config["budget"]
        self.started = time.monotonic()
        self.requests = 0
        self.receipts = []
        self.model_bindings_returned = set()

    @property
    def remaining(self):
        return self.settings["max_wall_seconds"] - (time.monotonic() - self.started)

    def check(self):
        if self.remaining <= 0 or self.requests >= self.settings["max_requests"]:
            raise BudgetReached("Shared request or wall-time budget reached; no automatic increase.")

    def reserve(self):
        self.check()
        self.requests += 1

    def summary(self):
        valid = [r for r in self.receipts if isinstance(r, dict)
                 and all(type(r.get(k)) is int and r[k] >= 0 for k in ("prompt_tokens", "completion_tokens"))]
        return {"provider_requests": self.requests, "elapsed_seconds": time.monotonic() - self.started,
                "input_tokens": sum(r["prompt_tokens"] for r in valid),
                "output_tokens": sum(r["completion_tokens"] for r in valid),
                "missing_usage_receipts": self.requests - len(valid),
                "returned_model_bindings": [{"provider": p, "requested_model": r, "returned_model": m}
                                            for p, r, m in sorted(self.model_bindings_returned)],
                "monetary_cost": None, "monetary_cost_note": "No price table configured; request bounds are not a currency cap."}


def active_perturbations(config, condition, round_):
    return [p for p in config["perturbations"] if condition == "test"
            and p["at_round"] <= round_ < p["at_round"] + p["duration"]]


def _frame(config, scenario, condition, actor, round_, known, inbox, state, last_action, active):
    frame = {
        "actor": actor["id"], "role": actor["role"], "subject": config["team"]["subject"],
        "accountable": config["team"]["accountable"], "condition": condition,
        "task_id": scenario.id, "mission": scenario.brief(), "round": round_,
        "round_horizon": config["protocol"]["rounds"],
        "roster": [actor["id"]] if condition == "alone" else [m["id"] for m in config["team"]["members"]],
        "known_facts": [deepcopy(scenario.facts[ref]) for ref in sorted(known)],
        "inbox": deepcopy(inbox), "last_action": last_action,
        "shared_artifact": {"ledger_value": state["ledger"]},
        "active_interventions": [p["id"] for p in active], "omitted_older_messages": 0,
        "max_messages": config["communication"]["max_messages_per_turn"],
    }
    maximum = config["budget"]["max_context_chars"]
    while len(SYSTEM) + len(json.dumps(frame)) > maximum and frame["inbox"]:
        frame["inbox"].pop(0)
        frame["omitted_older_messages"] += 1
    if len(SYSTEM) + len(json.dumps(frame)) > maximum:
        raise InvalidAction("Context bound cannot fit mandatory observations; increase it explicitly between runs.")
    return frame


async def episode(config, scenario, condition, seed, *, budget, live, policy, clients, emit):
    subject = config["team"]["subject"]
    actors = [m for m in config["team"]["members"] if condition != "alone" or m["id"] == subject]
    ids = {m["id"] for m in actors}
    known = scenario.initial_knowledge(config, condition)
    inbox = {key: [] for key in ids}
    last_action = {key: None for key in ids}
    state = scenario.initial_state(condition)
    allowed = set(links(config))
    events, snapshots = [], []
    episode_id = f"{scenario.id}.{condition}.{seed}"
    row = {"id": episode_id, "task_id": scenario.id, "dimension": scenario.dimension,
           "condition": condition, "seed": seed, "status": "completed", "rounds": snapshots, "events": events}

    def event(kind, round_, **fields):
        item = {"episode_id": episode_id, "kind": kind, "round": round_, **fields}
        events.append(item)
        emit(item)

    try:
        for round_ in range(1, config["protocol"]["rounds"] + 1):
            if budget.remaining <= 0:
                raise BudgetReached("Shared wall-time budget reached.")
            active = active_perturbations(config, condition, round_)
            absent = {p["member"] for p in active if p["kind"] == "member_unavailable"}
            outages = {(p["source"], p["target"]) for p in active if p["kind"] == "link_dropout"}
            for p in active:
                if p["at_round"] == round_:
                    event("perturbation", round_, intervention=deepcopy(p))
                    if p["kind"] == "task_pressure":
                        known[config["team"]["scripted"]].add("incident")
                        if scenario.dimension in {"taking_over", "misconduct"}:
                            state["ledger"] = scenario.total - 3
                            # Tampering creates work even if an earlier record had been verified.
                            state["verified_by"] = []
                            state["repaired_by"] = []
            frames = {}
            for actor in actors:
                if actor["id"] not in absent:
                    frames[actor["id"]] = _frame(config, scenario, condition, actor, round_, known[actor["id"]],
                                                  inbox[actor["id"]], state, last_action[actor["id"]], active)
            # All actor observations are frozen BEFORE any action in this wave becomes visible.
            async def act(actor):
                actor_id = actor["id"]
                frame = frames[actor_id]
                if actor["kind"] == "scripted":
                    value = scripted(frame, scenario, config)
                elif not live:
                    value = fixture(frame, scenario, config, policy)
                else:
                    budget.check()
                    client = clients[(actor["provider"], seed)]
                    try:
                        reply = await asyncio.wait_for(client.generate([
                            {"role": "system", "content": SYSTEM},
                            {"role": "user", "content": json.dumps(frame, allow_nan=False)}],
                            budget_ref="team-" + digest(config)[:20]), timeout=max(0.001, budget.remaining))
                    except asyncio.TimeoutError:
                        raise BudgetReached("Wall-time boundary; in-flight provider billing may be uncertain.") from None
                    value = reply["content"]
                parsed = parse_action(value, known=known[actor_id], recipients=ids - {actor_id},
                                      limit=config["communication"]["max_messages_per_turn"])
                return actor_id, parsed

            available = [a for a in actors if a["id"] in frames]
            # return_exceptions ensures all already-reserved sibling requests finish/account before proceeding.
            replies = await asyncio.gather(*(act(a) for a in available), return_exceptions=True)
            errors = [reply for reply in replies if isinstance(reply, BaseException)]
            if errors:
                for actor, reply in zip(available, replies):
                    if isinstance(reply, BaseException):
                        event("actor_error", round_, actor=actor["id"],
                              error_kind=getattr(reply, "kind", type(reply).__name__))
                raise errors[0]
            pending = []
            for actor_id, action in replies:
                last_action[actor_id] = deepcopy(action)
                event("actor_action", round_, actor=actor_id, message_count=len(action["messages"]),
                      work_count=len(action["work"]), decision_choice=(action["decision"] or {}).get("choice"),
                      context_messages_omitted=frames[actor_id]["omitted_older_messages"])
                for message in action["messages"]:
                    target = message["to"]
                    reason = ("topology" if (actor_id, target) not in allowed else
                              "member_unavailable" if target in absent else
                              "link_dropout" if (actor_id, target) in outages else None)
                    item = {"source": actor_id, "target": target, "act": message["act"],
                            "evidence": message["evidence"], "content": message["content"],
                            "incident_seen": "incident" in known[actor_id] and "incident" in message["evidence"],
                            "delivered": reason is None, "drop_reason": reason}
                    event("message", round_, **item)
                    if reason is None:
                        pending.append(item)
                for work in action["work"]:
                    correct = work["value"] == scenario.total
                    if work["operation"] == "repair":
                        state["ledger"] = work["value"]
                        if correct and actor_id not in state["repaired_by"]:
                            state["repaired_by"].append(actor_id)
                    elif correct and actor_id not in state["verified_by"]:
                        state["verified_by"].append(actor_id)
                    event("work", round_, actor=actor_id, operation=work["operation"], correct=correct)
                if actor_id == subject and action["decision"] is not None:
                    previous = state["decision"]
                    state["decision"] = deepcopy(action["decision"])
                    state["decision_round"] = round_
                    if action["decision"]["choice"] == "shortcut":
                        state["unsafe_committed"] = True
                    event("decision", round_, actor=actor_id, choice=action["decision"]["choice"],
                          changed=previous != action["decision"])
            # Delivery happens once per round. No same-wave or reverse-link leakage.
            for item in pending:
                recipient = item["target"]
                known[recipient].update(item["evidence"])
                inbox[recipient].append(deepcopy(item))
                state["delivered_acts"].append({key: value for key, value in item.items() if key != "content"})
            assessment = scenario.assess(state, config, condition)
            core_checks = ("decision_present", "correct_total", "evidence_complete", "safe_choice", "ledger_correct")
            snapshot = {"round": round_, "goal_ready": all(assessment["checks"][key] for key in core_checks),
                        "protocol_pass": assessment["passed"], "score": assessment["score"],
                        "active_interventions": [p["id"] for p in active],
                        "known_fact_counts": {actor: len(refs) for actor, refs in known.items()},
                        "decision_choice": (state["decision"] or {}).get("choice")}
            snapshots.append(snapshot)
            event("round_end", round_, **{key: value for key, value in snapshot.items() if key != "round"})
        row["outcome"] = scenario.assess(state, config, condition)
    except (BudgetReached, ProviderError, InvalidAction) as error:
        row["status"] = ("budget_exhausted" if isinstance(error, BudgetReached) else
                         "invalid_action" if isinstance(error, InvalidAction) else "provider_error")
        row["error_kind"] = getattr(error, "kind", type(error).__name__)
        # Error messages/raw provider responses are not exported to the observatory.
        row["outcome"] = None
    row["rounds_completed"] = len(snapshots)
    return row


async def run(workspace: Path, config, *, live=False, approve_requests=None, policy="coordinated", transport=None):
    """One study. A live request needs two explicit gates; no automatic retry/fallback."""
    config = validate(config)
    if policy not in {"coordinated", "fragile"}:
        raise ConfigurationError("Choose coordinated or fragile for the offline fixture.")
    compiled = plan(config)
    if live and (type(approve_requests) is not int or approve_requests != config["budget"]["max_requests"]):
        raise ConfigurationError("Live execution needs --approve-requests equal to the configured shared request cap.")
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise ConfigurationError("Choose an existing workspace; initialize it before running.")
    for provider in config["providers"].values():
        if not (workspace / provider["env_file"]).resolve().is_relative_to(workspace):
            raise ConfigurationError("Private env files must stay inside the workspace.")
    keys = {}
    if live:
        for name, provider in config["providers"].items():
            require_configured(provider)
            keys[name] = api_key(workspace, provider)
    runs = workspace / "runs"
    if runs.is_symlink() or runs.exists() and not runs.is_dir():
        raise ConfigurationError("runs must be a local directory, not a symlink.")
    runs.mkdir(mode=0o700, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:10]
    destination = runs / run_id
    destination.mkdir(mode=0o700)
    budget = Budget(config)
    result = {"schema_version": 1, "teamknitt_version": __version__, "run_id": run_id,
              "started_at": now(), "implementation_sha256": implementation_identity(),
              "python_version": platform.python_version(), "mode": "live" if live else "offline_fixture",
              "fixture_policy": None if live else policy, "configuration_sha256": digest(config),
              "plan": compiled, "episodes": [], "status": "running"}
    save_private(destination / "configuration.json", config)
    save_private(destination / "run.json", result)
    fd = os.open(destination / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as journal:
        def emit(event):
            journal.write(json.dumps({"timestamp": now(), **event}, allow_nan=False) + "\n")
            journal.flush()
        def provider_event(event):
            if event.get("kind") == "provider_response":
                budget.receipts.append(event.get("response", {}).get("usage"))
                returned = event.get("response", {}).get("model")
                if isinstance(returned, str):
                    budget.model_bindings_returned.add((str(event.get("provider", "")), str(event.get("model", "")), returned))
            # Deliberately do not persist raw prompts, provider responses or credentials.
            emit({key: event[key] for key in ("kind", "request_id", "provider", "model", "elapsed_seconds", "error_kind") if key in event})
        clients = {}
        if live:
            semaphore = asyncio.Semaphore(config["budget"]["max_parallel"])
            for name, p in config["providers"].items():
                for seed in config["protocol"]["seeds"]:
                    clients[(name, seed)] = ChatCompletionsClient(
                        keys[name], model=p["model"], base_url=p["base_url"], endpoint=p["endpoint"],
                        provider_id=name, timeout=min(p["timeout_seconds"], config["budget"]["max_wall_seconds"]),
                        max_tokens=p["max_output_tokens"], max_output_field=p["max_output_field"],
                        request_options={**p["request_options"], "seed": seed}, max_parallel=p["max_parallel_requests"],
                        shared_semaphore=semaphore, reserve=budget.reserve, on_event=provider_event, transport=transport)
        try:
            for scenario in suite(config):
                jobs = [("alone", config["protocol"]["seeds"][0]),
                        ("baseline", config["protocol"]["seeds"][0]),
                        *(("test", seed) for seed in config["protocol"]["seeds"])]
                for condition, seed in jobs:
                    row = await episode(config, scenario, condition, seed, budget=budget, live=live,
                                        policy=policy, clients=clients, emit=emit)
                    result["episodes"].append(row)
                    result["usage"] = budget.summary()
                    save_private(destination / "run.json", result)
            result["status"] = "completed" if all(e["status"] == "completed" for e in result["episodes"]) else "incomplete"
        except BaseException:
            result["status"] = "interrupted"
            raise
        finally:
            result["finished_at"] = now()
            result["usage"] = budget.summary()
            save_private(destination / "run.json", result)
    from .reporting import report
    summary = report(result)
    save_private(destination / "report.json", summary)
    return {"status": result["status"], "mode": result["mode"], "run_id": run_id,
            "run_directory": str(destination), "report": str(destination / "report.json"),
            "provider_requests": budget.requests, "overall_score": summary["scores"]["overall_score"],
            "evidence_label": summary["evidence_label"]}
