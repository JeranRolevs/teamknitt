"""Opt-in bounded workflows with explicit qualified domain-adapter dispatch."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from .config import merge, parse_yaml, project_file, validate
from .contracts import CallerContext, DecisionRequest, DecisionResult, DecisionStatus
from .planning import compile_plan
from .research import ResearchBackend, ResearchError, qualify_workspace, create_backend
from .providers.chat import ChatCompletionsClient
from .providers.http import ProviderError
from .providers.questions import validate_answer, validate_question
from .providers.configuration import generation_settings, require_configured
from .providers.typed import TypedDecisionBackend
from .decisions import decision_client_for, resolve_specialist, validate_declarations
from .visualization import activity_metadata, HEARTBEAT_SECONDS, CONFIRMATION_NODE
from .persistence import pass_task
from .sharing import filtered_view

ACTOR = ContextVar("study_actor", default=None)
NODE = ContextVar("study_node", default=None)
SCIENTIST_COMPARISON_FIELDS = ("scientist_persistence", "scientist_effort_mode", "scientist_sequences",
                               "scientist_context_policy", "scientist_sequences_completed", "scientist_passes_completed")
MULTI_LAB_COMPARISON_FIELDS = ("lab_count", "lab_sequences", "lab_sequences_completed", "lab_meeting", "lab_sharing")


class StudyError(ValueError):
    pass


class SequenceBudgetReached(RuntimeError):
    """An expected boundary for a user-selected budget-driven sequence."""


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def mapping(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise StudyError(label + " has missing or unknown fields.")
    return value


def load_study(workspace):
    workspace = workspace.resolve()
    c = parse_yaml(project_file(workspace, "study.yaml").read_text())
    fields = {"schema_version", "name", "problem_file", "provider", "runtime", "base_overrides", "variants"}
    if isinstance(c, dict) and "decision_providers" in c:
        fields.add("decision_providers")
    if isinstance(c, dict) and "multi_lab" in c:
        fields.add("multi_lab")
    mapping(c, fields, "study")
    validate_declarations(c, workspace)
    if c["schema_version"] != 1 or not isinstance(c["name"], str) or not c["name"].strip():
        raise StudyError("Study needs schema_version 1 and a name.")
    try:
        c["provider"] = p = generation_settings(c["provider"])
    except ProviderError as error:
        raise StudyError(str(error)) from None
    if not isinstance(c["problem_file"], str) or not c["problem_file"].strip():
        raise StudyError("problem_file must be a project-relative path.")
    runtime_fields={"mode","max_actions_per_episode","max_findings","comparison_metrics"}
    if isinstance(c["runtime"],dict) and c["runtime"].get("mode")=="research":
        runtime_fields.add("domain_config")
    r = mapping(c["runtime"],runtime_fields,"runtime")
    if r["mode"] not in {"text_only","research"}:
        raise StudyError("Unsupported runtime mode.")
    if r["mode"]=="research":
        project_file(workspace,r["domain_config"])
    for name in ("max_actions_per_episode", "max_findings"):
        if isinstance(r[name], bool) or not isinstance(r[name], int) or r[name] < 1:
            raise StudyError("Runtime count limits must be positive integers.")
    if not isinstance(r["comparison_metrics"], list) or not all(isinstance(x, str) and re.fullmatch(r"[a-z][a-z0-9_]*", x) for x in r["comparison_metrics"]):
        raise StudyError("Comparison metrics must be lowercase identifiers.")
    reserved = {"trial_id", "variant", "status", "verification_status", "elapsed_seconds", "provider_post_requests",
                "output_count", "chat_input_tokens", "chat_output_tokens", "decision_input_tokens",
                "decision_output_tokens", "missing_usage_receipts", "measurement_source"}
    reserved.update(SCIENTIST_COMPARISON_FIELDS)
    reserved.update(MULTI_LAB_COMPARISON_FIELDS)
    reserved.add("configuration_snapshot_id")
    if set(r["comparison_metrics"]) & reserved:
        raise StudyError("Comparison metric names conflict with system columns.")
    if len(set(r["comparison_metrics"])) != len(r["comparison_metrics"]):
        raise StudyError("Comparison metric names must be unique.")
    if not isinstance(c["base_overrides"], dict) or not isinstance(c["variants"], list) or not c["variants"]:
        raise StudyError("Supply lab overrides and at least one variant.")
    seen = set()
    for v in c["variants"]:
        mapping(v, {"id", "overrides"}, "variant")
        if not isinstance(v["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", v["id"]) or v["id"] in seen or not isinstance(v["overrides"], dict):
            raise StudyError("Variants need unique lowercase path-safe IDs and mapping overrides.")
        seen.add(v["id"])
    if "multi_lab" in c:
        validate(c["multi_lab"], "multi_lab.schema.json")
        labs = c["multi_lab"]["labs"]
        if len({lab["id"] for lab in labs}) != len(labs) or any(lab["variant"] not in seen for lab in labs):
            raise StudyError("Multi-lab entries need unique lab IDs and existing study variants.")
    project_file(workspace, c["problem_file"])
    if not (workspace / p["env_file"]).resolve().is_relative_to(workspace):
        raise StudyError("The private env file must stay inside the workspace.")
    return c


def api_key(workspace, provider):
    name = provider["api_key_env"]
    if name is None:
        return None
    key = os.environ.get(name, "").strip()
    if key:
        return key
    if (workspace / provider["env_file"]).exists():
        for line in project_file(workspace, provider["env_file"]).read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            field, sep, value = line.partition("=")
            if sep and field.strip() == name:
                value = value.strip()
                if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
                    value = value[1:-1]
                if value and value not in {"your-key", "replace-me", "YOUR_API_KEY"}:
                    return value
    raise StudyError("Set " + name + " in the workspace .env or process environment; never put credentials in study.yaml.")


def plans(project, config, *, workspace=None, variant_id=None, persistence=None, sequences=None, effort_mode=None, sequence_context=None):
    result = {}
    for variant in config["variants"]:
        overrides = merge(config["base_overrides"], variant["overrides"])
        overrides["model"] = {"provider": "chat_completions", "name": config["provider"]["model"]}
        # Overrides apply only to the requested variant and are part of its snapshot.
        plan = compile_plan(project, config_overrides=overrides,
                            **({"persistence": persistence, "sequences": sequences, "effort_mode": effort_mode,
                                "sequence_context": sequence_context} if variant["id"] == variant_id else {}))
        generation = generation_settings(config["provider"])
        bindings = {"generation": generation}
        if plan["statistics"].get("prior_records"):
            from .priors import runtime_priors
            records = runtime_priors(workspace or project, config, plan["statistics"])
            bindings["prior_approvals"] = {target: record["record_sha256"] for target, record in records.items()}
            plan["statistics"].update(status="reviewed_prior_protocol_bound", prior_adoption="explicit_user_review",
                                      sensitivity="declared_alternatives_on_each_measured_primary_result")
        plan["generation_provider"] = generation
        if plan["decision_service"]["mode"] != "llm_only":
            settings = resolve_specialist(config, plan["decision_service"]["specialist"])
            plan["decision_service"]["provider"] = settings
            bindings["decision"] = settings
        snapshot = plan["configuration_snapshot"]
        structural_hash = snapshot["sha256"]
        bound_hash = hashlib.sha256(json.dumps(
            {"structural": structural_hash, "providers": bindings},
            sort_keys=True, allow_nan=False).encode()).hexdigest()
        snapshot.update(id="config-" + bound_hash[:20], sha256=bound_hash,
                        structural_sha256=structural_hash, providers=bindings)
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", role["instance_id"]) for role in plan["personas"]):
            raise StudyError("Runtime actor IDs must be path-safe.")
        result[variant["id"]] = plan
    return result


def client_for(config, key, **kwargs):
    p = generation_settings(config["provider"])
    return ChatCompletionsClient(key, model=p["model"], base_url=p["base_url"], endpoint=p["endpoint"],
        models_endpoint=p["models_endpoint"], timeout=p["timeout_seconds"], max_tokens=p["max_output_tokens"],
        max_parallel=kwargs.pop("max_parallel", p["max_parallel_requests"]),
        max_output_field=p["max_output_field"], request_options=p["request_options"], **kwargs)


def prepare(project, workspace):
    config = load_study(workspace)
    resolved = plans(project, config, workspace=workspace)
    for name, plan in resolved.items():
        save(workspace / "plans" / (name + ".json"), plan)
    return {"status": "prepared", "variants": list(resolved), "model": config["provider"]["model"],
            "research_started": False, "api_calls": 0, "workspace": str(workspace)}


async def doctor(project, workspace, *, live=False, variant=None):
    config = load_study(workspace)
    resolved = plans(project, config, workspace=workspace)
    if variant is not None:
        if variant not in resolved:
            raise StudyError("Unknown doctor variant; inspect study prepare.")
        resolved = {variant: resolved[variant]}
    try:
        key = api_key(workspace, config["provider"])
    except StudyError:
        key = None
    selected, keys = {}, {}
    for plan in resolved.values():
        if plan["decision_service"]["mode"] != "llm_only":
            settings = resolve_specialist(config, plan["decision_service"]["specialist"])
            identity = settings["provider_id"]
            selected[identity] = settings
            try:
                keys[identity] = api_key(workspace, settings)
            except StudyError:
                keys[identity] = None
    problem = project_file(workspace, config["problem_file"]).read_text()
    result = {"checked_at": timestamp(), "status": "local_ready" if (key or config["provider"]["api_key_env"] is None) and all(keys[i] or selected[i]["api_key_env"] is None for i in selected) else "credential_missing",
              "variants": list(resolved), "model": config["provider"]["model"], "key_present": bool(key),
              "decision_providers": {identity: {"model": settings["model"], "key_present": bool(keys[identity]),
                                                "status": "not_tested" if keys[identity] or settings["api_key_env"] is None else "credential_missing"}
                                     for identity, settings in selected.items()},
              "research_problem_supplied": bool(problem.strip()) and "AWAITING_USER_PROBLEM" not in problem,
              "research_started": False, "live_checks_run": False}
    if live:
        require_configured(config["provider"])
        for settings in selected.values():
            require_configured(settings)
    if live and result["status"] == "local_ready":
        client = client_for(config, key)
        result["live_checks_run"] = True
        try:
            if client.models_endpoint is not None and client.model not in await client.models():
                raise ProviderError("unknown_model_or_path", "Configured generation model is not listed by the account.")
            reply = await client.generate([{"role": "user", "content": "Connectivity check. Reply only OK."}],
                                          budget_ref="connection_check")
            result["chat"] = {"status": "connected", "model": reply["model"], "usage": reply["usage"]}
            for identity, settings in selected.items():
                decision_client = decision_client_for(settings, keys[identity])
                probe = await decision_client.assess_text("The connection check succeeded.", {
                    "connection": {"type": "noul", "instructions": "Does this text say the connection check succeeded?"}})
                checked = {"status": "connected", "model": probe.get("model", settings["model"]),
                           "usage": probe.get("usage", {})}
                result["decision_providers"][identity].update(checked)
            result["status"] = "connected"
        except ProviderError as error:
            result["status"] = "connection_failed"
            result["error"] = {"kind": error.kind, "http_status": error.http_status, "message": str(error)}
    save(workspace / "setup" / "connection.json", result)
    return result


def parse_action(content):
    text = content.strip()
    fence = chr(96) * 3
    if text.startswith(fence) and text.endswith(fence):
        text = text.split("\n", 1)[1].rsplit(fence, 1)[0]
    try:
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError()
        json.dumps(value, allow_nan=False)
        return value
    except (ValueError, TypeError):
        raise StudyError("Model returned no finite JSON action; raw output is retained and no success is inferred.") from None


ACTION_CONTRACT = """Participate in a bounded TEXT-ONLY research planning study.
Do not claim to have executed code, experiments, statistics or independent verification.
The user controls the lab organization. You see only permitted inputs. Return ONE JSON object:
{"action":"final","summary":"...","findings":[{"kind":"proposal","text":"...","evidence_refs":[]}],
 "wisdom":[{"lesson":"conditional abstraction, no detailed recipe","conditions":"...","limits":"..."}],
 "candidate_output":"proposed output, explicitly unverified"}
OR {"action":"decision.assess","spec_id":"semantic_choice.v1","question":
 {"type":"choice","instructions":"bounded semantic question","criteria":{"a":"...","b":"..."}}}
The decision service also accepts noul (no criteria) and score (ordered criteria list).
Request it only for a useful compatible question. A result resumes this conversation.
OR {"action":"delegate","task":"bounded child task and expected output"}
Do not invent evidence IDs. State uncertainty. Wisdom omits identities, rankings and exact recipes.
"""


class TextStudy:
    def __init__(self, project, workspace, config, plan, variant, key, *, trial_root=None,
                 shared_limits=None, event_sink=None, generation_client=None):
        self.project, self.workspace, self.config, self.plan, self.key = project, workspace, config, plan, key
        self.shared_limits, self.event_sink = shared_limits, event_sink
        self.inter_lab_context = {}
        self._secrets = {key} if key else set()
        self.specialist_client = None
        self.decision_settings = None
        self.id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + variant + "-" + uuid4().hex[:8]
        self.root = trial_root if trial_root is not None else workspace / "trials" / self.id
        self.root.mkdir(parents=True, exist_ok=False)
        self.started = time.monotonic()
        self.calls = self.events = self.active = 0
        self.execution = plan.get("execution", {"kind": "phase_graph"})
        self.sequence_request_end = self.sequence_deadline = None
        self.progress = ({"sequences": self.execution["sequences"], "completed_sequences": 0,
                          "current_sequence": 0, "current_pass": 0, "completed_passes": 0,
                          "passes_per_sequence": self.execution["passes_per_sequence"]}
                         if self.execution["kind"] == "single_scientist" else None)
        self.descendants, self.history, self.outputs = {}, {}, []
        self.usage = {"chat_input_tokens": 0, "chat_output_tokens": 0,
                      "decision_input_tokens": 0, "decision_output_tokens": 0, "missing_usage_receipts": 0}
        self.decision_usage = {}
        self.snapshot = plan["configuration_snapshot"]["id"]
        self.research = create_backend(workspace,config["runtime"]["domain_config"],self.root,plan) if config["runtime"]["mode"]=="research" else None
        self.action_contract=ACTION_CONTRACT
        if self.research is not None:
            self.research.generation_model=config["provider"]["model"]
            self.action_contract=self.action_contract.replace(
                "Participate in a bounded TEXT-ONLY research planning study.",
                "Participate in a bounded measured research study.").replace(
                "Do not claim to have executed code, experiments, statistics or independent verification.",
                "Claim execution only when an experiment.run receipt supports it. Execute only through the declared scientific tool.")
            if hasattr(self.research,"action_contract"):
                self.action_contract += self.research.action_contract
            else:
                self.action_contract += """
Additional scientific tool:
{"action":"experiment.run","candidate":{"statistic":"damp_raw","reference":"growing","window":2000,"threshold":"age_matched_rank","gamma":0}}
Allowed statistics: damp_raw, knn5_raw, mean_distance_raw.
Allowed reference: growing or bounded; window: 2000,3000,4500,6000,10000.
Allowed threshold: short_rank, age_matched_rank, age_scaled_rank; gamma: 0..1.
A registered, OS-sandboxed Python evaluator fits thresholds on separate event-free calibration
blocks and returns measured development FAR, CP intervals/counts, real-event hits/delays.
Do not change the calibration, split or evaluator rules. Unsupported methods stay unsupported.
Use experiment.run to test a concrete candidate during this study; analysis alone does not
establish a useful detector. Include actual receipt IDs in findings.evidence_refs. The shared
development evaluation budget is small; preserve useful results when exhausted.
Confirmation is withheld from agents and runs once after search; never request its data.
Generalization to external datasets and unimplemented analysis methods is untested by this
initial tool, so do not claim those capabilities solved.
"""
        self.client = generation_client if generation_client is not None else client_for(config, key, reserve=self.reserve, on_event=self.event,
                                 shared_semaphore=shared_limits.llm_semaphore if shared_limits else None,
                                 max_parallel=min(config["provider"]["max_parallel_requests"], plan["resources"]["max_llm_requests"]))
        if plan["decision_service"]["mode"] != "llm_only":
            self.decision_settings = resolve_specialist(config, plan["decision_service"]["specialist"])
            settings = self.decision_settings
            try:
                specialist_key = api_key(workspace, settings)
                available = True
            except StudyError:
                specialist_key, available = None, False
            if available:
                if specialist_key:
                    self._secrets.add(specialist_key)
                self.specialist_client = decision_client_for(settings, specialist_key,
                    shared_semaphore=self.client._semaphore, reserve=self.reserve, on_event=self.event)
        self.roles = {r["instance_id"]: r for r in plan["personas"]}
        self.problem = project_file(workspace, config["problem_file"]).read_text()
        self.design = project_file(project, plan["design"]["file"]).read_text()
        self.summary = {"trial_id": self.id, "variant": variant, "started_at": timestamp(),
                        "status": "running", "mode": config["runtime"]["mode"], "verification_status": "not_evaluated",
                        "configuration_snapshot_id": self.snapshot, "statistics": plan["statistics"],
                        "quality_metrics": {}, "actual_cost": None}
        if self.progress is not None:
            self.summary.update(execution=self.execution, sequence_progress=self.progress, sequence_results=[])
        save(self.root / "plan.json", plan)
        save(self.root / "study_config.json", config)
        (self.root / "problem.md").write_text(self.clean(self.problem))
        save(self.root / "summary.json", self.summary)

    def clean(self, value):
        if isinstance(value, str):
            for secret in sorted(self._secrets, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {self.clean(k): self.clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(v) for v in value]
        return value

    def event(self, value):
        self.events += 1
        provider = value.get("provider", "generation")
        specialist = provider.startswith("decision/")
        if value.get("kind") == "provider_request" and specialist:
            identity = provider
            row = self.decision_usage.setdefault(identity, {"requests": 0, "input_tokens": 0, "output_tokens": 0})
            row["requests"] += 1
        if value.get("kind") == "provider_error":
            self.usage["missing_usage_receipts"] += 1
        if value.get("kind") == "provider_response":
            usage = value["response"].get("usage") or {}
            incoming = usage.get("prompt_tokens", usage.get("input_tokens"))
            outgoing = usage.get("completion_tokens", usage.get("output_tokens"))
            if isinstance(incoming, int) and not isinstance(incoming, bool) and incoming >= 0:
                if specialist:
                    identity = provider
                    row = self.decision_usage.setdefault(identity, {"requests": 0, "input_tokens": 0, "output_tokens": 0})
                    row["input_tokens"] += incoming
                    self.usage["decision_input_tokens"] += incoming
                else:
                    self.usage["chat_input_tokens"] += incoming
            else:
                self.usage["missing_usage_receipts"] += 1
            if isinstance(outgoing, int) and not isinstance(outgoing, bool) and outgoing >= 0:
                if specialist:
                    self.usage["decision_output_tokens"] += outgoing
                    identity = provider
                    self.decision_usage.setdefault(identity, {"requests": 0, "input_tokens": 0, "output_tokens": 0})["output_tokens"] += outgoing
                else:
                    self.usage["chat_output_tokens"] += outgoing
        progress = ({"sequence": self.progress["current_sequence"], "pass": self.progress["current_pass"]}
                    if self.progress is not None else {})
        event = self.clean({"seq": self.events, "time": timestamp(), "actor": ACTOR.get(), "node": NODE.get(), **progress, **value})
        with (self.root / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event, allow_nan=False) + "\n")
        with (self.root / "activity.jsonl").open("a") as stream:
            stream.write(json.dumps(activity_metadata(event), allow_nan=False) + "\n")
        if self.event_sink is not None:
            self.event_sink(activity_metadata(event))

    @contextmanager
    def activity(self, category):
        identity = uuid4().hex
        self.event({"kind": "activity_started", "activity_id": identity, "category": category})
        started, status = time.monotonic(), "completed"
        try:
            yield
        except BaseException as error:
            status = "budget_exhausted" if isinstance(error, SequenceBudgetReached) else (
                "cancelled" if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)) else "failed")
            raise
        finally:
            self.event({"kind": "activity_finished", "activity_id": identity, "category": category,
                        "status": status, "elapsed_seconds": time.monotonic() - started})

    def heartbeat(self):
        save(self.root / "activity-heartbeat.json", {"time": timestamp(), "status": self.summary["status"]})

    async def pulse(self):
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            self.heartbeat()

    def reserve(self):
        if self.sequence_request_end is not None and self.calls >= self.sequence_request_end:
            raise SequenceBudgetReached("request_allowance")
        if self.sequence_deadline is not None and time.monotonic() >= self.sequence_deadline:
            raise SequenceBudgetReached("time_allowance")
        if self.calls >= self.plan["budget"]["max_llm_calls"]:
            raise StudyError("Trial request budget exhausted, including decisions and fallbacks.")
        if time.monotonic() - self.started >= self.plan["budget"]["max_wall_seconds"]:
            raise StudyError("Trial wall-time budget exhausted.")
        remaining = self.plan["budget"]["max_wall_seconds"] - (time.monotonic() - self.started)
        if self.shared_limits is not None:
            remaining = min(remaining, self.shared_limits.reserve_request())
        self.calls += 1
        if self.sequence_deadline is not None:
            remaining = min(remaining, self.sequence_deadline - time.monotonic())
        self.client.timeout = min(self.config["provider"]["timeout_seconds"], remaining)
        if self.specialist_client is not None and self.specialist_client is not self.client:
            self.specialist_client.timeout = min(self.decision_settings["timeout_seconds"], remaining)

    def visible_peer_rows(self, actor, team):
        return [row for row in self.outputs if row["team"] != team]

    def peer_view(self, actor, team):
        policy = self.plan["communication"]
        if not policy["research_exchange"]:
            return {}
        peers = self.visible_peer_rows(actor, team)
        valid = (ref for ref, entry in self.research.receipts.items()
                 if entry["result"].get("status") == "valid") if self.research is not None else ()
        view, low_count = filtered_view(peers, policy, valid)
        view = self.clean(view)
        folder = self.root / "communication" / actor / str(self.events+1).zfill(6)
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in view.items():
            (folder / name).write_text(text + "\n")
        self.event({"kind": "sharing_read", "profile": policy["effective_profile"], "files": list(view),
                    "words": sum(len(v.split()) for v in view.values()), "low_tested_dead_ends": low_count,
                    "semantic_filtering": "structured_agent_output_best_effort_not_formal"})
        return view

    async def judge(self, question, state):
        reply = await self.client.generate([
            {"role": "system", "content": "Answer a bounded semantic question as JSON only. noul: {\"noul\": probability_yes}; choice: {\"choice\":option_id,\"confidence\":probability,\"probabilities\":{option_id:probability,...}}; score: {\"score\":expected_zero_based_position,\"confidence\":probability,\"probabilities\":[probability,...]}. Probabilities sum to one. Do not invoke tools. Judgment is not empirical verification."},
            {"role": "user", "content": json.dumps(self.clean({"state": state, "question": question}))}
        ], budget_ref=self.id)
        return validate_answer(question, parse_action(reply["content"]))

    async def decision(self, actor, team, episode, action, messages):
        p = self.plan["decision_service"]
        if not p["agent_access"] or action.get("spec_id") not in p["allowed_specs"]:
            return {"status": "unsupported", "reason": "Question spec not permitted."}
        question = validate_question(action.get("question", {}))
        state = json.dumps(self.clean(messages))
        ref = "context:" + episode
        caller = CallerContext(actor, team, self.config["name"], episode, self.snapshot,
                               "mission-input-and-exposure", (ref,), self.id)
        request = DecisionRequest(uuid4().hex, action["spec_id"], "agent_local_semantic_question", (ref,), caller, question)
        if p["mode"] == "llm_only":
            return {"status": "answered", "backend": "same_llm", "answer": await self.judge(question, state)}
        async def assess():
            if self.specialist_client is None:
                return DecisionResult(request.request_id, DecisionStatus.UNAVAILABLE, None,
                                      self.decision_settings["provider_id"], request.context_refs,
                                      {"error_kind": "missing_key"})
            return await TypedDecisionBackend(self.specialist_client, lambda req: self.clean(state)).assess(request)
        if p["mode"] == "shadow":
            primary = await self.judge(question, state)
            shadow = await assess()
            self.event({"kind": "shadow_decision", "result": asdict(shadow), "visible_to_agent": False})
            return {"status": "answered", "backend": "same_llm", "answer": primary}
        result = await assess()
        self.event({"kind": "decision_result", "result": asdict(result)})
        if result.status == DecisionStatus.ANSWERED:
            return {"status": "answered", "backend": result.backend_id, "model_id": result.model_id, "answer": result.answer}
        self.event({"kind": "decision_fallback", "from_backend": result.backend_id,
                    "specialist_status": str(result.status), "to_backend": "same_llm"})
        return {"status": "answered", "backend": "same_llm_fallback", "specialist_status": str(result.status),
                "answer": await self.judge(question, state)}

    async def episode(self, actor, team, role, task, *, depth=0, parent_context=None, tools_allowed=True):
        if self.active >= self.plan["resources"]["max_active_agents"]:
            return {"status": "resource_denied", "summary": "Active-agent limit reached."}
        if depth and self.descendants.get(team, 0) >= self.plan["delegation"]["max_active_descendants"]:
            return {"status": "resource_denied", "summary": "Active-descendant limit reached."}
        self.active += 1
        if depth:
            self.descendants[team] = self.descendants.get(team, 0)+1
        episode = actor + ":" + uuid4().hex[:8]
        token = ACTOR.set({"id": actor, "episode": episode, "team": team})
        outcome = "failed"
        try:
            self.event({"kind": "episode_started"})
            if actor not in self.history:
                self.history[actor] = [
                    {"role": "system", "content": self.action_contract + "\nYour role:\n" + json.dumps(role) + "\nLab design:\n" + self.design},
                    {"role": "user", "content": json.dumps({"problem": self.problem, "parent_permitted_context": parent_context})}]
            messages = self.history[actor]
            messages.append({"role": "user", "content": json.dumps({"phase_task": task, "peer_views": self.peer_view(actor, team),
                            "statistics": self.plan["statistics"], "runtime": self.config["runtime"]["mode"],
                            **({"lab_exchange": self.inter_lab_context} if self.inter_lab_context else {})})})
            decisions = children = 0
            for turn in range(self.config["runtime"]["max_actions_per_episode"]):
                reply = await self.client.generate(self.clean(messages), budget_ref=self.id)
                messages.append({"role": "assistant", "content": reply["content"]})
                try:
                    action = parse_action(reply["content"])
                except StudyError:
                    self.event({"kind":"action_rejected","reason":"invalid_json","episode":episode,
                                "tool_dispatched":False})
                    messages.append({"role":"user","content":json.dumps({"action_error":{
                        "status":"invalid_json","instructions":"Return one valid finite JSON object matching the action contract. No action was executed. This correction uses your existing action/request budget."}})})
                    continue
                if action.get("action") == "final":
                    if not all(isinstance(action.get(k), str) for k in ("summary", "candidate_output")):
                        raise StudyError("Final action is missing text fields.")
                    for field in ("findings", "wisdom"):
                        if not isinstance(action.get(field), list) or not all(isinstance(v, dict) for v in action[field]):
                            raise StudyError("Final action has an invalid findings/wisdom list.")
                        action[field] = action[field][:self.config["runtime"]["max_findings"]]
                    output = {"actor": actor, "team": team, "episode": episode, "depth": depth, "output": action}
                    save(self.root / "actors" / actor / (episode.replace(":", "_")+".json"), self.clean(output))
                    outcome = "completed"
                    return output
                if not tools_allowed:
                    raise StudyError("Meeting contributions accept final actions only; no research tools are dispatched.")
                if action.get("action") == "decision.assess":
                    if decisions >= self.plan["decision_service"]["max_calls_per_episode"]:
                        response = {"status": "budget_exhausted", "reason": "Episode decision-call limit."}
                    else:
                        decisions += 1
                        try:
                            with self.activity("decision"):
                                response = await self.decision(actor, team, episode, action, messages)
                        except StudyError:
                            response={"status":"invalid_decision","reason":"The decision judge did not return a valid JSON answer; no judgment is available."}
                        except ProviderError as error:
                            if error.kind not in {"invalid_question","invalid_response"}:
                                raise
                            response={"status":"invalid_decision","reason":str(error)}
                elif action.get("action") == "experiment.run":
                    if self.research is None:
                        response={"status":"unsupported","reason":"This trial is text_only."}
                    else:
                        with self.activity("evaluation"):
                            result=await self.research.evaluate(actor,team,action.get("candidate"))
                        response=self.research.visible_result(result)
                        self.event({"kind":"experiment_result","receipt_id":result.get("receipt_id"),
                                    "status":result["status"],"source_ref":result.get("source_ref")})
                elif action.get("action") == "delegate":
                    if not isinstance(action.get("task"), str) or not action["task"].strip():
                        raise StudyError("Delegation needs a nonempty task.")
                    limits = self.plan["delegation"]
                    if depth >= limits["max_depth"] or children >= limits["max_children_per_agent"]:
                        response = {"status": "resource_denied", "reason": "Depth or child-count limit."}
                    else:
                        children += 1
                        with self.activity("delegation"):
                            response = await self.episode(actor+".child"+str(children), team,
                                {"role": "child", "approach": role["approach"]}, action["task"],
                                depth=depth+1, parent_context=messages[:])
                else:
                    raise StudyError("Unsupported model action; no file or code execution is granted.")
                messages.append({"role": "user", "content": json.dumps({"tool_result": response})})
            raise StudyError("Episode action limit reached; partial responses retained.")
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except SequenceBudgetReached:
            outcome = "budget_exhausted"
            raise
        finally:
            try:
                self.event({"kind": "episode_finished", "status": outcome})
            finally:
                ACTOR.reset(token)
                self.active -= 1
                if depth:
                    self.descendants[team] -= 1

    async def run_node_episode(self, node, actor):
        token = NODE.set(node["id"])
        try:
            self.event({"kind": "phase_started", "actor": {"id": actor, "team": actor}})
            if self.execution["kind"] == "single_scientist":
                return await self.run_scientist_node(node, actor)
            return await self.episode(actor, actor, self.roles[actor], node["id"])
        finally:
            NODE.reset(token)

    def start_sequence(self, sequence, actor):
        reset = sequence > 1 and self.execution["context_policy"] == "fresh_sequence"
        if reset:
            self.history.pop(actor, None)
        self.progress.update(current_sequence=sequence, current_pass=0)
        self.sequence_started_calls = self.calls
        self.sequence_started_passes = self.progress["completed_passes"]
        self.event({"kind": "sequence_started", "context_reset": reset,
                    "actor": {"id": actor, "team": actor}})

    def finish_sequence(self, sequence, reason):
        self.progress["completed_sequences"] += 1
        result = {"sequence": sequence, "stop_reason": reason, "requests_used": self.calls-self.sequence_started_calls,
                  "completed_passes": self.progress["completed_passes"]-self.sequence_started_passes}
        self.summary["sequence_results"].append(result)
        self.event({"kind": "sequence_finished", "sequence": sequence, "status": "completed", "stop_reason": reason})

    async def scientist_pass(self, sequence, step, actor):
        self.progress.update(current_sequence=sequence, current_pass=step)
        self.event({"kind": "pass_started", "actor": {"id": actor, "team": actor}})
        result = await self.episode(actor, actor, self.roles[actor], pass_task(self.execution, sequence, step))
        if "output" not in result:
            raise StudyError("Single-scientist pass could not start or produce an episode result.")
        self.progress["completed_passes"] += 1
        self.event({"kind": "pass_completed", "actor": {"id": actor, "team": actor}})
        return result

    async def run_scientist_node(self, node, actor):
        sequence = node["sequence"]
        if self.execution["effort_mode"] == "fixed_passes":
            if node["pass"] == 1:
                self.start_sequence(sequence, actor)
            result = await self.scientist_pass(sequence, node["pass"], actor)
            if node["pass"] == self.execution["passes_per_sequence"]:
                self.finish_sequence(sequence, "fixed_passes_completed")
            return result
        remaining_calls = self.plan["budget"]["max_llm_calls"] - self.calls
        remaining_time = self.plan["budget"]["max_wall_seconds"] - (time.monotonic() - self.started)
        if self.shared_limits is not None:
            remaining_calls = min(remaining_calls, self.shared_limits.remaining_requests())
            remaining_time = min(remaining_time, self.shared_limits.remaining_time())
        remaining_sequences = self.execution["sequences"] - sequence + 1
        if remaining_calls < remaining_sequences or remaining_time <= 0:
            raise StudyError("Shared budget exhausted before the remaining single-scientist sequences could execute.")
        allowance = (remaining_calls + remaining_sequences - 1) // remaining_sequences
        time_allowance = remaining_time / remaining_sequences
        self.start_sequence(sequence, actor)
        started_calls = self.calls
        self.sequence_request_end = self.calls + allowance
        self.sequence_deadline = time.monotonic() + time_allowance
        self.event({"kind": "sequence_allowance", "request_allowance": allowance, "time_allowance_seconds": time_allowance})
        reason = "request_allowance"
        try:
            # Each successful pass must consume a request. The loop is finite even for a broken worker.
            for step in range(1, allowance + 1):
                if self.calls >= self.sequence_request_end:
                    break
                if time.monotonic() >= self.sequence_deadline:
                    reason = "time_allowance"
                    break
                before = self.calls
                try:
                    result = await self.scientist_pass(sequence, step, actor)
                except SequenceBudgetReached as boundary:
                    reason = str(boundary)
                    self.event({"kind": "pass_limit_reached", "status": "budget_exhausted", "stop_reason": reason})
                    break
                self.outputs.append(result)
                if self.calls == before:
                    raise StudyError("Single-scientist budget pass made no request; refusing to spin.")
        finally:
            self.sequence_request_end = self.sequence_deadline = None
        self.finish_sequence(sequence, reason)
        self.summary["sequence_results"][-1].update(request_allowance=allowance, requests_used=self.calls-started_calls,
                                                    time_allowance_seconds=time_allowance)
        return {}  # Successful passes were retained individually, including before a later failure.

    async def before_wave(self, nodes):
        """Optional local extension boundary; ordinary Labtune has no extra behavior."""

    async def after_wave(self, nodes, outputs):
        """Publish optional local extension state only at the dependency-wave barrier."""

    async def run_graph(self):
        nodes=self.plan["work_graph"]
        pending={node["id"]:node for node in nodes}
        known=set(pending)
        if len(pending)!=len(nodes) or any(set(n["depends_on"])-known for n in nodes):
            raise StudyError("Invalid workflow dependencies.")
        # Validate the entire graph before any model or scientific request.
        remaining,seen=dict(pending),set()
        while remaining:
            available=[key for key,node in remaining.items() if set(node["depends_on"])<=seen]
            if not available:
                raise StudyError("Workflow contains a dependency cycle.")
            seen.update(available)
            for key in available:
                del remaining[key]
        completed=set()
        while pending:
            ready=[node for node in pending.values() if set(node["depends_on"])<=completed]
            if not ready:
                raise StudyError("Workflow contains a dependency cycle.")
            await self.before_wave(ready)
            jobs=[]
            for node in ready:
                if node["kind"] in {"qualification","verification"}:
                    if self.research is not None and node["kind"]=="qualification":
                        self.event({"kind":"domain_qualified","node":node["id"],
                                    "source_ref":str(self.workspace/"setup/research_qualification/current.json")})
                    else:
                        self.event({"kind":"domain_step_pending","node":node["id"],"status":"not_evaluated",
                                    "reason":"confirmation is deferred until all agent work ends" if self.research else "text-only"})
                    continue
                if node["kind"]=="unbound_extension":
                    raise StudyError("Custom procedure requires a runtime binding: "+node["id"])
                if node["research_activity"]=="operational_only":
                    self.event({"kind":"operational_coordination","node":node["id"],"peer_research_exchanged":False})
                    continue
                jobs.extend((node,actor) for actor in node["actors"])
            wave_outputs=[]
            width=self.plan["resources"]["max_active_agents"]
            while jobs:
                batch,rest,actors=[],[],set()
                for node,actor in jobs:
                    if len(batch)<width and actor not in actors:
                        batch.append((node,actor)); actors.add(actor)
                    else:
                        rest.append((node,actor))
                jobs=rest
                results=await asyncio.gather(*[
                    self.run_node_episode(node,actor)
                    for node,actor in batch],return_exceptions=True)
                for result in results:
                    if isinstance(result,BaseException):
                        raise result
                    if "output" in result:
                        wave_outputs.append(result)
            # A dependency wave sees one prior snapshot, regardless of finish order or resource width.
            await self.after_wave(ready, wave_outputs)
            self.outputs.extend(wave_outputs)
            for node in ready:
                self.event({"kind":"phase_completed","node":node["id"],"actors":node["actors"]})
                completed.add(node["id"])
                del pending[node["id"]]

    async def finalize_research(self, *, confirm=True):
        if self.research is None:
            return
        if confirm and self.summary["status"] == "completed_text_workflow":
            node_token = NODE.set(CONFIRMATION_NODE)
            actor_token = ACTOR.set({"id": "system:verification", "team": "system", "episode": "confirmation"})
            try:
                with self.activity("confirmation"):
                    await self.research.complete()
            finally:
                ACTOR.reset(actor_token)
                NODE.reset(node_token)
            self.summary["status"] = "completed_research_pilot"
        research_summary = self.research.finalize()
        self.summary["research"] = research_summary
        self.summary["verification_status"] = (
            "confirmation_evaluated_exploratory" if research_summary["confirmation_metrics"] else "no_valid_confirmation")

    async def run(self, *, finalize=True):
        self.summary["status"] = "running"
        self.heartbeat()
        pulse = asyncio.create_task(self.pulse())
        try:
            self.event({"kind": "trial_started"})
            await self.run_graph()
            save(self.root / "outputs.json", self.clean(self.outputs))
            self.summary["status"] = "completed_text_workflow"
        except (StudyError, ProviderError, ResearchError) as error:
            self.summary.update(status="failed_or_incomplete", error=self.clean(str(error)),
                                error_kind=getattr(error, "kind", "workflow"))
            save(self.root / "outputs.partial.json", self.clean(self.outputs))
        except BaseException as error:
            self.summary.update(status="cancelled" if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt))
                                else "failed_or_incomplete", error_kind="interrupted")
            raise
        finally:
            try:
                if finalize:
                    await self.finalize_research()
            except (ResearchError, OSError, ValueError) as error:
                self.summary["status"]="failed_or_incomplete"
                self.summary["verification_status"]="not_evaluated"
                self.summary["error"]=self.clean(str(error))
            except BaseException as error:
                self.summary["status"] = "cancelled" if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)) else "failed_or_incomplete"
                raise
            finally:
                pulse.cancel()
                await asyncio.gather(pulse, return_exceptions=True)
                self.event({"kind": "trial_finished", "status": self.summary["status"]})
                self.summary.update(finished_at=timestamp(), elapsed_seconds=time.monotonic()-self.started,
                                    provider_post_requests=self.calls, usage=self.usage, decision_usage=self.decision_usage,
                                    event_count=self.events, output_count=len(self.outputs))
                save(self.root / "summary.json", self.clean(self.summary))
                self.heartbeat()
        return self.summary


async def run_variant(project, workspace, variant, *, persistence=None, sequences=None, effort_mode=None, sequence_context=None):
    config = load_study(workspace)
    resolved = plans(project, config, workspace=workspace, variant_id=variant, persistence=persistence, sequences=sequences,
                     effort_mode=effort_mode, sequence_context=sequence_context)
    if variant not in resolved:
        raise StudyError("Unknown variant; inspect study prepare.")
    if any(value is not None for value in (persistence, sequences, effort_mode, sequence_context)):
        for row in config["variants"]:
            if row["id"] == variant:
                row["overrides"] = merge(row["overrides"], {"single_scientist":
                    resolved[variant]["configuration_snapshot"]["resolved_config"]["single_scientist"]})
    problem = project_file(workspace, config["problem_file"]).read_text()
    if not problem.strip() or "AWAITING_USER_PROBLEM" in problem:
        raise StudyError("Research problem not supplied. No research or model calls started.")
    require_configured(config["provider"])
    chosen = resolved[variant]
    if chosen["decision_service"]["mode"] != "llm_only":
        require_configured(chosen["decision_service"]["provider"])
    key = api_key(workspace, config["provider"])
    import fcntl
    with (workspace / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StudyError("Another run owns this workspace.") from None
        return await TextStudy(project, workspace, config, resolved[variant], variant, key).run()


def compare(workspace):
    config = load_study(workspace)
    rows = []
    for path in sorted((workspace/"trials").glob("*/summary.json")):
        summary = json.loads(path.read_text())
        saved=path.parent/"study_config.json"
        if saved.is_file() and json.loads(saved.read_text()).get("name")!=config["name"]:
            continue
        row = {key: summary.get(key) for key in ("trial_id", "variant", "status", "verification_status", "elapsed_seconds", "provider_post_requests", "output_count", "configuration_snapshot_id")}
        execution = summary.get("execution") or {}
        if execution.get("kind") == "single_scientist":
            progress = summary.get("sequence_progress") or {}
            row.update(scientist_persistence=execution["persistence"], scientist_effort_mode=execution["effort_mode"],
                       scientist_sequences=execution["sequences"], scientist_context_policy=execution["context_policy"],
                       scientist_sequences_completed=progress.get("completed_sequences", 0),
                       scientist_passes_completed=progress.get("completed_passes", 0))
        if execution.get("kind") == "multi_lab":
            saved_plan = json.loads((path.parent / "plan.json").read_text())
            row.update(lab_count=execution["lab_count"], lab_sequences=execution["sequences"],
                       lab_sequences_completed=(summary.get("sequence_progress") or {}).get("completed_sequences", 0),
                       lab_meeting=execution["meeting"], lab_sharing=saved_plan["communication"]["effective_profile"])
        usage = summary.get("usage") or {}
        row.update({name: usage.get(name, 0) for name in (
            "chat_input_tokens", "chat_output_tokens", "decision_input_tokens",
            "decision_output_tokens", "missing_usage_receipts")})
        row["measurement_source"] = ""
        if (path.parent/"measurements.json").exists():
            data = json.loads((path.parent/"measurements.json").read_text())
            mapping(data, {"metrics", "source_refs"}, "measurements")
            if not isinstance(data["metrics"], dict) or not isinstance(data["source_refs"], list) or not data["source_refs"] or not all(isinstance(v, str) and v for v in data["source_refs"]):
                raise StudyError("Measurements require a metrics mapping and nonempty source references.")
            for name, value in data["metrics"].items():
                if name not in config["runtime"]["comparison_metrics"] or isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise StudyError("Unexpected/nonnumeric comparison metric.")
            json.dumps(data, allow_nan=False)
            row.update(data["metrics"])
            row["measurement_source"] = " | ".join(data["source_refs"])
        rows.append(row)
    columns = ["trial_id", "variant", "status", "verification_status", "elapsed_seconds", "provider_post_requests", "output_count",
               "configuration_snapshot_id", *SCIENTIST_COMPARISON_FIELDS, *MULTI_LAB_COMPARISON_FIELDS,
               "chat_input_tokens", "chat_output_tokens", "decision_input_tokens",
               "decision_output_tokens", "missing_usage_receipts",
               *config["runtime"]["comparison_metrics"], "measurement_source"]
    folder = workspace/"comparisons"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/"trials.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("'"+v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v) for k, v in row.items()})
    report = {"generated_at": timestamp(), "study_name":config["name"], "trials": rows, "automatic_winner": None,
              "statistical_analysis": "not_run", "reason": "No automatic ranking or fabricated quality scores.",
              "declared_metrics": config["runtime"]["comparison_metrics"]}
    save(folder/"summary.json", report)
    lines = ["# User-run configuration comparison", "", "No automatic winner or statistical result is inferred.", "",
             "| Trial | Variant | Status | Verified | Requests | Seconds |",
             "|---|---|---|---|---:|---:|"]
    for row in rows:
        lines.append("| ["+row["trial_id"]+"](../trials/"+row["trial_id"]+"/) | "+str(row["variant"])+" | "+
                     str(row["status"])+" | "+str(row["verification_status"])+" | "+str(row["provider_post_requests"])+
                     " | "+str(round(row["elapsed_seconds"] or 0, 3))+" |")
    (folder/"README.md").write_text("\n".join(lines)+"\n")
    return {"status": "comparison_saved", "trials": len(rows), "folder": str(folder), "automatic_winner": None}


def command(project, workspace, operation, *, live=False, variant=None, persistence=None, sequences=None,
            effort_mode=None, sequence_context=None, multi_lab=False):
    project, workspace = project.resolve(), workspace.resolve()
    if multi_lab:
        from .multi_lab import compile_multi_lab, run_multi_lab
        if variant is not None or persistence is not None or effort_mode is not None:
            raise StudyError("Multi-lab selects per-lab variants and effort settings from study.yaml.")
        if operation == "prepare":
            plan = compile_multi_lab(project, load_study(workspace), workspace=workspace, sequences=sequences, sequence_context=sequence_context)
            save(workspace / "plans/multi-lab.json", plan)
            return {"status": "prepared", "variant": "multi-lab", "labs": [lab["id"] for lab in plan["multi_lab"]["labs"]],
                    "sequences": plan["execution"]["sequences"], "meeting": plan["execution"]["meeting"], "api_calls": 0,
                    "research_started": False, "plan": str(workspace / "plans/multi-lab.json")}
        if operation == "run":
            return asyncio.run(run_multi_lab(project, workspace, sequences=sequences, sequence_context=sequence_context))
        raise StudyError("Choose multi-lab prepare, run or visualize.")
    if operation == "prepare" and (sequences is not None or sequence_context is not None):
        raise StudyError("Prepare sequence overrides require --multi-lab; use a scientist variant for single-lab runs.")
    if operation == "qualify":
        config=load_study(workspace)
        if config["runtime"]["mode"]!="research":
            raise StudyError("Qualification requires research mode and a domain config.")
        return qualify_workspace(workspace,config["runtime"]["domain_config"])
    if operation == "prepare":
        return prepare(project, workspace)
    if operation == "doctor":
        return asyncio.run(doctor(project, workspace, live=live, variant=variant))
    if operation == "run":
        return asyncio.run(run_variant(project, workspace, variant, persistence=persistence, sequences=sequences,
                                       effort_mode=effort_mode, sequence_context=sequence_context))
    if operation == "compare":
        return compare(workspace)
    raise StudyError("Unknown study operation.")
