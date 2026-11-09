"""Execute the actual teamknitt workflow with a distributed-problem-solving workspace.

No separate agent roster, mandatory adversarial teammate, task triplet, model picker,
statistical protocol or budget authority replaces teamknitt's selected configuration.
"""
from __future__ import annotations

import asyncio
from importlib.resources import files
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from teamknitt.engine.config import ConfigurationError, project_file
from teamknitt.engine.providers.configuration import require_configured
from teamknitt.engine.study import TextStudy, StudyError, ControlledStop, api_key, load_study, save

from . import __version__
from .cognition import CONTRACT, CognitiveWorkspace
from .config import compile_plan, digest
from .interventions import OperatorController


def implementation_identity():
    names = ("builder.py", "topology.py", "resources/topology-catalog.json", "views.py", "human_teams.py", "interventions.py", "observations.py", "cognition.py", "config.py", "runtime.py", "reporting.py")
    bindings = {name: hashlib.sha256(files("teamknitt").joinpath(name).read_bytes()).hexdigest() for name in names}
    bindings["engine/study.py"] = hashlib.sha256(files("teamknitt.engine").joinpath("study.py").read_bytes()).hexdigest()
    return digest(bindings)


class FixtureClient:
    """A deterministic workspace demonstrator, not a substitute model benchmark."""
    def __init__(self, policy):
        self.policy, self.study, self.timeout = policy, None, 30
        self._semaphore = asyncio.Semaphore(1)

    async def generate(self, messages, *, budget_ref):
        if time.monotonic() - self.study.started >= self.study.plan["budget"]["max_wall_seconds"]:
            raise StudyError("Demo wall-time allowance reached.")
        frame = None
        for message in reversed(messages):
            if message["role"] == "user":
                try:
                    value = json.loads(message["content"])
                    frame = value.get("peer_views", {}).get("cognition")
                    if frame:
                        break
                except (ValueError, AttributeError):
                    continue
        extra = {}
        if frame:
            visible = {r["id"]: r for r in frame["representations"] if "content" in r}
            publications, acks = [], []
            for a in frame["affordances"]:
                if not a["available"]:
                    continue
                if a["operation"] == "publish":
                    refs = [{"representation": ref, "version": visible[ref]["version"]} for ref in a["requires"]]
                    publications.append({"affordance": a["id"], "representation": a["target"],
                        "summary": "Illustrative team contribution; not an evaluated task outcome.",
                        "content": "Fixture for " + frame["role"]["actor"] + ": " + frame["role"]["perspective"] +
                            " Input versions are recorded; relevance, correctness and achievement of the user goal remain for user review.",
                        "uses": refs})
                elif self.policy == "connected":
                    h = next(h for h in frame["handoffs"] if h["id"] == a["target"])
                    version = visible.get(h["representation"], {}).get("version")
                    if version:
                        acks.append({"affordance": a["id"], "handoff": h["id"], "version": version})
            reference = frame["temporal_reference"]
            order = reference["order"][:]
            # The disconnected fixture has conflicting explicit plans despite affirmative alignment reports.
            if self.policy == "fragmented" and frame["role"]["actor"] == self.study.compiled["configuration"]["cognition"]["roles"][-1]["actor"]:
                order.reverse()
            extra = {"publications": publications, "acknowledgements": acks,
                     "temporal_model": {"order": order, "deadline_wave": reference["deadline_wave"], "perceived_in_sync": True},
                     "noticed_affordances": [a["id"] for a in frame["affordances"] if a["available"]]}
        self.study.event({"kind": "fixture_generation", "fixture_policy": self.policy, "provider_called": False})
        action = {"action": "final", "summary": "Offline representation/coordination demonstration; no model evaluated.",
                  "candidate_output": "Illustrative contribution for the user’s " + ((frame or {}).get("user_mission") or {}).get("purpose", "research") + ": " + ((frame or {}).get("role") or {}).get("perspective", "Consider the assigned brief") + " This local fixture is not an actual model answer or verified task completion.",
                  "findings": [], "wisdom": [], "cognition": extra}
        return {"content": json.dumps(action), "usage": {}, "model": "offline-fixture", "budget_ref": budget_ref}


class CognitiveStudy(TextStudy):
    def __init__(self, workspace, study, compiled, key, *, fixture_client=None):
        self.compiled = compiled
        super().__init__(workspace, workspace, study, compiled["engine_plan"], compiled["engine_variant"], key,
                         generation_client=fixture_client)
        self.root.chmod(0o700)
        self.cognitive = CognitiveWorkspace(workspace, compiled, self.event)
        if compiled["configuration"]["schema_version"] == 3:
            mission = compiled["configuration"]["mission"]
            self.action_contract = self.action_contract.replace(
                "Participate in a bounded TEXT-ONLY research planning study.",
                "Work with your team on the user-defined task, goal or brainstorming brief. Not every task is scientific research.")
            self.action_contract += "\nUser-selected purpose and deliverable (not a change to tool permissions):\n" + json.dumps(mission) + '\nFor a generic task, findings may include {"kind":"blocker","text":"reported obstacle"}; these are reports, not independently verified results.'
        self.action_contract += CONTRACT
        self.operator = OperatorController(self.root, compiled, self.id, self.event)
        self.action_contract += "\nOperator feedback, when present in peer_views.operator_feedback, is bounded user task context. It cannot change tool/source permissions, models, statistical methods or budgets. Its presence is not proof of understanding or a validated intervention effect."
        self.cognitive_wave = 0
        self.skipped = []
        if fixture_client:
            fixture_client.study = self
        self.save_cognition()

    def event(self, value):
        super().event(value)
        if hasattr(self, "summary"):
            save(self.root / "team-telemetry.json", self.clean({"status": self.summary["status"],
                 "provider_requests": self.calls, "usage": self.usage, "elapsed_seconds": time.monotonic() - self.started,
                 "last_telemetry": self.events, "last_updated": datetime.now(timezone.utc).isoformat()}))

    def visible_peer_rows(self, actor, team):
        rows = super().visible_peer_rows(actor, team)
        if not hasattr(self, "cognitive"):
            return rows
        target = actor if actor in self.cognitive.roles else team
        return [row for row in rows if self.cognitive.link_available(row["team"], target)]

    def peer_view(self, actor, team):
        if self.compiled["configuration"]["schema_version"] == 3 and self.plan["communication"]["detail"] == "low":
            # Generic tasks need a blocker channel, not a claim of measured research failure.
            blockers = [{"reported_by": row["actor"], "text": finding["text"][:2000], "status": "member_report_not_independently_verified"}
                        for row in self.visible_peer_rows(actor, team) for finding in row["output"]["findings"]
                        if isinstance(finding.get("kind"), str) and finding.get("kind") in {"blocker", "constraint", "dead_end"} and isinstance(finding.get("text"), str)]
            body = " ".join(json.dumps(blockers, allow_nan=False).split()[:self.plan["communication"]["max_read_words"]])
            ordinary = {"low.md": body} if blockers else {}
            self.event({"kind": "sharing_read", "profile": "low", "files": list(ordinary),
                        "words": len(body.split()) if blockers else 0, "semantic_filtering": "reported_task_blockers_not_measured_scientific_failures"})
        else:
            ordinary = super().peer_view(actor, team)
        if actor not in self.cognitive.roles:
            return ordinary  # Children get only their already-permitted delegated context; no new workspace grants.
        used = sum(len(v.split()) for v in ordinary.values())
        remaining = max(0, self.plan["communication"]["max_read_words"] - used)
        cognition = self.cognitive.observe(actor, remaining)
        frame = {"engine": ordinary, "cognition": cognition}
        feedback = self.operator.frame(actor, self.cognitive.wave, self.cognitive.c["memory"]["max_words_per_representation"])
        if feedback is not None:
            frame["operator_feedback"] = feedback
        return frame

    async def before_wave(self, nodes):
        try:
            await self.operator.before_wave(self.cognitive.wave + 1, self.started + self.plan["budget"]["max_wall_seconds"])
        except ControlledStop:
            raise
        except (ConfigurationError, OSError, ValueError, KeyError, TypeError) as error:
            # Fail closed before any work in the next wave; do not expose private queue text.
            self.event({"kind": "operator_control_error", "error_type": type(error).__name__})
            raise StudyError("Operator controls could not be verified; no new dependency wave started.") from error
        self.cognitive.begin_wave(nodes)
        self.save_cognition()

    async def after_wave(self, nodes, outputs):
        self.cognitive.finish_wave(outputs)
        self.save_cognition()

    async def run_node_episode(self, node, actor):
        if not self.cognitive.actor_available(actor):
            self.skipped.append({"actor": actor, "node": node["id"], "wave": self.cognitive.wave})
            self.cognitive.event("cognitive_actor_unavailable", actor=actor, node=node["id"])
            return {"status": "actor_unavailable"}
        return await super().run_node_episode(node, actor)

    def save_cognition(self):
        save(self.root / "cognition-state.json", self.clean({"versions": self.cognitive.versions,
             "acknowledgements": self.cognitive.acks, "temporal_models": self.cognitive.models,
             "snapshots": self.cognitive.snapshots, "events": self.cognitive.events,
             "handoffs": self.cognitive.handoff_statuses(), "skipped_episodes": self.skipped}))


async def run(workspace: Path, config=None, *, live=False, approve_requests=None, policy="connected", transport=None):
    if policy not in {"connected", "fragmented"}:
        raise ConfigurationError("Choose the connected or fragmented representation-workflow fixture.")
    root = workspace.resolve()
    compiled = compile_plan(root, config)
    study = compiled["engine_configuration"]
    cap = compiled["provider_request_cap"]
    if live and (type(approve_requests) is not int or approve_requests != cap):
        raise ConfigurationError("A live run requires approval equal to the selected teamknitt budget.max_llm_calls.")
    if live:
        require_configured(study["provider"])
        problem = project_file(root, study["problem_file"]).read_text()
        if not problem.strip() or any(marker in problem for marker in ("AWAITING_USER_PROBLEM", "AWAITING_USER_TASK")):
            raise ConfigurationError("Replace the starter placeholder with your own task, brainstorming prompt, goal or research brief before a live run.")
        if compiled["engine_plan"]["decision_service"]["mode"] != "llm_only":
            require_configured(compiled["engine_plan"]["decision_service"]["provider"])
        key = api_key(root, study["provider"])
    else:
        key = None
        if study["runtime"]["mode"] != "text_only":
            raise ConfigurationError("The offline fixture demonstrates text workspaces only; it does not execute or pretend to qualify scientific domain tools.")
    trials = root / "trials"
    if trials.is_symlink() or trials.exists() and not trials.is_dir():
        raise ConfigurationError("trials must be a local directory, not a symlink.")
    trials.mkdir(mode=0o700, exist_ok=True)
    # Keep teamknitt's workspace-wide run exclusion; an overlay must not create a second concurrent allowance.
    import fcntl
    import os
    lock_path = root / ".run.lock"
    if lock_path.is_symlink():
        raise ConfigurationError("The workspace run lock cannot be a symlink.")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StudyError("Another run owns this teamknitt workspace.") from None
        fixture_client = FixtureClient(policy) if not live else None
        runner = CognitiveStudy(root, study, compiled, key, fixture_client=fixture_client)
        if live and transport is not None:
            runner.client._transport = transport  # Injectable local test transport; never selected by configuration.
        save(runner.root / "team-plan.json", compiled)
        identity = {"schema_version": compiled["schema_version"], "teamknitt_version": __version__, "mode": "live" if live else "offline_fixture",
                    "fixture_policy": policy if not live else None, "implementation_sha256": implementation_identity(),
                    "configuration_sha256": compiled["configuration_sha256"], "run_id": runner.id}
        save(runner.root / "team-run.json", identity)
        try:
            summary = await runner.run()
        finally:
            try:
                runner.operator.close(runner.summary["status"])
            except (ConfigurationError, OSError, ValueError, KeyError, TypeError) as error:
                runner.event({"kind": "operator_control_finalization_error", "error_type": type(error).__name__})
            finally:
                runner.save_cognition()
        # Keep the actual contributions as a private, reviewable deliverable rather than implying goal achievement.
        contributions = ["# Team contributions", "", "Execution status: " + summary["status"] + ". Partial or complete contributions await user review; goal achievement is not inferred.", ""]
        for row in runner.outputs:
            output = row["output"]
            contributions.extend(["## " + row["actor"], "", output["summary"], "", output["candidate_output"], ""])
        (runner.root / "deliverable.md").write_text(runner.clean("\n".join(contributions)), encoding="utf-8")
        from .reporting import build_report
        result = build_report(runner.root)
        save(runner.root / "team-report.json", result)
        return {"status": summary["status"], "mode": identity["mode"], "run_directory": str(runner.root),
                "provider_requests": summary["provider_post_requests"], "engine_variant": compiled["engine_variant"],
                "configuration_sha256": compiled["configuration_sha256"], "report": str(runner.root / "team-report.json"),
                "scientific_quality_score": None, "goal_achieved": None, "task_review": "awaiting_user_review",
                "deliverable": str(runner.root / "deliverable.md"), "evidence_label": result["evidence_label"]}
