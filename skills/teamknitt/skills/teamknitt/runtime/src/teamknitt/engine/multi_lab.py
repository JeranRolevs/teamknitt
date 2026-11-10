"""User-configured labs, sequence barriers and filtered scientific meetings."""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import time
from uuid import uuid4

from .config import validate
from .planning import resolve_sharing
from .providers.configuration import require_configured
from .providers.http import ProviderError
from .research import ResearchError
from .sharing import filtered_view
from .study import (NODE, SequenceBudgetReached, StudyError, TextStudy, api_key,
                    load_study, plans, save, timestamp)
from .visualization import CONFIRMATION_NODE, HEARTBEAT_SECONDS, activity_metadata


def meeting_calls(settings, sharing):
    if settings["meeting"]["kind"] == "none" or not sharing["research_exchange"]:
        return 0
    return 1 + settings["meeting"]["discussion_rounds"]


def research_calls(plan):
    return sum(len(node["actors"]) for node in plan["work_graph"]
               if node["kind"] not in {"qualification", "verification"}
               and node["research_activity"] != "operational_only")


def compile_multi_lab(project, config, *, workspace=None, sequences=None, sequence_context=None):
    if "multi_lab" not in config:
        raise StudyError("Add multi_lab settings to study.yaml, or initialize the multi-lab template.")
    settings = deepcopy(config["multi_lab"])
    if sequences is not None:
        settings["sequences"] = sequences
    if sequence_context is not None:
        settings["context_policy"] = sequence_context
    validate(settings, "multi_lab.schema.json")
    # There is no natural inter-lab preset: the user supplies this policy explicitly.
    sharing = resolve_sharing({"communication": {**settings["communication"], "cadence": "sequence_boundary"}}, {})
    resolved = plans(project, config, workspace=workspace)
    labs, ids = [], set()
    for entry in settings["labs"]:
        if entry["id"] in ids or entry["variant"] not in resolved:
            raise StudyError("Multi-lab entries need unique lab IDs and existing study variants.")
        ids.add(entry["id"])
        plan = deepcopy(resolved[entry["variant"]])
        if plan["execution"].get("kind") == "single_scientist" and plan["execution"]["sequences"] != 1:
            raise StudyError("Use multi_lab.sequences for the outer sequences; each scientist variant must use sequences: 1.")
        if any(node["kind"] == "unbound_extension" for node in plan["work_graph"]):
            raise StudyError("Multi-lab execution requires bound lab procedures.")
        representative = entry.get("representative", next(p["instance_id"] for p in plan["personas"] if p["role"] == "prime"))
        if representative not in {p["instance_id"] for p in plan["personas"]}:
            raise StudyError("The meeting representative must be an existing persona in its lab.")
        minimum = research_calls(plan) + meeting_calls(settings, sharing)
        if plan["budget"]["max_llm_calls"] < minimum * settings["sequences"]:
            raise StudyError("Lab " + entry["id"] + " request budget cannot cover the minimum research and meeting calls for all sequences.")
        labs.append({**entry, "representative": representative, "plan": plan, "minimum_calls_per_sequence": minimum})
    minimum = sum(lab["minimum_calls_per_sequence"] for lab in labs) * settings["sequences"]
    if settings["budget"]["max_llm_calls"] < minimum:
        raise StudyError("The multi-lab request budget cannot cover the minimum research and meeting calls for all sequences.")
    payload = {"settings": settings, "labs": [{"id": lab["id"], "variant": lab["variant"],
                "snapshot": lab["plan"]["configuration_snapshot"]["sha256"]} for lab in labs]}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
    composite = deepcopy(labs[0]["plan"])
    composite.update(multi_lab={**settings, "labs": labs},
        design={"id": "multi_lab", "name": "Multiple labs", "file": "multi-lab",
                "governance": "user-selected independent labs", "procedure": "research, exchange and optional meeting, repeat"},
        execution={"kind": "multi_lab", "sequences": settings["sequences"], "context_policy": settings["context_policy"],
                   "lab_count": len(labs), "meeting": settings["meeting"]["kind"], "budget_scope": "all_labs_and_sequences"},
        communication=sharing,
        budget={**settings["budget"], "max_evaluations": sum(lab["plan"]["budget"]["max_evaluations"] for lab in labs),
                "confirmation_evaluations_reserved": sum(lab["plan"]["budget"]["confirmation_evaluations_reserved"] for lab in labs)},
        resources={**settings["resources"], "max_active_agents": sum(sorted(
            (lab["plan"]["resources"]["max_active_agents"] for lab in labs), reverse=True)[:settings["resources"]["max_active_labs"]])},
        decision_service={"mode": "per_lab", "specialist": None},
        personas=[{**persona, "instance_id": lab["id"] + "." + persona["instance_id"],
                   "name": lab["id"] + " / " + persona.get("name", persona["instance_id"])}
                  for lab in labs for persona in lab["plan"]["personas"]])
    approaches = {lab["plan"]["statistics"]["approach"] for lab in labs}
    composite["statistics"]["approach"] = next(iter(approaches)) if len(approaches) == 1 else "mixed"
    composite["configuration_snapshot"].update(id="config-" + fingerprint[:20], sha256=fingerprint, multi_lab=payload)
    nodes, previous = [], []
    for sequence in range(1, settings["sequences"] + 1):
        research = []
        for lab in labs:
            node = {"id": f"sequence-{sequence}:lab-{lab['id']}", "label": lab["id"] + " / " + lab["plan"]["design"]["name"],
                    "kind": "lab_research", "actors": [lab["id"] + "." + p["instance_id"] for p in lab["plan"]["personas"]],
                    "depends_on": previous[:], "sequence": sequence, "lab": lab["id"]}
            nodes.append(node)
            research.append(node["id"])
        previous = research
        if meeting_calls(settings, sharing):
            for stage in range(meeting_calls(settings, sharing)):
                current = []
                for lab in labs:
                    name = "presentation" if stage == 0 else f"discussion-{stage}"
                    identity = f"sequence-{sequence}:{name}:{lab['id']}"
                    nodes.append({"id": identity, "label": lab["id"] + " / " + name, "kind": name.split("-")[0],
                                  "actors": [lab["id"] + "." + lab["representative"]], "depends_on": previous[:],
                                  "sequence": sequence, "lab": lab["id"]})
                    current.append(identity)
                previous = current
        identity = f"sequence-{sequence}:exchange"
        nodes.append({"id": identity, "label": "Permitted lab exchange" if sharing["research_exchange"] else "Isolated sequence boundary",
                      "kind": "exchange", "actors": ["system:exchange"], "depends_on": previous[:], "sequence": sequence})
        previous = [identity]
    composite["work_graph"] = nodes
    composite["notes"] = ["No automatic lab selection, redesign or extra research sequence.",
        "Each lab retains its own history and evidence. Cross-lab content is filtered at sequence barriers.",
        "Meetings obey the inter-lab policy; none without wisdom exchanges no research and makes no meeting calls.",
        "The group request/wall limits and every lab's own limits apply, including meetings and specialist calls.",
        "Evaluation allowances remain per lab; confirmation is withheld until all sequences and meetings end."]
    return composite


class GroupLimits:
    def __init__(self, plan):
        self.calls = 0
        self.maximum = plan["budget"]["max_llm_calls"]
        self.deadline = time.monotonic() + plan["budget"]["max_wall_seconds"]
        self.llm_semaphore = asyncio.Semaphore(plan["resources"]["max_llm_requests"])
        self.generation_semaphore = asyncio.Semaphore(plan["generation_provider"]["max_parallel_requests"])
        self.decision_semaphores = {}
        self.experiment_semaphore = asyncio.Semaphore(plan["resources"]["max_experiments"])

    def reserve_request(self):
        if self.calls >= self.maximum or time.monotonic() >= self.deadline:
            raise StudyError("Multi-lab shared request or wall-time budget exhausted.")
        self.calls += 1
        return self.deadline - time.monotonic()


class LabLimits:
    def __init__(self, group, plan):
        self.group, self.study, self.request_end = group, None, None
        self.llm_semaphore = CombinedSemaphore(asyncio.Semaphore(plan["resources"]["max_llm_requests"]), group.llm_semaphore)

    def remaining_requests(self):
        remaining = self.group.maximum - self.group.calls
        return min(remaining, max(0, self.request_end - self.study.calls)) if self.request_end is not None else remaining

    def remaining_time(self):
        return self.group.deadline - time.monotonic()

    def reserve_request(self):
        if self.request_end is not None and self.study.calls >= self.request_end:
            raise SequenceBudgetReached("request_allowance")
        return self.group.reserve_request()


class CombinedSemaphore:
    """Acquire both the lab and group experiment slots without replacing either cap."""
    def __init__(self, local, shared):
        self.local, self.shared = local, shared
        self.stacks = {}

    async def __aenter__(self):
        stack = AsyncExitStack()
        try:
            await stack.enter_async_context(self.local)
            await stack.enter_async_context(self.shared)
        except BaseException:
            await stack.aclose()
            raise
        self.stacks[asyncio.current_task()] = stack

    async def __aexit__(self, *args):
        return await self.stacks.pop(asyncio.current_task()).__aexit__(*args)


class MultiLabStudy:
    def __init__(self, project, workspace, config, plan, key):
        self.project, self.workspace, self.config, self.plan = project, workspace, deepcopy(config), plan
        self.config["multi_lab"] = {k: v for k, v in plan["multi_lab"].items() if k != "labs"}
        self.config["multi_lab"]["labs"] = [{k: lab[k] for k in ("id", "variant", "representative")} for lab in plan["multi_lab"]["labs"]]
        self.id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-multi-lab-" + uuid4().hex[:8]
        self.root = workspace / "trials" / self.id
        self.root.mkdir(parents=True, exist_ok=False)
        self.started, self.events, self.sequence = time.monotonic(), 0, 0
        self.limits = GroupLimits(plan)
        self.labs, self.nodes, self.cycle_outputs = {}, {}, {}
        self._secrets = {key} if key else set()
        self.progress = {"current_sequence": 0, "completed_sequences": 0, "current_pass": 0, "completed_passes": 0}
        self.summary = {"trial_id": self.id, "variant": "multi-lab", "mode": config["runtime"]["mode"],
            "status": "running", "started_at": timestamp(), "verification_status": "not_evaluated",
            "configuration_snapshot_id": plan["configuration_snapshot"]["id"], "execution": plan["execution"],
            "sequence_progress": self.progress, "sequence_results": [], "meetings": [], "labs": {},
            "quality_metrics": {}, "actual_cost": None, "automatic_winner": None, "output_count": 0}
        save(self.root / "plan.json", plan)
        save(self.root / "study_config.json", self.config)
        for lab in plan["multi_lab"]["labs"]:
            identity = lab["id"]
            limits = LabLimits(self.limits, lab["plan"])
            study = TextStudy(project, workspace, config, lab["plan"], lab["variant"], key,
                trial_root=self.root / "labs" / identity, shared_limits=limits,
                event_sink=lambda event, name=identity: self.child_event(name, event))
            limits.study = study
            study.client._provider_semaphore = CombinedSemaphore(study.client._provider_semaphore, self.limits.generation_semaphore)
            if study.specialist_client is not None:
                settings = study.decision_settings
                slots = self.limits.decision_semaphores.setdefault(settings["provider_id"], asyncio.Semaphore(settings["max_parallel_requests"]))
                study.specialist_client._provider_semaphore = CombinedSemaphore(study.specialist_client._provider_semaphore, slots)
            self._secrets.update(study._secrets)
            study.summary.update(lab_id=identity, trial_directory="labs/" + identity,
                                 group_trial_id=self.id, group_configuration_snapshot_id=plan["configuration_snapshot"]["id"])
            if study.research is not None:
                study.research.deadline = min(study.research.deadline, self.limits.deadline)
                study.research.semaphore = CombinedSemaphore(study.research.semaphore, self.limits.experiment_semaphore)
            self.labs[identity] = study
        self.settings = plan["multi_lab"]
        self.sharing = plan["communication"]
        self.write_summary()

    def clean(self, value):
        if isinstance(value, str):
            for secret in sorted(self._secrets, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {self.clean(key): self.clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        return value

    def event(self, value):
        self.events += 1
        event = activity_metadata({"time": timestamp(), **value, "seq": self.events, "sequence": self.sequence})
        for name in ("events.jsonl", "activity.jsonl"):
            with (self.root / name).open("a") as stream:
                stream.write(json.dumps(event, allow_nan=False) + "\n")

    def child_event(self, identity, event):
        if event["kind"] in {"phase_started", "phase_completed"}:
            return  # The group records the whole lab's boundary, not every inner phase as completed.
        event = deepcopy(event)
        event["kind"] = {"sequence_started": "lab_sequence_started", "sequence_finished": "lab_sequence_finished",
                         "trial_started": "lab_trial_started", "trial_finished": "lab_trial_finished"}.get(event["kind"], event["kind"])
        if event.get("actor"):
            event["actor"] = {key: identity + "." + value if value else "" for key, value in event["actor"].items()}
            if event["actor"]["id"].startswith(identity + ".system:"):
                event["actor"]["id"] = "system:" + identity + ":" + event["actor"]["id"].split("system:", 1)[1]
        event["node"] = CONFIRMATION_NODE if event["node"] == CONFIRMATION_NODE else self.nodes.get(identity, "")
        self.event(event)

    def write_summary(self):
        for study in self.labs.values():
            study.summary.update(provider_post_requests=study.calls, usage=deepcopy(study.usage))
        self.summary.update(provider_post_requests=self.limits.calls, event_count=self.events,
            elapsed_seconds=time.monotonic() - self.started, labs={name: deepcopy(study.summary) for name, study in self.labs.items()})
        usage = {}
        for study in self.labs.values():
            for name, value in study.usage.items():
                usage[name] = usage.get(name, 0) + value
        self.summary["usage"] = usage
        save(self.root / "summary.json", self.clean(self.summary))
        save(self.root / "activity-heartbeat.json", {"time": timestamp(), "status": self.summary["status"]})

    async def pulse(self):
        while True:
            self.write_summary()
            await asyncio.sleep(HEARTBEAT_SECONDS)

    async def parallel(self, operation):
        slots = asyncio.Semaphore(self.settings["resources"]["max_active_labs"])
        failed = False
        async def bounded(identity):
            nonlocal failed
            async with slots:
                if failed:
                    return None
                try:
                    return await operation(identity)
                except BaseException:
                    failed = True
                    raise
        results = await asyncio.gather(*(bounded(identity) for identity in self.labs), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result

    def view(self, recipient, rows):
        peers = [row for name, entries in rows.items() if name != recipient for row in reversed(entries)]
        valid = {ref for study in self.labs.values() if study.research is not None
                 for ref, entry in study.research.receipts.items() if entry["result"].get("status") == "valid"}
        return self.clean(filtered_view(peers, self.sharing, valid)[0])

    async def research_sequence(self, identity):
        study = self.labs[identity]
        self.nodes[identity] = f"sequence-{self.sequence}:lab-{identity}"
        self.event({"kind": "phase_started", "node": self.nodes[identity]})
        if self.sequence > 1 and self.settings["context_policy"] == "fresh_sequence":
            study.history.clear()
            study.outputs.clear()
            study.inter_lab_context = {}
        if study.progress is not None:
            study.progress.update(completed_sequences=0, current_sequence=0, current_pass=0, completed_passes=0)
            study.summary["sequence_results"] = []
        remaining = self.settings["sequences"] - self.sequence + 1
        available = study.plan["budget"]["max_llm_calls"] - study.calls - meeting_calls(self.settings, self.sharing) * remaining
        allowance = (available + remaining - 1) // remaining
        if allowance < research_calls(study.plan):
            raise StudyError("Lab " + identity + " has insufficient remaining research/meeting allowance.")
        study.shared_limits.request_end = study.calls + allowance
        before, started_calls = len(study.outputs), study.calls
        try:
            result = await study.run(finalize=False)
        finally:
            study.shared_limits.request_end = None
            self.cycle_outputs[identity] = study.outputs[before:]
            self.summary["output_count"] += len(self.cycle_outputs[identity])
        if result["status"] != "completed_text_workflow":
            raise StudyError("Lab " + identity + " did not complete its research sequence: " + str(result.get("error", result["status"])))
        self.event({"kind": "phase_completed", "node": self.nodes[identity]})
        return {"lab": identity, "requests_used": study.calls - started_calls}

    async def meeting(self):
        kind = self.settings["meeting"]["kind"]
        if kind == "none":
            return
        record = {"sequence": self.sequence, "kind": kind, "status": "operational_only", "stages": []}
        self.summary["meetings"].append(record)
        if not self.sharing["research_exchange"]:
            save(self.root / "meetings" / f"sequence-{self.sequence}.json", record)
            return
        record["status"] = "running"
        save(self.root / "meetings" / f"sequence-{self.sequence}.json", record)
        presented = {identity: [] for identity in self.labs}
        for stage in range(meeting_calls(self.settings, self.sharing)):
            name = "presentation" if stage == 0 else f"discussion-{stage}"
            # Every participant reads the same completed stage, independent of completion order.
            views = {identity: self.view(identity, presented) if stage else {} for identity in self.labs}
            contributions = {}
            async def contribute(identity):
                study = self.labs[identity]
                self.nodes[identity] = f"sequence-{self.sequence}:{name}:{identity}"
                self.event({"kind": "phase_started", "node": self.nodes[identity]})
                entry = next(lab for lab in self.settings["labs"] if lab["id"] == identity)
                actor = entry["representative"]
                valid = [ref for ref, entry in study.research.receipts.items() if entry["result"].get("status") == "valid"] if study.research is not None else ()
                own = self.clean(filtered_view(self.cycle_outputs[identity], self.sharing, valid)[0])
                task = {"meeting": kind, "stage": name, "sequence": self.sequence,
                    "own_lab_export": own, "permitted_peer_views": views[identity],
                    "instructions": "Return a final action only. Present findings with evidence limits." if stage == 0 else
                        "Return a final action only. Discuss the permitted material, disagreements and next research questions. Do not claim independent verification.",
                    "sharing_policy": self.sharing["effective_profile"]}
                token = NODE.set(self.nodes[identity])
                try:
                    result = await study.episode(actor, actor, study.roles[actor], task, tools_allowed=False)
                finally:
                    NODE.reset(token)
                if "output" not in result:
                    raise StudyError("Meeting representative could not produce a contribution.")
                contributions[identity] = result
                self.event({"kind": "phase_completed", "node": self.nodes[identity]})
            try:
                await self.parallel(contribute)
            except BaseException as error:
                record.update(status="cancelled" if isinstance(error, asyncio.CancelledError) else "failed",
                              pending_stage=name, completed_speakers=list(contributions))
                save(self.root / "meetings" / f"sequence-{self.sequence}.json", record)
                raise
            for identity, study in self.labs.items():
                self.cycle_outputs[identity].append(contributions[identity])
                presented[identity].append(contributions[identity])
                study.outputs.append(contributions[identity])
                self.summary["output_count"] += 1
            published = {identity: self.view(identity, presented) for identity in self.labs}
            record["stages"].append({"stage": name, "input_views": views, "recipient_views": published})
            save(self.root / "meetings" / f"sequence-{self.sequence}.json", record)
        record["status"] = "completed"
        save(self.root / "meetings" / f"sequence-{self.sequence}.json", record)

    async def run(self):
        pulse = asyncio.create_task(self.pulse())
        successful = False
        try:
            self.event({"kind": "trial_started"})
            for sequence in range(1, self.settings["sequences"] + 1):
                self.sequence = sequence
                self.progress["current_sequence"] = sequence
                self.event({"kind": "sequence_started", "context_reset": sequence > 1 and self.settings["context_policy"] == "fresh_sequence"})
                started = self.limits.calls
                self.cycle_outputs = {}
                await self.parallel(self.research_sequence)
                await self.meeting()
                node = f"sequence-{sequence}:exchange"
                self.event({"kind": "phase_started", "node": node})
                exchanges = {identity: self.view(identity, self.cycle_outputs) for identity in self.labs}
                for identity, study in self.labs.items():
                    study.inter_lab_context = exchanges[identity]
                save(self.root / "exchanges" / f"sequence-{sequence}.json",
                     {"sequence": sequence, "policy": self.sharing, "recipient_views": exchanges})
                self.event({"kind": "phase_completed", "node": node})
                self.progress["completed_sequences"] += 1
                self.summary["sequence_results"].append({"sequence": sequence, "requests_used": self.limits.calls - started})
                self.event({"kind": "sequence_finished", "status": "completed"})
                self.write_summary()
            successful = True
            self.summary["status"] = "completed_multi_lab_workflow"
        except (StudyError, ProviderError, ResearchError, SequenceBudgetReached) as error:
            self.summary.update(status="failed_or_incomplete", error=str(error), error_kind=getattr(error, "kind", "workflow"))
        except BaseException as error:
            self.summary.update(status="cancelled" if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)) else "failed_or_incomplete")
            raise
        finally:
            try:
                for study in self.labs.values():
                    try:
                        await study.finalize_research(confirm=successful)
                    except (ResearchError, OSError, ValueError) as error:
                        study.summary.update(status="failed_or_incomplete", verification_status="not_evaluated", error=study.clean(str(error)))
                        self.summary.update(status="failed_or_incomplete", error=self.clean(str(error)))
                    finally:
                        study.summary.update(provider_post_requests=study.calls, usage=study.usage, decision_usage=study.decision_usage,
                                             finished_at=timestamp(), event_count=study.events, output_count=len(study.outputs))
                        save(study.root / "summary.json", study.clean(study.summary))
                        save(study.root / "outputs.json", study.clean(study.outputs))
                if self.config["runtime"]["mode"] == "research":
                    self.summary["verification_status"] = "confirmation_evaluated_exploratory" if all(
                        lab.summary["verification_status"] == "confirmation_evaluated_exploratory" for lab in self.labs.values()) else "no_valid_confirmation"
            except (ResearchError, OSError, ValueError) as error:
                self.summary.update(status="failed_or_incomplete", error=str(error))
            except BaseException as error:
                self.summary["status"] = "cancelled" if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt)) else "failed_or_incomplete"
                raise
            finally:
                pulse.cancel()
                await asyncio.gather(pulse, return_exceptions=True)
                self.summary["finished_at"] = timestamp()
                self.event({"kind": "trial_finished", "status": self.summary["status"]})
                self.write_summary()
        return self.clean(self.summary)


async def run_multi_lab(project, workspace, *, sequences=None, sequence_context=None):
    config = load_study(workspace)
    plan = compile_multi_lab(project, config, workspace=workspace, sequences=sequences, sequence_context=sequence_context)
    problem = (workspace / config["problem_file"]).read_text()
    if not problem.strip() or "AWAITING_USER_PROBLEM" in problem:
        raise StudyError("Research problem not supplied. No research or model calls started.")
    require_configured(config["provider"])
    for lab in plan["multi_lab"]["labs"]:
        if lab["plan"]["decision_service"]["mode"] != "llm_only":
            require_configured(lab["plan"]["decision_service"]["provider"])
    key = api_key(workspace, config["provider"])
    import fcntl
    with (workspace / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StudyError("Another run owns this workspace.") from None
        study = MultiLabStudy(project, workspace, config, plan, key)
        return await study.run()
