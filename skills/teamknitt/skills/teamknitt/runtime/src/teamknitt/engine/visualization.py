"""Two local, read-only agents project lab plans and runtime metadata into a web view.

These agents use no LLM, credentials or research tools. The setup agent owns the
structural view; the observer tails the runner's metadata-only activity journal.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import math
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qs, urlsplit

from .config import ConfigurationError, project_file


HEARTBEAT_SECONDS = 2
STALE_SECONDS = 15
CONFIRMATION_NODE = "runtime:confirmation"
TERMINAL = {"completed_text_workflow", "completed_research_pilot", "completed_multi_lab_workflow", "failed_or_incomplete", "cancelled"}


def now():
    return datetime.now(timezone.utc).isoformat()


def seconds(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def text(value, limit=180):
    return value[:limit] if isinstance(value, str) else ""


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else 0


# Never copy arbitrary event payloads: provider events also contain prompts and responses.
def activity_metadata(event):
    """The sole allowlist shared by the runner and observer, including old journals."""
    output = {key: text(event.get(key)) for key in (
        "kind", "time", "node", "request_id", "activity_id", "category", "provider", "model", "path", "status")}
    output["seq"] = number(event.get("seq"))
    actor = event.get("actor")
    output["actor"] = {key: text(actor.get(key)) for key in ("id", "team", "episode")} if isinstance(actor, dict) else None
    output["elapsed_seconds"] = number(event.get("elapsed_seconds"))
    for key in ("sequence", "pass", "request_allowance", "time_allowance_seconds"):
        if key in event:
            output[key] = number(event[key])
    if "context_reset" in event:
        output["context_reset"] = event["context_reset"] is True
    if event.get("stop_reason") in {"request_allowance", "time_allowance", "fixed_passes_completed"}:
        output["stop_reason"] = event["stop_reason"]
    if event.get("kind") == "provider_response":
        response = event.get("response")
        usage = (response.get("usage") if isinstance(response, dict) else None) or event.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        output["usage"] = {
            "input_tokens": number(usage.get("input_tokens", usage.get("prompt_tokens"))),
            "output_tokens": number(usage.get("output_tokens", usage.get("completion_tokens"))),
        }
    return output


class SetupVisualizationAgent:
    """Project an exact resolved plan; dependency edges never imply data access."""
    id = "setup-visualizer"

    def visualize(self, plan):
        ranks, nodes = {}, []
        pending = list(plan["work_graph"])
        if len({n["id"] for n in pending}) != len(pending):
            raise ConfigurationError("Cannot visualize duplicate workflow IDs.")
        while pending:
            ready = [n for n in pending if all(dep in ranks for dep in n["depends_on"])]
            if not ready:
                raise ConfigurationError("Cannot visualize invalid or cyclic workflow dependencies.")
            for n in ready:
                rank = max((ranks[d] + 1 for d in n["depends_on"]), default=0)
                ranks[n["id"]] = rank
                parts = n["id"].split(":")
                label = parts[1] if len(parts) > 1 and parts[0].isdigit() else parts[0]
                nodes.append({"id": n["id"], "label": text(n.get("label", label)).replace("_", " "), "kind": n["kind"],
                              "actors": n["actors"][:], "depends_on": n["depends_on"][:], "rank": rank})
                for key in ("sequence", "pass"):
                    if key in n:
                        nodes[-1][key] = number(n[key])
                if "lab" in n:
                    nodes[-1]["lab"] = text(n["lab"])
                pending.remove(n)
        # The bounded runner defers confirmation until after all acting episodes.
        nodes.append({"id": CONFIRMATION_NODE, "label": "Reserved confirmation", "kind": "confirmation",
                      "actors": ["system:verification"], "rank": max(ranks.values(), default=0) + 1,
                      "depends_on": [n["id"] for n in nodes if not any(n["id"] in other["depends_on"] for other in nodes)]})
        actors = [{"id": p["instance_id"], "role": text(p["role"]), "name": text(p.get("name", p["instance_id"])),
                   "approach": text(p.get("approach"))} for p in plan["personas"]]
        return {
            "snapshot_id": plan["configuration_snapshot"]["id"],
            "design": {k: text(plan["design"].get(k)) for k in ("id", "name", "governance", "procedure")},
            "design_letter": "M" if plan.get("execution", {}).get("kind") == "multi_lab" else Path(plan["design"]["file"]).name.split("-")[0][:1].upper(),
            "model": {k: text(plan["configuration_snapshot"]["resolved_config"]["model"].get(k)) for k in ("name", "provider")},
            "communication": text(plan["communication"]["effective_profile"]),
            "statistics": text(plan["statistics"]["approach"]),
            "decision_mode": text(plan["decision_service"]["mode"]),
            "specialist": text(plan["decision_service"].get("specialist")),
            "resources": {k: number(plan["resources"].get(k)) for k in ("max_active_agents", "max_llm_requests", "max_experiments", "max_active_labs")},
            "budget": {k: number(plan["budget"].get(k)) for k in ("max_llm_calls", "max_wall_seconds", "max_evaluations")},
            "delegation": {k: number(plan["delegation"].get(k)) for k in ("max_depth", "max_children_per_agent")},
            "execution": ({key: plan["execution"].get(key) for key in
                           ("kind", "persistence", "effort_mode", "sequences", "passes_per_sequence", "context_policy", "lab_count", "meeting")}
                          if plan.get("execution", {}).get("kind") in {"single_scientist", "multi_lab"} else {"kind": "phase_graph"}),
            "labs": [{"id": text(lab["id"]), "variant": text(lab["variant"]), "design": text(lab["plan"]["design"]["name"]),
                      "sharing": text(lab["plan"]["communication"]["effective_profile"])} for lab in plan.get("multi_lab", {}).get("labs", [])],
            "actors": actors, "nodes": nodes,
        }


class RuntimeObserverAgent:
    """Incrementally reduce telemetry; never open actor outputs or research inputs."""
    id = "runtime-observer"

    def __init__(self):
        self.reset()

    def reset(self):
        self.offset, self.inode = 0, None
        self.nodes, self.actors, self.requests, self.activities = {}, {}, {}, {}
        self.recent = deque(maxlen=40)
        self.last_event_at = None
        self.metrics = dict(requests=0, input_tokens=0, output_tokens=0, errors=0, evaluations=0)
        self.skipped = 0
        self.caught_up = True
        self.progress = {"current_sequence": 0, "current_pass": 0, "completed_passes": 0, "completed_sequences": 0}

    def consume(self, raw):
        event = activity_metadata(raw)
        kind, node, actor = event["kind"], event["node"], event["actor"]
        self.last_event_at = event["time"] or self.last_event_at
        self.recent.append(event)
        if kind == "sequence_started":
            self.progress.update(current_sequence=event.get("sequence", 0), current_pass=0)
        elif kind == "pass_started":
            self.progress.update(current_sequence=event.get("sequence", 0), current_pass=event.get("pass", 0))
        elif kind == "pass_completed":
            self.progress["completed_passes"] += 1
        elif kind == "sequence_finished":
            self.progress["completed_sequences"] += 1
        if actor and actor["id"]:
            self.actors.setdefault(actor["id"], {**actor, "status": "idle", "node": node})
            self.actors[actor["id"]].update(node=node or self.actors[actor["id"]]["node"])
        if kind == "phase_started" and node:
            self.nodes[node] = "running"
        elif kind == "episode_started" and actor:
            self.actors[actor["id"]]["status"] = "running"
            if node:
                self.nodes[node] = "running"
        elif kind == "episode_finished" and actor:
            self.actors[actor["id"]]["status"] = event["status"]
            if node and event["status"] in {"failed", "cancelled"}:
                self.nodes[node] = "interrupted" if event["status"] == "cancelled" else "failed"
        elif kind == "phase_completed" and node:
            if self.nodes.get(node) not in {"deferred", "skipped"}:
                self.nodes[node] = "completed"
        elif kind == "domain_step_pending" and node:
            self.nodes[node] = "deferred"
        elif kind == "operational_coordination" and node:
            self.nodes[node] = "skipped"
        elif kind == "provider_request":
            self.metrics["requests"] += 1
            self.requests[event["request_id"]] = event
        elif kind in {"provider_response", "provider_error"}:
            self.requests.pop(event["request_id"], None)
            if kind == "provider_error":
                self.metrics["errors"] += 1
            else:
                for key in ("input_tokens", "output_tokens"):
                    self.metrics[key] += event["usage"][key]
        elif kind == "activity_started":
            self.activities[event["activity_id"]] = event
            if node:
                self.nodes[node] = "running"
        elif kind == "activity_finished":
            self.activities.pop(event["activity_id"], None)
            if event["status"] == "failed":
                self.metrics["errors"] += 1
                if node:
                    self.nodes[node] = "failed"
            elif event["status"] == "cancelled" and node:
                self.nodes[node] = "interrupted"
            elif node == CONFIRMATION_NODE:
                self.nodes[node] = "completed"
            if event["category"] == "evaluation":
                self.metrics["evaluations"] += 1

    def tail(self, path):
        if not path.exists():
            return
        stat = path.stat()
        if self.inode != (stat.st_dev, stat.st_ino) or stat.st_size < self.offset:
            self.reset()
            self.inode = (stat.st_dev, stat.st_ino)
        with path.open("rb") as stream:
            stream.seek(self.offset)
            # Dedicated activity events are small. Old full journals are bounded too.
            for _ in range(10000):
                start = stream.tell()
                line = stream.readline(1024 * 1024 + 1)
                if not line:
                    break
                if not line.endswith(b"\n"):
                    if len(line) <= 1024 * 1024:
                        stream.seek(start)  # A writer has not finished this line yet.
                        break
                    while line and not line.endswith(b"\n"):
                        line = stream.readline(1024 * 1024 + 1)
                    self.skipped += 1
                else:
                    try:
                        raw = json.loads(line)
                        if not isinstance(raw, dict):
                            raise ValueError()
                        self.consume(raw)
                    except (ValueError, UnicodeError, TypeError, KeyError):
                        self.skipped += 1
                self.offset = stream.tell()
            self.caught_up = self.offset >= path.stat().st_size

    def observe(self, root, setup, *, clock=None):
        current = datetime.now(timezone.utc).timestamp() if clock is None else clock
        if root is None:
            summary, heartbeat, status = {}, {}, "plan_only"
        else:
            # The caller confines root and each fixed filename to the workspace.
            summary = read_json(root, "summary.json") or {}
            heartbeat = read_json(root, "activity-heartbeat.json") or {}
            journal = "activity.jsonl" if (root / "activity.jsonl").exists() else "events.jsonl"
            available = (root / journal).exists()
            if available:
                self.tail(project_file(root, journal))
            recorded = summary.get("status") or heartbeat.get("status")
            beat = seconds(heartbeat.get("time"))
            if recorded in TERMINAL:
                status = "failed" if recorded in {"failed_or_incomplete", "cancelled"} else "completed"
            elif beat is None:
                status = "activity_unknown"
            elif current - beat > STALE_SECONDS or beat - current > STALE_SECONDS:
                status = "stale"
            else:
                status = "running"
            if status == "running" and not self.caught_up:
                status = "catching_up"
            elif status == "running" and (not available or self.skipped):
                status = "activity_unknown"
        states = dict(self.nodes)
        for node in setup["nodes"]:
            states.setdefault(node["id"], "planned")
        for node in setup["nodes"]:
            if states[node["id"]] == "planned" and node["depends_on"] and all(
                states[d] in {"completed", "deferred", "skipped"} for d in node["depends_on"]):
                states[node["id"]] = "ready" if status == "running" else "planned"
        if summary.get("mode") == "text_only":
            states[CONFIRMATION_NODE] = "skipped"
        for key, value in list(states.items()):
            if value == "running" and status != "running":
                states[key] = "interrupted" if status in {"failed", "completed"} else "unknown"
        active = []
        decision_episodes = {e["actor"]["episode"] for e in self.activities.values()
                             if e["category"] == "decision" and e["actor"]}
        for event in [*self.requests.values(), *self.activities.values()]:
            start = seconds(event["time"])
            category = event["category"] or ("decision" if event["provider"].startswith("decision/") or
                       event["actor"] and event["actor"]["episode"] in decision_episodes else "generation")
            active.append({**event, "category": category,
                           "elapsed_seconds": max(0, current - start) if start and status == "running" else None,
                           "status": "running" if status == "running" else "interrupted" if status in {"failed", "completed"} else "unknown"})
        actors = [dict(a) for a in self.actors.values()]
        waiting = {e["actor"]["id"] for e in self.activities.values() if e["category"] == "delegation" and e["actor"]}
        for actor in actors:
            if actor["status"] == "running" and status != "running":
                actor["status"] = "interrupted" if status in {"completed", "failed"} else "unknown"
            elif actor["status"] == "running" and actor["id"] in waiting:
                actor["status"] = "waiting"
        return {"status": status, "recorded_status": text(summary.get("status")),
                "sequence_progress": {key: number((summary.get("sequence_progress") or {}).get(key, value))
                                      if summary.get("status") in TERMINAL else value
                                      for key, value in self.progress.items()},
                "verification_status": summary.get("verification_status") if summary.get("verification_status") in {
                    "not_evaluated", "no_valid_confirmation", "confirmation_evaluated_exploratory"
                } else "not_run" if root is None else "unknown",
                "trial_id": text(summary.get("trial_id")), "variant": text(summary.get("variant")),
                "heartbeat_at": text(heartbeat.get("time")), "last_event_at": self.last_event_at,
                "node_states": states, "actors": actors, "active": active,
                "recent_events": list(self.recent), "metrics": {**self.metrics}, "skipped_events": self.skipped,
                "telemetry": "runtime activity; hardware CPU/GPU utilization is not sampled"}


def read_json(root, name):
    if not (root / name).exists():
        return None
    path = project_file(root, name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (ValueError, UnicodeError):
        return None  # A running writer may be between writes; retry on the next poll.


class VisualizationSession:
    """Own both agents; serve one selected setup plus explicitly selectable saved trials."""
    def __init__(self, plan, workspace=None, variant=None, trial=None):
        self.plan, self.variant, self.trial = plan, variant, trial
        self.workspace = workspace.resolve() if workspace is not None else None
        self.setup_agent, self.observers = SetupVisualizationAgent(), {}
        self.lock = threading.Lock()

    def trial_root(self, name):
        if self.workspace is None or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,200}", name or ""):
            raise ConfigurationError("Choose a saved trial ID from this workspace.")
        root = (self.workspace / "trials" / name).resolve()
        if not root.is_relative_to(self.workspace) or not root.is_dir():
            raise ConfigurationError("Trial is outside this workspace or does not exist.")
        return root

    def snapshot(self, selection=None):
        with self.lock:
            rows = []
            if self.workspace is not None:
                for path in sorted((self.workspace / "trials").glob("*/summary.json"), reverse=True):
                    try:
                        root = self.trial_root(path.parent.name)
                        summary = read_json(root, "summary.json") or {}
                        if self.variant and summary.get("variant") != self.variant:
                            continue
                        rows.append({"id": root.name, "variant": text(summary.get("variant")),
                                     "status": text(summary.get("status")),
                                     "compatible": summary.get("configuration_snapshot_id") == self.plan["configuration_snapshot"]["id"]})
                    except (ConfigurationError, OSError):
                        continue
            selected = selection if selection is not None else self.trial or "latest"
            if selected == "latest":
                selected = next((row["id"] for row in rows if row["compatible"]), "setup")
            root = None if selected == "setup" else self.trial_root(selected)
            plan = self.plan if root is None else read_json(root, "plan.json")
            if plan is None:
                raise ConfigurationError("The saved trial has no complete plan yet; refresh after initialization.")
            setup = self.setup_agent.visualize(plan)
            observer = self.observers.setdefault(selected, RuntimeObserverAgent())
            return {"schema_version": 1, "generated_at": now(), "setup": setup,
                    "runtime": observer.observe(root, setup), "trials": rows,
                    "selection": selected, "requested_selection": selection if selection is not None else self.trial or "latest", "agents": [
                        {"id": self.setup_agent.id, "name": "Setup visualizer", "status": "ready",
                         "description": "Draws the resolved design, personas and workflow dependencies."},
                        {"id": observer.id, "name": "Runtime observer", "status": "watching" if root else "waiting",
                         "description": "Observes local activity metadata and locates active computation."}],
                    "agent_mode": "local; no model calls", "read_only": True}


def render_page(state, api_url=None):
    assets = files("teamknitt.engine.resources").joinpath("visualization")
    bootstrap = json.dumps({"state": state, "api_url": api_url}, allow_nan=False).replace("<", "\\u003c")
    return (assets.joinpath("index.html").read_text(encoding="utf-8")
            .replace("/* teamknitt_CSS */", assets.joinpath("style.css").read_text(encoding="utf-8"))
            .replace("/* teamknitt_BOOTSTRAP */", bootstrap)
            .replace("/* teamknitt_JS */", assets.joinpath("app.js").read_text(encoding="utf-8")))


class VisualizationServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, session, port=8765):
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ConfigurationError("Visualization port must be between 0 and 65535.")
        self.session, self.prefix = session, "/" + secrets.token_urlsafe(24) + "/"
        super().__init__(("127.0.0.1", port), VisualizationHandler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}{self.prefix}"

    def response(self, path, *, host, origin=None):
        if host not in {f"127.0.0.1:{self.server_port}", f"localhost:{self.server_port}"}:
            return 403, "text/plain", "Local access only."
        if origin and origin not in {f"http://127.0.0.1:{self.server_port}", f"http://localhost:{self.server_port}"}:
            return 403, "text/plain", "Same-origin access only."
        request = urlsplit(path)
        try:
            if request.path == self.prefix:
                return 200, "text/html", render_page(self.session.snapshot(), self.prefix + "api/state")
            if request.path == self.prefix + "api/state":
                query = parse_qs(request.query)
                if set(query) - {"trial"} or len(query.get("trial", [])) > 1:
                    return 400, "text/plain", "Invalid view selection."
                selected = query.get("trial", [None])[0]
                return 200, "application/json", json.dumps(self.session.snapshot(selected), allow_nan=False)
        except (ConfigurationError, KeyError, OSError, TypeError, ValueError):
            return 400, "text/plain", "Cannot read this view. Check the workspace and trial selection."
        return 404, "text/plain", "Not found."


class VisualizationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, content_type, body = self.server.response(
            self.path, host=self.headers.get("Host"), origin=self.headers.get("Origin"))
        body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def visualize(project, *, workspace=None, variant=None, trial=None, output=None, port=8765,
              config="configs/lab.yaml", design=None, profile=None, statistics=None,
              persistence=None, sequences=None, effort_mode=None, sequence_context=None, multi_lab=False):
    from .planning import compile_plan
    if (variant or trial or multi_lab) and (design or profile or statistics or config != "configs/lab.yaml"):
        raise ConfigurationError("Variant and saved-trial views use their own settings; preview base-config overrides separately.")
    if trial and any(value is not None for value in (persistence, sequences, effort_mode, sequence_context)):
        raise ConfigurationError("Saved trials retain their recorded persistence and sequence settings.")
    if multi_lab:
        if workspace is None or variant is not None or persistence is not None or effort_mode is not None:
            raise ConfigurationError("Multi-lab visualization needs a workspace and per-lab settings in study.yaml.")
        from .study import load_study
        from .multi_lab import compile_multi_lab
        plan = compile_multi_lab(project, load_study(workspace), workspace=workspace, sequences=sequences, sequence_context=sequence_context)
        variant = "multi-lab"
    elif variant:
        if workspace is None:
            raise ConfigurationError("--variant requires --workspace.")
        from .study import load_study, plans
        resolved = plans(project, load_study(workspace), workspace=workspace, variant_id=variant, persistence=persistence,
                         sequences=sequences, effort_mode=effort_mode, sequence_context=sequence_context)
        if variant not in resolved:
            raise ConfigurationError("Unknown visualization variant.")
        plan = resolved[variant]
    elif trial:
        if workspace is None:
            raise ConfigurationError("--trial requires --workspace.")
        holder = VisualizationSession({}, workspace)
        plan = read_json(holder.trial_root(trial), "plan.json")
        if plan is None:
            raise ConfigurationError("Saved trial plan is unavailable.")
    else:
        plan = compile_plan(project, config, design_file=design, profile=profile, statistical_approach=statistics,
                            persistence=persistence, sequences=sequences, effort_mode=effort_mode,
                            sequence_context=sequence_context)
    session = VisualizationSession(plan, workspace, variant, trial)
    state = session.snapshot()
    if output is not None:
        output = output.expanduser().absolute()
        # Export is explicit and refuses to overwrite a user's existing document.
        with output.open("x", encoding="utf-8") as stream:
            stream.write(render_page(state))
        return {"status": "visualization_saved", "output": str(output), "api_calls": 0}
    with VisualizationServer(session, port) as server:
        print(json.dumps({"status": "visualization_serving", "url": server.url,
                          "agents": [a["id"] for a in state["agents"]], "api_calls": 0}), flush=True)
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
    return {"status": "visualization_stopped", "api_calls": 0}
