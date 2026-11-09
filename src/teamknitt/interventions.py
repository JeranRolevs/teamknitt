"""Explicit operator requests, private audit receipts and safe wave-boundary control.

No provider calls, configuration writes or budget changes occur when a request is queued.
Already-approved current-wave work is not cancelled. Feedback remains private task context,
not permission to alter models, tools, source grants or engine limits.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from .engine.config import ConfigurationError, project_file
from .engine.study import ControlledStop
from .compat import original_engine_plan
from .config import digest

ACTIONS = ("pause", "resume", "stop", "feedback")
MAX_REQUESTS = 256
MAX_PENDING = 64
BOUNDARY = "Before the next dependency wave; already-approved current-wave work may finish."


def now():
    return datetime.now(timezone.utc).isoformat()


def _read(path, limit=100_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ConfigurationError("Operator records must be bounded regular files, not symlinks.")
    value = json.loads(path.read_text(encoding="utf-8"))
    json.dumps(value, allow_nan=False)
    return value


def _write(path, value):
    if path.is_symlink():
        raise ConfigurationError("An operator record cannot be a symlink.")
    temporary = path.with_name(".operator-" + uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
    os.replace(temporary, path)


@contextmanager
def _lock(folder):
    import fcntl
    if folder.is_symlink() or not folder.is_dir() or (folder / "requests").is_symlink():
        raise ConfigurationError("Operator storage must remain inside the selected run.")
    fd = os.open(folder / ".queue.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _context(root):
    identity = _read(root / "team-run.json")
    plan = _read(root / "team-plan.json", 10_000_000)
    binding = original_engine_plan(plan)["configuration_snapshot"]["cognition_binding"]
    if digest(binding) != identity["configuration_sha256"] or binding["cognition"] != plan["configuration"] or plan["configuration_sha256"] != identity["configuration_sha256"]:
        raise ConfigurationError("Operator target has an invalid saved configuration binding.")
    state = _read(root / "operator/state.json", 5_000_000)
    if state["run_id"] != identity["run_id"] or state["configuration_sha256"] != identity["configuration_sha256"]:
        raise ConfigurationError("Operator state belongs to a different run/configuration.")
    actors = [r["actor"] for r in plan["configuration"]["cognition"]["roles"]]
    return identity, actors, state


def _validate_request(value, identity, actors):
    fields = {"schema_version", "id", "run_id", "configuration_sha256", "action", "created_at", "actors", "message"}
    if not isinstance(value, dict) or set(value) != fields or value["schema_version"] != 1:
        raise ConfigurationError("Unknown operator request fields.")
    if not isinstance(value["id"], str) or re.fullmatch(r"[a-f0-9]{32}", value["id"]) is None:
        raise ConfigurationError("Invalid operator request identity.")
    if value["run_id"] != identity["run_id"] or value["configuration_sha256"] != identity["configuration_sha256"]:
        raise ConfigurationError("Operator request is bound to another execution.")
    if value["action"] not in ACTIONS or not isinstance(value["created_at"], str) or len(value["created_at"]) > 60:
        raise ConfigurationError("Invalid operator action or timestamp.")
    targets = value["actors"]
    if not isinstance(targets, list) or len(targets) > 16 or any(not isinstance(a, str) or a not in actors for a in targets) or len(set(targets)) != len(targets):
        raise ConfigurationError("Operator targets must be unique configured main members.")
    message = value["message"]
    if not isinstance(message, str) or len(message.encode("utf-8")) > 12_000:
        raise ConfigurationError("Feedback text exceeds the private input bound.")
    if value["action"] == "feedback":
        if not message.strip() or not targets:
            raise ConfigurationError("Feedback needs nonempty text and explicit configured recipients.")
    elif message or targets:
        raise ConfigurationError("Only feedback can include text or recipients.")


def _receipt(value, status, wave=None):
    return {"request_id": value["id"], "action": value["action"], "requested_at": value["created_at"],
            "actors": value["actors"], "message_sha256": hashlib.sha256(value["message"].encode()).hexdigest() if value["message"] else None,
            "message_characters": len(value["message"]), "status": status, "boundary_wave": wave}


def submit(run_directory: Path, *, action, message_file=None, actors=None, apply=False):
    selected = Path(run_directory)
    if selected.is_symlink():
        raise ConfigurationError("Select a regular run directory, not a symlink.")
    root = selected.resolve()
    if not (root / "operator/state.json").is_file():
        raise ConfigurationError("This record has no active operator-control implementation; historical records remain immutable.")
    identity, configured, state = _context(root)
    if action not in ACTIONS:
        raise ConfigurationError("Choose pause, resume, stop or feedback.")
    if state["mode"] not in {"running", "paused"} or _read(root / "summary.json")["status"] != "running":
        raise ConfigurationError("This run is terminal; a request cannot restart it.")
    message = ""
    if message_file is not None:
        if action != "feedback":
            raise ConfigurationError("Message files belong only to feedback requests.")
        if root.parent.name != "trials":
            raise ConfigurationError("Feedback files require the original workspace/trials run location.")
        relative = Path(message_file)
        if relative.suffix.lower() not in {".md", ".txt"} or relative.is_absolute() or any(p in {".git", ".venv", "trials", "runs", "setup", "results", "local-reference", "data"} for p in relative.parts) or relative.name.startswith(".env") or relative.name == "private_splits.json":
            raise ConfigurationError("Use bounded workspace-relative feedback text, not credential/runtime paths.")
        if any(root.parent.parent.joinpath(*relative.parts[:i]).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ConfigurationError("Feedback paths cannot use symlinks.")
        path = project_file(root.parent.parent, str(relative))
        if path.stat().st_size > 12_000:
            raise ConfigurationError("Feedback file exceeds 12 KB.")
        message = path.read_text(encoding="utf-8")
    targets = (list(configured) if actors is None else list(actors)) if action == "feedback" else list(actors or [])
    value = {"schema_version": 1, "id": uuid4().hex, "run_id": identity["run_id"],
             "configuration_sha256": identity["configuration_sha256"], "action": action,
             "created_at": now(), "actors": targets, "message": message}
    _validate_request(value, identity, configured)
    result = {"status": "operator_request_draft_only", "request": _receipt(value, "preview_only"),
              "boundary": BOUNDARY, "api_calls": 0, "models_permissions_or_budgets_changed": False,
              "notice": "No request queued. --apply queues an explicit request; queueing is not runtime acknowledgement or feedback understanding."}
    if not apply:
        return result
    folder = root / "operator"
    with _lock(folder):
        _, _, state = _context(root)
        if state["mode"] not in {"running", "paused"} or _read(root / "summary.json")["status"] != "running":
            raise ConfigurationError("The run ended while this request was being reviewed.")
        requests = list((folder / "requests").glob("*.json"))
        seen = {r["request_id"] for r in state["receipts"]}
        if len(requests) >= MAX_REQUESTS or len([p for p in requests if p.stem.split("-")[-1] not in seen]) >= MAX_PENDING:
            raise ConfigurationError("The bounded operator request queue is full.")
        _write(folder / "requests" / (str(time.time_ns()) + "-" + value["id"] + ".json"), value)
    return {**result, "status": "operator_request_queued", "request": _receipt(value, "queued_not_acknowledged"),
            "notice": "Explicit request queued. Current-wave requests may finish; no immediate cancellation or automatic restart is implied."}


class OperatorController:
    def __init__(self, root, compiled, run_id, emit):
        self.root, self.folder, self.emit = root, root / "operator", emit
        self.identity = {"run_id": run_id, "configuration_sha256": compiled["configuration_sha256"]}
        self.actors = [r["actor"] for r in compiled["configuration"]["cognition"]["roles"]]
        self.folder.mkdir(mode=0o700)
        (self.folder / "requests").mkdir(mode=0o700)
        self.state = {"schema_version": 1, **self.identity, "mode": "running", "boundary_wave": 0,
                      "receipts": [], "feedback_exposures": [], "updated_at": now(), "stop_reason": None}
        self.feedback = []
        self.seen = set()
        self._save()

    def _save(self):
        self.state["updated_at"] = now()
        _write(self.folder / "state.json", self.state)

    def _drain(self, wave, *, terminal=False):
        files = sorted((self.folder / "requests").glob("*.json"))
        if len(files) > MAX_REQUESTS:
            raise ConfigurationError("Operator queue exceeds its size bound.")
        for path in files:
            request_id = path.stem.split("-")[-1]
            if request_id in self.seen:
                continue
            try:
                value = _read(path, 30_000)
                _validate_request(value, self.identity, self.actors)
                if value["id"] != request_id:
                    raise ConfigurationError("Request filename and identity do not match.")
                status = "not_applied_run_ended" if terminal else "applied_at_boundary"
                if not terminal:
                    action = value["action"]
                    if self.state["mode"] == "stopped":
                        status = "not_applied_after_stop"
                    elif action == "feedback":
                        self.feedback.append(value)
                        status = "accepted_for_delivery_not_understood"
                    elif action == "stop":
                        self.state.update(mode="stopped", stop_reason="operator_stop")
                    elif action == "pause":
                        status = "already_paused" if self.state["mode"] == "paused" else status
                        self.state["mode"] = "paused"
                    elif action == "resume":
                        status = "already_running" if self.state["mode"] == "running" else status
                        self.state["mode"] = "running"
                receipt = _receipt(value, status, wave)
            except (ConfigurationError, ValueError, KeyError, TypeError, OSError):
                receipt = {"request_id": request_id if re.fullmatch(r"[a-f0-9]{32}", request_id) else "invalid",
                           "action": "unknown", "status": "rejected_invalid_request", "boundary_wave": wave}
            self.seen.add(request_id)
            self.state["receipts"].append(receipt)
            self.emit({"kind": "operator_request_receipt", **receipt})

    async def before_wave(self, wave, deadline, poll_seconds=.1):
        while True:
            with _lock(self.folder):
                self._drain(wave)
                self.state["boundary_wave"] = wave
                if time.monotonic() >= deadline:
                    self.state.update(mode="stopped", stop_reason="wall_time_limit")
                self._save()
                mode, reason = self.state["mode"], self.state["stop_reason"]
            if mode == "stopped":
                raise ControlledStop("Operator boundary stop; no new dependency wave started.", kind=reason)
            if mode != "paused":
                return
            await asyncio.sleep(poll_seconds)

    def frame(self, actor, wave, word_cap):
        candidates = [v for v in self.feedback if actor in v["actors"]]
        selected, remaining = [], word_cap
        for value in reversed(candidates):
            if remaining <= 0:
                break
            words = value["message"].split()
            text = " ".join(words[:remaining])
            if text:
                selected.append({"request_id": value["id"], "requested_at": value["created_at"],
                                 "content": text, "truncated": len(words) > remaining})
                remaining -= len(text.split())
        if not selected:
            return None
        with _lock(self.folder):
            for row in selected:
                exposure = {"request_id": row["request_id"], "actor": actor, "wave": wave,
                            "words": len(row["content"].split()), "truncated": row["truncated"]}
                prior = next((v for v in self.state["feedback_exposures"] if v["request_id"] == row["request_id"] and v["actor"] == actor), None)
                if prior is None:
                    self.state["feedback_exposures"].append({**exposure, "first_wave": wave, "assemblies": 1})
                else:
                    prior.update(wave=wave, words=exposure["words"], truncated=exposure["truncated"], assemblies=prior["assemblies"] + 1)
                self.emit({"kind": "operator_feedback_exposed", **exposure})
            self._save()
        return {"status": "operator_task_context_not_engine_authority", "messages": list(reversed(selected)),
                "earlier_requests_omitted": len(candidates) - len(selected),
                "boundary": "Feedback does not grant tool/source permissions or change models, budgets or statistical settings."}

    def close(self, status):
        with _lock(self.folder):
            self._drain(self.state["boundary_wave"], terminal=True)
            self.state["mode"] = "stopped" if status == "stopped" else "finished"
            self.state["execution_status"] = status
            self._save()


def metadata(root, status):
    path = root / "operator/state.json"
    if not path.exists():
        return {"available": False, "mode": "not_started_or_legacy", "receipts": [], "pending": [], "feedback_exposures": [], "boundary": BOUNDARY}
    if (root / "operator").is_symlink() or (root / "operator/requests").is_symlink():
        raise ConfigurationError("Operator metadata must remain inside the selected run.")
    identity, actors, state = _context(root)
    allowed = ("mode", "boundary_wave", "updated_at", "stop_reason", "execution_status")
    result = {k: deepcopy(state[k]) for k in allowed if k in state}
    receipt_fields = ("request_id", "action", "requested_at", "actors", "message_sha256", "message_characters", "status", "boundary_wave")
    result["receipts"] = [{k: deepcopy(v[k]) for k in receipt_fields if k in v} for v in state["receipts"]]
    result["feedback_exposures"] = [{k: deepcopy(v[k]) for k in ("request_id", "actor", "first_wave", "wave", "words", "truncated", "assemblies") if k in v} for v in state["feedback_exposures"]]
    result["available"] = status == "running" and state["mode"] in {"running", "paused"}
    if status != "running" and state["mode"] in {"running", "paused"}:
        result.update(mode="terminal_unacknowledged_control_state", execution_status=status)
    result["pending"] = []
    seen = {v["request_id"] for v in state["receipts"]}
    paths = sorted((root / "operator/requests").glob("*.json"))
    if len(paths) > MAX_REQUESTS:
        raise ConfigurationError("Operator queue exceeds its size bound.")
    for p in paths:
        if p.stem.split("-")[-1] in seen:
            continue
        try:
            v = _read(p, 30_000)
            _validate_request(v, identity, actors)
            result["pending"].append(_receipt(v, "queued_not_acknowledged"))
        except (ConfigurationError, ValueError, KeyError, TypeError, OSError):
            continue
    result["boundary"] = BOUNDARY
    return result


def schedule(workspace: Path, disturbance, *, apply=False):
    """Preview/apply one explicit pre-run disturbance; never reset bindings or limits."""
    from .config import load, compile_plan
    from .builder import apply_configuration
    c = load(workspace)
    c["dynamics"]["perturbations"].append(deepcopy(disturbance))
    p = compile_plan(workspace, c)
    result = {"status": "disturbance_draft_only", "disturbance": disturbance,
              "configuration_sha256": p["configuration_sha256"], "api_calls": 0,
              "note": "A planned software condition, not model-weight training, a human-team replication or proof of adaptation."}
    if apply:
        written = apply_configuration(workspace, c, reset_cognition=True)
        result.update(status="disturbance_scheduled", backup=written["backup"], engine_settings_changed=False,
                      task_text_changed=False, bindings_regenerated=False)
    return result
