"""Multi-lab boundaries, meetings, persistent context and shared caps; fake services only."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from teamknitt.engine.cli import main
from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.multi_lab import CombinedSemaphore, MultiLabStudy, compile_multi_lab, run_multi_lab
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.research import ResearchError
from teamknitt.engine.scaffold import init_workspace
from teamknitt.engine.study import StudyError, compare, load_study
from teamknitt.engine.visualization import VisualizationSession
import test_providers as fixtures

PROJECT = fixtures.PROJECT


def config_for_tests():
    config = fixtures.fixture_config()
    config["base_overrides"].update(
        budget={"max_llm_calls": 40, "max_wall_seconds": 60},
        teams={"max_depth": 0, "max_children_per_agent": 0, "max_active_descendants": 0},
        resources={"max_active_agents": 1, "max_llm_requests": 1})
    config["variants"] = [{"id": "solo", "overrides": {
        "lab": {"design_file": "lab_designs/F-single-scientist.md"},
        "single_scientist": {"persistence": "low", "sequences": 1, "effort_mode": "fixed_passes", "context_policy": "continue"}}}]
    config["multi_lab"] = {
        "labs": [{"id": "alpha", "variant": "solo"}, {"id": "beta", "variant": "solo"}],
        "sequences": 2, "context_policy": "continue",
        "communication": {"profile": "high", "wisdom": False, "max_read_words": 700},
        "meeting": {"kind": "none", "discussion_rounds": 0},
        "budget": {"max_llm_calls": 80, "max_wall_seconds": 60},
        "resources": {"max_active_labs": 2, "max_llm_requests": 2, "max_experiments": 1}}
    return config


class MultiLabTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "mission").mkdir()
        (self.root / "mission/problem.md").write_text("A bounded offline test mission.")
        self.config = config_for_tests()

    def save_config(self):
        (self.root / "study.yaml").write_text(json.dumps(self.config))

    def study(self, *, meeting="none", profile="high", wisdom=False, sequences=2):
        group = self.config["multi_lab"]
        group.update(sequences=sequences)
        group["meeting"].update(kind=meeting, discussion_rounds=1 if meeting == "symposium" else 0)
        group["communication"].update(profile=profile, wisdom=wisdom)
        self.save_config()
        config = load_study(self.root)
        return MultiLabStudy(PROJECT, self.root, config, compile_multi_lab(PROJECT, config), fixtures.FAKE_KEY)

    def transports(self, study, *, before_reply=None):
        calls = {identity: [] for identity in study.labs}
        for identity, lab in study.labs.items():
            def transport(method, path, body, name=identity):
                messages = deepcopy(body["messages"])
                calls[name].append(messages)
                if before_reply is not None:
                    extra = before_reply(name, body, len(calls[name]))
                    if extra is not None:
                        return extra
                task = json.loads(messages[-1]["content"]).get("phase_task", {})
                stage = task.get("stage", "research") if isinstance(task, dict) else "research"
                marker = f"{name}-private-{stage}-{len(calls[name])}"
                action = {"action": "final", "summary": marker,
                    "findings": [{"kind": "proposal", "text": marker, "evidence_refs": []}],
                    "wisdom": [{"lesson": "Repeat measurements under changed conditions.", "conditions": "Uncertain evidence", "limits": "No universal conclusion", "private_extra": marker}],
                    "candidate_output": marker}
                return {"model": "fixture-chat", "choices": [{"message": {"content": json.dumps(action)}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
            lab.client._transport = transport
        return calls

    def test_same_and_different_lab_designs_are_user_selected(self):
        self.config["variants"].append({"id": "silos", "overrides": {"lab": {"design_file": "lab_designs/A-multidisciplinary-silos.md"}}})
        self.config["multi_lab"]["labs"].append({"id": "gamma", "variant": "silos"})
        plan = compile_multi_lab(PROJECT, self.config)
        self.assertEqual([lab["plan"]["design"]["id"] for lab in plan["multi_lab"]["labs"]],
                         ["single_scientist", "single_scientist", "multidisciplinary_silos"])
        self.assertEqual(plan["execution"]["lab_count"], 3)
        self.assertEqual(len({p["instance_id"] for p in plan["personas"]}), len(plan["personas"]))

    def test_invalid_configuration_is_rejected_before_credentials_or_trials(self):
        variants = []
        for count in (0, -1, True, 1.5, 1001):
            config = deepcopy(self.config)
            config["multi_lab"]["sequences"] = count
            variants.append(config)
        for change in ({"id": "alpha", "variant": "solo"}, {"id": "gamma", "variant": "missing"},
                       {"id": "../escape", "variant": "solo"}, {"id": "gamma", "variant": "solo", "representative": "unknown.1"}):
            config = deepcopy(self.config)
            config["multi_lab"]["labs"][1] = change
            variants.append(config)
        for config in variants:
            (self.root / "study.yaml").write_text(json.dumps(config))
            with self.subTest(config=config["multi_lab"]), patch("teamknitt.engine.multi_lab.api_key", side_effect=AssertionError("No key lookup")):
                with self.assertRaises((StudyError, ConfigurationError)):
                    asyncio.run(run_multi_lab(PROJECT, self.root))
        self.assertFalse((self.root / "trials").exists())

    def test_minimum_budget_includes_every_lab_sequence_and_meeting(self):
        self.config["multi_lab"]["meeting"] = {"kind": "conference", "discussion_rounds": 0}
        self.config["multi_lab"]["budget"]["max_llm_calls"] = 7  # 2 labs * 2 sequences * (research + presentation) = 8.
        with self.assertRaisesRegex(StudyError, "multi-lab request budget"):
            compile_multi_lab(PROJECT, self.config)
        self.config["multi_lab"]["budget"]["max_llm_calls"] = 80
        self.config["base_overrides"]["budget"]["max_llm_calls"] = 3
        with self.assertRaisesRegex(StudyError, "Lab alpha request budget"):
            compile_multi_lab(PROJECT, self.config)

    def test_sequences_continue_own_context_and_only_admitted_peer_material(self):
        study = self.study()
        calls = self.transports(study)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "completed_multi_lab_workflow")
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 2)
        self.assertEqual(summary["provider_post_requests"], 4)
        self.assertNotIn("beta-private", json.dumps(calls["alpha"][0]))
        self.assertIn("beta-private-research-1", json.dumps(calls["alpha"][1]))
        self.assertIn("alpha-private-research-1", json.dumps(calls["alpha"][1]))
        self.assertEqual([r["requests_used"] for r in summary["sequence_results"]], [2, 2])
        self.assertEqual(compare(self.root)["trials"], 1)
        snapshot = VisualizationSession(study.plan, self.root, "multi-lab", study.id).snapshot()
        self.assertEqual(snapshot["runtime"]["status"], "completed")
        self.assertEqual(snapshot["runtime"]["metrics"]["requests"], 4)
        self.assertEqual(snapshot["runtime"]["sequence_progress"]["completed_sequences"], 2)
        self.assertEqual(snapshot["setup"]["execution"]["kind"], "multi_lab")
        self.assertNotIn("private-research", json.dumps(snapshot))

    def test_none_keeps_labs_isolated_even_with_a_meeting_selected(self):
        study = self.study(meeting="conference", profile="none")
        calls = self.transports(study)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["provider_post_requests"], 4)
        self.assertTrue(all(row["status"] == "operational_only" for row in summary["meetings"]))
        self.assertNotIn("beta-private", json.dumps(calls["alpha"]))
        self.assertNotIn("alpha-private", json.dumps(calls["beta"]))
        self.assertEqual(study.labs["alpha"].inter_lab_context, {})

    def test_wisdom_only_never_exports_summaries_details_or_extra_fields(self):
        study = self.study(meeting="symposium", profile="wisdom_only", wisdom=True)
        calls = self.transports(study)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "completed_multi_lab_workflow")
        self.assertEqual(summary["provider_post_requests"], 12)
        self.assertEqual([stage["stage"] for stage in summary["meetings"][0]["stages"]], ["presentation", "discussion-1"])
        self.assertNotIn("beta-private", json.dumps(calls["alpha"]))
        self.assertNotIn("alpha-private", json.dumps(calls["beta"]))
        for path in [*study.root.glob("exchanges/*.json"), *study.root.glob("meetings/*.json")]:
            self.assertNotIn("private-", path.read_text())
        self.assertEqual(set(study.labs["alpha"].inter_lab_context), {"wisdom.md"})

    def test_conference_opens_with_independent_presentations_and_preserves_context(self):
        study = self.study(meeting="conference")
        calls = self.transports(study)
        result = asyncio.run(study.run())
        self.assertEqual(result["provider_post_requests"], 8)
        self.assertEqual(len(result["meetings"][0]["stages"]), 1)
        self.assertNotIn("beta-private", json.dumps(calls["alpha"][1]))
        self.assertIn("beta-private-presentation-2", json.dumps(calls["alpha"][2]))
        self.assertIn("alpha-private-presentation-2", json.dumps(calls["alpha"][2]))

    def test_fresh_sequence_resets_working_context_but_keeps_recorded_evidence(self):
        self.config["multi_lab"]["context_policy"] = "fresh_sequence"
        study = self.study()
        calls = self.transports(study)
        result = asyncio.run(study.run())
        self.assertEqual(result["sequence_progress"]["completed_sequences"], 2)
        self.assertNotIn("private-research-1", json.dumps(calls["alpha"][1]))
        self.assertEqual(len(list((study.labs["alpha"].root / "actors").rglob("*.json"))), 2)
        self.assertTrue((study.root / "exchanges/sequence-1.json").is_file())

    def test_persistent_effort_is_divided_across_outer_sequences_and_reserves_meetings(self):
        self.config["variants"][0]["overrides"]["single_scientist"].update(persistence="persistent", effort_mode="budget")
        self.config["base_overrides"]["budget"]["max_llm_calls"] = 6
        self.config["multi_lab"]["budget"]["max_llm_calls"] = 12
        study = self.study(meeting="conference")
        self.transports(study)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_multi_lab_workflow")
        self.assertEqual(result["provider_post_requests"], 12)
        self.assertEqual([r["requests_used"] for r in result["sequence_results"]], [6, 6])

    def test_failed_service_is_not_retried_and_stops_before_the_next_sequence(self):
        study = self.study(meeting="conference")
        def fail(name, body, count):
            if name == "beta":
                raise ProviderError("transport_uncertain", "Offline injected failure.")
        calls = self.transports(study, before_reply=fail)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "failed_or_incomplete")
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 0)
        self.assertEqual(len(calls["beta"]), 1)
        self.assertEqual(summary["meetings"], [])

    def test_global_caps_include_decision_calls_and_meetings(self):
        self.config["multi_lab"]["budget"]["max_llm_calls"] = 8
        study = self.study(meeting="conference")
        def decision(name, body, count):
            if name == "alpha" and count == 1:
                content = {"action": "decision.assess", "spec_id": "semantic_choice.v1", "question": {"type": "noul", "instructions": "Is this a fixture?"}}
            elif name == "alpha" and count == 2:
                content = {"noul": .8}
            else:
                return None
            return {"choices": [{"message": {"content": json.dumps(content)}}]}
        self.transports(study, before_reply=decision)
        result = asyncio.run(study.run())
        self.assertEqual(result["provider_post_requests"], 8)
        self.assertEqual(sum(lab.calls for lab in study.labs.values()), 8)
        self.assertEqual(result["status"], "failed_or_incomplete")
        self.assertEqual(result["sequence_progress"]["completed_sequences"], 1)

    def test_global_concurrency_and_lab_concurrency_caps_apply(self):
        for limit, active_labs in ((1, 2), (2, 1), (2, 2)):
            self.config["multi_lab"]["resources"].update(max_llm_requests=limit, max_active_labs=active_labs)
            study = self.study(sequences=1)
            active = peak = 0
            lock = threading.Lock()
            barrier = threading.Barrier(2) if min(limit, active_labs) == 2 else None
            def work(*args):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                if barrier is not None:
                    barrier.wait(timeout=5)
                else:
                    time.sleep(.01)
                with lock:
                    active -= 1
            self.transports(study, before_reply=work)
            asyncio.run(study.run())
            self.assertEqual(peak, min(limit, active_labs))

    def test_sequence_overrides_change_identity_and_leave_user_configuration_untouched(self):
        before = deepcopy(self.config)
        a = compile_multi_lab(PROJECT, self.config)
        b = compile_multi_lab(PROJECT, self.config, sequences=3)
        self.assertNotEqual(a["configuration_snapshot"]["id"], b["configuration_snapshot"]["id"])
        self.assertEqual(self.config, before)

    def test_prepare_and_visualize_new_starter_need_no_provider_and_package_the_guide(self):
        root = self.root / "portable"
        with patch("teamknitt.engine.study.ChatCompletionsClient", side_effect=AssertionError("No provider")):
            init_workspace(root, "multi-lab")
            self.assertEqual(main(["--project", str(root), "study", "prepare", "--workspace", str(root), "--multi-lab"]), 0)
            self.assertEqual(main(["--project", str(root), "visualize", "--workspace", str(root), "--multi-lab", "--output", str(self.root / "labs.html")]), 0)
        self.assertTrue((root / "docs/MULTI_LAB.md").is_file())
        self.assertFalse((root / ".env").exists())
        self.assertIn("symposium", (self.root / "labs.html").read_text())

    def test_placeholders_prevent_live_run_before_credentials_and_trial_creation(self):
        self.config["provider"]["base_url"] = "https://provider.example.invalid/v1"
        self.config["provider"]["model"] = "YOUR_MODEL_ID"
        self.save_config()
        with patch("teamknitt.engine.multi_lab.api_key", side_effect=AssertionError("No credentials")):
            with self.assertRaises(ProviderError):
                asyncio.run(run_multi_lab(PROJECT, self.root))
        self.assertFalse((self.root / "trials").exists())

    def test_intermediate_views_exclude_detailed_candidates_and_bound_all_channels(self):
        study = self.study(profile="intermediate", wisdom=True)
        study.sharing["max_read_words"] = 11
        rows = {"alpha": [], "beta": [{"output": {
            "summary": "A compact reported conclusion with substantial uncertainty.",
            "findings": [{"text": "DETAILED_PRIVATE_METHOD"}], "candidate_output": "DETAILED_PRIVATE_METHOD",
            "wisdom": [{"lesson": "Inspect repeated observations.", "conditions": "Uncertainty", "limits": "Limited scope"}]}}]}
        view = study.view("alpha", rows)
        self.assertNotIn("DETAILED_PRIVATE_METHOD", json.dumps(view))
        self.assertLessEqual(sum(len(value.split()) for value in view.values()), 11)

    def test_no_meeting_can_invoke_research_tools(self):
        study = self.study(meeting="conference")
        def forbidden(name, body, count):
            task = json.loads(body["messages"][-1]["content"]).get("phase_task", {})
            if isinstance(task, dict) and task.get("meeting"):
                return {"choices": [{"message": {"content": json.dumps({"action": "experiment.run", "candidate": {}})}}]}
        self.transports(study, before_reply=forbidden)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "failed_or_incomplete")
        self.assertIn("final actions only", result["error"])
        self.assertEqual(result["sequence_progress"]["completed_sequences"], 0)
        self.assertFalse(any(study.root.rglob("experiments")))
        record = json.loads((study.root / "meetings/sequence-1.json").read_text())
        self.assertEqual(record["status"], "failed")

    def test_discussion_rounds_read_prior_stage_and_not_partial_same_round_updates(self):
        self.config["multi_lab"]["resources"]["max_active_labs"] = 1
        study = self.study(meeting="symposium", sequences=1)
        calls = self.transports(study)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_multi_lab_workflow")
        beta_task = json.loads(calls["beta"][2][-1]["content"])["phase_task"]
        self.assertIn("alpha-private-presentation-2", json.dumps(beta_task["permitted_peer_views"]))
        self.assertNotIn("alpha-private-discussion-1-3", json.dumps(beta_task["permitted_peer_views"]))

    def test_expired_global_wall_budget_dispatches_no_request(self):
        study = self.study()
        calls = self.transports(study)
        study.limits.deadline = 0
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "failed_or_incomplete")
        self.assertEqual(result["provider_post_requests"], 0)
        self.assertEqual(calls, {"alpha": [], "beta": []})

    def test_cancellation_retains_a_cancelled_summary_and_does_not_continue(self):
        study = self.study()
        async def cancel(identity):
            raise asyncio.CancelledError()
        study.research_sequence = cancel
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(study.run())
        summary = json.loads((study.root / "summary.json").read_text())
        self.assertEqual(summary["status"], "cancelled")
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 0)
        self.assertEqual(summary["provider_post_requests"], 0)

    def test_development_receipts_and_confirmation_stay_per_lab_and_after_all_meetings(self):
        self.config["runtime"].update(mode="research", domain_config="domain.yaml")
        (self.root / "domain.yaml").write_text("schema_version: 1\n")
        confirmations = []
        class Backend:
            action_contract = "Offline test evaluator."
            def __init__(backend, workspace, config_path, root, plan):
                backend.deadline = time.monotonic() + 60
                backend.semaphore = asyncio.Semaphore(1)
                backend.receipts = {}
                backend.confirmed = False
            async def complete(backend):
                confirmations.append(study.progress["completed_sequences"])
                backend.confirmed = True
                backend.receipts["protected-confirmation"] = {"result": {"status": "valid", "private_confirmation": "NEVER_TO_AGENTS"}}
            def finalize(backend):
                return {"confirmation_metrics": {"fixture": 1} if backend.confirmed else {}}
        with patch("teamknitt.engine.study.create_backend", side_effect=Backend):
            study = self.study(meeting="conference", profile="low")
        calls = self.transports(study)
        a, b = study.labs.values()
        b.research.receipts["valid-b"] = {"result": {"status": "valid"}}
        b.research.receipts["invalid-b"] = {"result": {"status": "invalid_candidate"}}
        study.cycle_outputs = {"alpha": [], "beta": [{"output": {
            "summary": "DO_NOT_SEND_SUMMARY", "candidate_output": "DO_NOT_SEND_CANDIDATE", "wisdom": [],
            "findings": [{"kind": "dead_end", "text": "Supported failed method", "evidence_refs": ["valid-b"]},
                         {"kind": "dead_end", "text": "UNSUPPORTED_CLAIM", "evidence_refs": ["invalid-b"]}]}}]}
        view = study.view("alpha", study.cycle_outputs)
        self.assertIn("Supported failed method", json.dumps(view))
        self.assertNotIn("UNSUPPORTED_CLAIM", json.dumps(view))
        self.assertNotIn("DO_NOT_SEND", json.dumps(view))
        self.assertIsNot(a.research.receipts, b.research.receipts)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_multi_lab_workflow")
        self.assertEqual(confirmations, [2, 2])
        self.assertNotIn("NEVER_TO_AGENTS", json.dumps(calls))
        self.assertEqual(result["verification_status"], "confirmation_evaluated_exploratory")

    def test_mixed_designs_execute_without_combining_agent_histories(self):
        self.config["variants"].append({"id": "silos", "overrides": {"lab": {"design_file": "lab_designs/A-multidisciplinary-silos.md"}}})
        self.config["multi_lab"]["labs"][1]["variant"] = "silos"
        study = self.study(sequences=1, profile="none")
        calls = self.transports(study)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_multi_lab_workflow")
        self.assertEqual(len(study.labs["alpha"].history), 1)
        self.assertGreater(len(study.labs["beta"].history), 1)
        self.assertNotIn("alpha-private", json.dumps(calls["beta"]))

    def test_one_confirmation_failure_does_not_discard_another_labs_finalization(self):
        study = self.study(sequences=1)
        self.transports(study)
        completed = []
        class Backend:
            def __init__(backend, identity):
                backend.identity, backend.receipts = identity, {}
            async def complete(backend):
                completed.append(backend.identity)
                if backend.identity == "alpha":
                    raise ResearchError("Injected confirmation failure")
            def finalize(backend):
                return {"confirmation_metrics": {"fixture": 1}}
        for identity, lab in study.labs.items():
            lab.research = Backend(identity)
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "failed_or_incomplete")
        self.assertEqual(completed, ["alpha", "beta"])
        self.assertEqual(result["labs"]["alpha"]["status"], "failed_or_incomplete")
        self.assertEqual(result["labs"]["beta"]["verification_status"], "confirmation_evaluated_exploratory")

    def test_queued_experiments_recheck_deadlines_before_starting_either_evaluator(self):
        from teamknitt.engine.memory import MemoryResearchBackend
        from teamknitt.engine.research import ResearchBackend
        cases = [(MemoryResearchBackend, "teamknitt.engine.memory.execute", {"name": "fixture", "source": "fixture"}),
                 (ResearchBackend, "teamknitt.engine.research.execute_job", {"statistic": "damp_raw", "reference": "growing",
                     "window": 2000, "threshold": "age_matched_rank", "gamma": 0})]
        async def exercise(kind, execute, candidate):
            backend = object.__new__(kind)
            backend.workspace, backend.root = self.root, self.root / "experiments"
            backend.plan = {"budget": {"max_evaluations": 2, "confirmation_evaluations_reserved": 0}, "statistics": {"approach": "frequentist"}}
            backend.config = {"timeout_seconds": 60}
            backend.deadline, backend.calls, backend.receipts, backend.generation_model = time.monotonic() + 60, 0, {}, "fixture"
            local, shared = asyncio.Semaphore(1), asyncio.Semaphore(0)
            backend.semaphore = CombinedSemaphore(local, shared)
            with patch(execute, side_effect=AssertionError("No evaluator may start after the queued deadline")):
                task = asyncio.create_task(backend.evaluate("actor", "team", candidate))
                await asyncio.sleep(0)
                self.assertTrue(local.locked())
                backend.deadline = 0
                shared.release()
                result = await task
                self.assertEqual(result["status"], "budget_exhausted")
                self.assertEqual(backend.calls, 0)
        for kind, execute, candidate in cases:
            with self.subTest(kind=kind.__name__):
                asyncio.run(exercise(kind, execute, candidate))

    def test_labs_share_the_generation_endpoints_configured_connection_cap(self):
        self.config["provider"]["max_parallel_requests"] = 1
        study = self.study(sequences=1)
        active = peak = 0
        lock = threading.Lock()
        def work(*args):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.01)
            with lock:
                active -= 1
        self.transports(study, before_reply=work)
        self.assertEqual(asyncio.run(study.run())["status"], "completed_multi_lab_workflow")
        self.assertEqual(peak, 1)

    def test_specialist_account_caps_and_per_lab_aggregate_request_caps_apply(self):
        self.config["base_overrides"]["decisions"].update(mode="selected_active", specialist="specialist")
        self.config["decision_providers"]["specialist"]["max_parallel_requests"] = 1
        with patch("teamknitt.engine.study.api_key", return_value=fixtures.FAKE_KEY):
            study = self.study(sequences=1)
        active = peak = 0
        lock = threading.Lock()
        def transport(method, path, body):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.01)
            with lock:
                active -= 1
            return {"model": body["model"], "answers": {"q": {"noul": .8}}, "choices": [{"message": {"content": "fixture"}}]}
        for lab in study.labs.values():
            lab.specialist_client._transport = transport
        async def specialists():
            await asyncio.gather(*(lab.specialist_client.assess_text("fixture", {"q": {"type": "noul", "instructions": "Fixture?"}}) for lab in study.labs.values()))
        asyncio.run(specialists())
        self.assertEqual(peak, 1)
        active = peak = 0
        lab = study.labs["alpha"]
        lab.client._transport = transport
        async def mixed_requests():
            await asyncio.gather(lab.client.generate([{"role": "user", "content": "fixture"}], budget_ref="fixture"),
                                 lab.specialist_client.assess_text("fixture", {"q": {"type": "noul", "instructions": "Fixture?"}}))
        # A fresh group avoids reusing contended semaphores across event loops.
        with patch("teamknitt.engine.study.api_key", return_value=fixtures.FAKE_KEY):
            second = self.study(sequences=1)
        lab = second.labs["alpha"]
        lab.client._transport = lab.specialist_client._transport = transport
        asyncio.run(mixed_requests())
        self.assertEqual(peak, 1)
