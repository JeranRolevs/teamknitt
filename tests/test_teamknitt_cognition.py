"""Distributed-cognition configuration and execution. All inference is mocked or absent."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from labtune.config import ConfigurationError, parse_yaml
from labtune.study import StudyError
from teamknitt.cli import main
from teamknitt.cognition import CognitiveWorkspace
from teamknitt.config import compile_plan, digest, load, resource
from teamknitt.observatory import html, snapshot
from teamknitt.reporting import build_report, coordination_stability, plan_report
from teamknitt.runtime import run
from teamknitt.scaffold import init

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "team"
        init(self.root, template="research")
        self.c = load(self.root)

    def plan(self, c=None):
        return compile_plan(self.root, self.c if c is None else c)

    def study(self):
        return parse_yaml((self.root / "study.yaml").read_text())

    def write_study(self, study):
        (self.root / "study.yaml").write_text(json.dumps(study))

    def execute(self, c=None, **kwargs):
        info = asyncio.run(run(self.root, self.c if c is None else c, **kwargs))
        return info, build_report(Path(info["run_directory"]))


class CognitionConfigurationTests(WorkspaceCase):
    def test_baseline_is_actual_labtune_variant_not_parallel_roster_or_providers(self):
        with patch("labtune.study.ChatCompletionsClient", side_effect=AssertionError("No provider construction")):
            p = self.plan()
        self.assertEqual(p["labtune_variant"], "team")
        self.assertEqual(p["labtune_plan"]["design"]["id"], "complementary_co_leaders")
        self.assertEqual(p["provider_request_cap"], 16)
        self.assertEqual(len(p["waves"]), 6)
        self.assertEqual(len(p["configuration"]["cognition"]["roles"]), 2)
        for field in ("providers", "team", "protocol", "statistics", "budget"):
            self.assertNotIn(field, p["configuration"])
        self.assertEqual(p["api_calls"], 0)
        self.assertIsNone(p["scientific_quality_score"])

    def test_baseline_model_budget_statistics_and_delegation_remain_authoritative(self):
        s = self.study()
        s["provider"]["model"] = "user-selected-model"
        s["base_overrides"]["budget"]["max_llm_calls"] = 9
        s["base_overrides"]["teams"]["max_depth"] = 1
        s["base_overrides"]["statistics"] = {"approach": "bayesian"}
        self.write_study(s)
        p = self.plan()
        self.assertEqual(p["provider_request_cap"], 9)
        self.assertEqual(p["labtune_plan"]["generation_provider"]["model"], "user-selected-model")
        self.assertEqual(p["labtune_plan"]["statistics"]["approach"], "bayesian")
        self.assertEqual(p["labtune_plan"]["delegation"]["max_depth"], 1)

    def test_independent_alternative_is_explicit_and_has_no_peer_workspace_channel(self):
        alternate = parse_yaml((self.root / "configurations/independent-contributions.team.yaml").read_text())
        p = self.plan(alternate)
        self.assertEqual(p["labtune_variant"], "independent")
        self.assertEqual(p["labtune_plan"]["communication"]["effective_profile"], "none")
        self.assertEqual(p["configuration"]["cognition"]["task"]["structure"], "unitary")
        self.assertEqual(p["configuration"]["cognition"]["handoffs"], [])
        _, report = self.execute(alternate)
        cross = [e for e in report["events"] if e["kind"] == "representation_exposed" and e["author"] not in {e["actor"], "researcher"}]
        self.assertFalse(cross)
        self.assertEqual(report["communication"]["effective_profile"], "none")
        self.assertIsNone(report["scientific_quality_score"])

    def test_change_design_requires_explicit_role_rebinding(self):
        s = self.study()
        s["variants"][0]["overrides"]["lab"]["design_file"] = "lab_designs/B-transdisciplinary-integration.md"
        self.write_study(s)
        with self.assertRaisesRegex(ConfigurationError, "role bindings"):
            self.plan()

    def test_cognition_cannot_escalate_labtune_sharing(self):
        s = self.study()
        s["variants"][0]["overrides"]["communication"]["profile"] = "intermediate"
        self.write_study(s)
        with self.assertRaisesRegex(ConfigurationError, "high-detail"):
            self.plan()

    def test_interaction_intent_is_checked_not_a_silent_policy_override(self):
        self.c["cognition"]["task"]["interaction"] = "independent"
        with self.assertRaisesRegex(ConfigurationError, "Independent"):
            self.plan()
        self.c["cognition"]["task"]["interaction"] = "limited_exchange"
        with self.assertRaisesRegex(ConfigurationError, "Limited"):
            self.plan()

    def test_unknown_and_duplicate_actor_representation_work_references_fail(self):
        changes = [lambda c: c["cognition"]["roles"].append(deepcopy(c["cognition"]["roles"][0])),
                   lambda c: c["cognition"]["representations"][0]["readers"].append("unknown.1"),
                   lambda c: c["cognition"]["work"][0].update(phase="not_a_lab_phase"),
                   lambda c: c["cognition"]["work"][0].update(inputs=["missing"]),
                   lambda c: c["cognition"]["work"][0].update(outputs=["measurement-note"]),
                   lambda c: c["cognition"]["expertise_directory"][0].update(holders=["unknown.1"])]
        for change in changes:
            c = deepcopy(self.c)
            change(c)
            with self.subTest(change=change), self.assertRaises(ConfigurationError):
                self.plan(c)

    def test_work_dependencies_must_match_baseline_phase_order_and_be_acyclic(self):
        c = deepcopy(self.c)
        c["cognition"]["work"][0]["depends_on"] = ["joint-challenge"]
        with self.assertRaises(ConfigurationError):
            self.plan(c)
        c = deepcopy(self.c)
        c["cognition"]["work"][0]["depends_on"] = ["measure"]
        with self.assertRaisesRegex(ConfigurationError, "precede"):
            self.plan(c)

    def test_handoff_and_affordance_require_actual_role_capabilities_and_permissions(self):
        changes = [lambda c: c["cognition"]["handoffs"][0].update(consumer="mechanism_lead.1"),
                   lambda c: c["cognition"]["affordances"][0].update(capability="not_assigned"),
                   lambda c: c["cognition"]["affordances"][0].update(target="measurement-note"),
                   lambda c: c["cognition"]["handoffs"][0].update(due_phase="missing")]
        for change in changes:
            c = deepcopy(self.c)
            change(c)
            with self.assertRaises(ConfigurationError):
                self.plan(c)

    def test_sources_are_hashed_bounded_and_cannot_read_private_runtime_or_escape(self):
        p = self.plan()
        (self.root / "mission/cognition/mechanism.md").write_text("A changed researcher input.")
        q = self.plan()
        self.assertNotEqual(p["configuration_sha256"], q["configuration_sha256"])
        for path in ("../outside.md", ".env", "mission/private_splits.json"):
            c = deepcopy(self.c)
            candidate = self.root / path
            if path != "../outside.md":
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text("private")
            c["cognition"]["representations"][0]["path"] = path
            with self.assertRaises(ConfigurationError):
                self.plan(c)

    def test_optional_disturbances_are_not_a_mandatory_test_condition(self):
        self.assertEqual(self.plan()["configuration"]["dynamics"]["perturbations"], [])
        c = deepcopy(self.c)
        c["dynamics"]["perturbations"] = [{"id": "note-outage", "kind": "representation_unavailable", "representation": "mechanism-note", "at_wave": 3, "duration": 1}]
        self.assertEqual(self.plan(c)["configuration"]["dynamics"]["perturbations"][0]["at_wave"], 3)
        for field, value in (("at_wave", 6), ("representation", "missing")):
            bad = deepcopy(c)
            bad["dynamics"]["perturbations"][0][field] = value
            if field == "at_wave":
                bad["dynamics"]["perturbations"][0]["duration"] = 2
            with self.assertRaises(ConfigurationError):
                self.plan(bad)

    def test_no_hidden_budget_model_or_benchmark_protocol_fields(self):
        for key in ("providers", "budget", "protocol", "automatic_team_redesign"):
            c = deepcopy(self.c)
            c[key] = {}
            with self.assertRaises(ConfigurationError):
                self.plan(c)


class CognitiveStateTests(WorkspaceCase):
    def state(self):
        p = self.plan()
        return CognitiveWorkspace(self.root, p, lambda e: None), p

    def observe_wave(self, state, p, number):
        node_ids = p["waves"][number-1]["nodes"]
        nodes = [n for n in p["labtune_plan"]["work_graph"] if n["id"] in node_ids]
        state.begin_wave(nodes)

    def test_complementary_source_access_and_capability_conditioned_opportunities(self):
        state, p = self.state()
        self.observe_wave(state, p, 1)
        a = state.observe("mechanism_lead.1", 700)
        b = state.observe("measurement_lead.1", 700)
        self.assertEqual([r["id"] for r in a["representations"] if "content" in r], ["mechanism-source"])
        self.assertEqual([r["id"] for r in b["representations"] if "content" in r], ["measurement-source"])
        self.assertIn("externalize-explanation", state.available["mechanism_lead.1"])
        self.assertNotIn("acknowledge-measurement", state.available["mechanism_lead.1"])
        self.assertIn("not_verified_expertise", a["expertise_status"])

    def test_publication_requires_seen_provenance_and_available_operation(self):
        state, p = self.state()
        self.observe_wave(state, p, 1)
        frame = state.observe("mechanism_lead.1", 700)
        ref = next(r for r in frame["representations"] if r["id"] == "mechanism-source")
        pub = {"affordance": "externalize-explanation", "representation": "mechanism-note", "summary": "Summary", "content": "Content",
               "uses": [{"representation": "mechanism-source", "version": ref["version"]}]}
        state.validate_output("mechanism_lead.1", {"publications": [pub]})
        bad = deepcopy(pub)
        bad["uses"][0]["version"] = "unseen"
        with self.assertRaises(StudyError):
            state.validate_output("mechanism_lead.1", {"publications": [bad]})
        bad = deepcopy(pub)
        bad["uses"] = []
        with self.assertRaises(StudyError):
            state.validate_output("mechanism_lead.1", {"publications": [bad]})
        bad = deepcopy(pub)
        bad["representation"] = "measurement-note"
        with self.assertRaises(StudyError):
            state.validate_output("mechanism_lead.1", {"publications": [bad]})

    def test_wave_publications_do_not_leak_and_validate_atomically(self):
        state, p = self.state()
        self.observe_wave(state, p, 1)
        frame = state.observe("mechanism_lead.1", 700)
        before = state.observe("measurement_lead.1", 700)
        ref = next(r for r in frame["representations"] if "version" in r)
        pub = {"affordance": "externalize-explanation", "representation": "mechanism-note", "summary": "Summary", "content": "Shared note",
               "uses": [{"representation": ref["id"], "version": ref["version"]}]}
        self.assertFalse(any(r.get("id") == "mechanism-note" and "content" in r for r in before["representations"]))
        outputs = [{"actor": "mechanism_lead.1", "output": {"cognition": {"publications": [pub]}}},
                   {"actor": "measurement_lead.1", "output": {"cognition": {"unknown": True}}}]
        with self.assertRaises(StudyError):
            state.finish_wave(outputs)
        self.assertEqual(state.versions["mechanism-note"], [])
        state.finish_wave(outputs[:1])
        self.assertEqual(state.versions["mechanism-note"][0]["version"], "v0001")
        self.assertNotIn(("mechanism-note", "v0001"), state.observed["measurement_lead.1"])

    def test_source_change_between_plan_and_initialization_fails_before_calls(self):
        p = self.plan()
        (self.root / "mission/cognition/mechanism.md").write_text("Changed")
        with self.assertRaisesRegex(ConfigurationError, "changed after planning"):
            CognitiveWorkspace(self.root, p, lambda e: None)

    def test_representation_outage_blocks_new_exposure_without_erasing_history(self):
        self.c["dynamics"]["perturbations"] = [{"id": "source-outage", "kind": "representation_unavailable", "representation": "mechanism-source", "at_wave": 2, "duration": 1}]
        state, p = self.state()
        self.observe_wave(state, p, 1)
        state.observe("mechanism_lead.1", 700)
        prior = state.observed["mechanism_lead.1"].copy()
        self.observe_wave(state, p, 2)
        f = state.observe("mechanism_lead.1", 700)
        self.assertTrue(prior <= state.observed["mechanism_lead.1"])
        self.assertFalse(any(r["id"] == "mechanism-source" and "content" in r for r in f["representations"]))
        self.assertNotIn("externalize-explanation", state.available["mechanism_lead.1"])

    def test_malformed_cognitive_fields_fail_as_protocol_errors(self):
        state, p = self.state()
        self.observe_wave(state, p, 1)
        state.observe("mechanism_lead.1", 700)
        for value in ({"publications": "not a list"}, {"temporal_model": {"order": [], "deadline_wave": True, "perceived_in_sync": True}}, {"noticed_affordances": [[]]}):
            with self.assertRaises(StudyError):
                state.validate_output("mechanism_lead.1", value)


class CognitionExecutionTests(WorkspaceCase):
    def test_connected_fixture_uses_actual_labtune_graph_without_model_calls_or_scores(self):
        with patch("labtune.study.client_for", side_effect=AssertionError("No provider construction")):
            info, report = self.execute()
        self.assertEqual(info["status"], "completed_text_workflow")
        self.assertEqual(info["provider_requests"], 0)
        self.assertEqual(info["mode"], "offline_fixture")
        self.assertIsNone(report["scientific_quality_score"])
        self.assertEqual(len(report["snapshots"]), 6)
        self.assertEqual(report["snapshots"][-1]["reported_plan_pair_agreement"], 1)
        self.assertTrue(all(h["acknowledged_on_time"] for h in report["handoffs"]))
        self.assertNotIn("scores", report)
        self.assertNotIn("subject", report["cognition"])
        self.assertIn("complementary_co_leaders", json.dumps(report["design"]))

    def test_fragmented_fixture_separates_perception_from_explicit_plan_disagreement(self):
        _, report = self.execute(policy="fragmented")
        last = report["snapshots"][-1]
        self.assertEqual(last["reported_plan_pair_agreement"], 0)
        self.assertEqual(last["perceived_in_sync_reports"], 2)
        self.assertEqual(len(last["perceived_in_sync_despite_reported_disagreement"]), 2)
        self.assertEqual(last["reported_plans_matching_reference"], 1)
        self.assertTrue(all(not h["acknowledged"] for h in report["handoffs"]))

    def test_late_handoff_does_not_count_as_on_time_or_trigger_role_substitution(self):
        self.c["dynamics"]["perturbations"] = [{"id": "absent", "kind": "actor_unavailable", "actor": "measurement_lead.1", "at_wave": 4, "duration": 1}]
        _, report = self.execute()
        h = next(h for h in report["handoffs"] if h["consumer"] == "measurement_lead.1")
        self.assertEqual(h["status"], "acknowledged_late")
        self.assertFalse(h["acknowledged_on_time"])
        self.assertTrue(report["skipped_episodes"])
        self.assertEqual(report["personas"], self.plan()["labtune_plan"]["personas"])

    def test_partial_exposure_and_no_second_cross_role_sharing_budget(self):
        s = self.study()
        s["base_overrides"]["communication"] = {"max_read_words": 8}
        self.write_study(s)
        _, report = self.execute()
        events = [e for e in report["events"] if e["kind"] == "representation_exposed" and e["author"] not in {e["actor"], "researcher"}]
        self.assertTrue(all(e["words"] <= 8 for e in events))

    def test_live_requires_both_gates_configured_provider_and_user_mission(self):
        for kwargs in ({"live": True}, {"live": True, "approve_requests": 17}, {"live": True, "approve_requests": 16}):
            with self.assertRaises(Exception):
                asyncio.run(run(self.root, self.c, **kwargs))
        self.assertFalse((self.root / "trials").exists())

    def test_actual_generation_adapter_uses_inherited_budget_and_no_cognition_judge(self):
        s = self.study()
        s["provider"].update(model="local-mock", base_url="http://127.0.0.1:1", api_key_env=None)
        self.write_study(s)
        (self.root / "mission/problem.md").write_text("User-selected local mock research task.")
        calls = []
        def transport(method, path, body):
            calls.append(body)
            return {"choices": [{"message": {"content": json.dumps({"action": "final", "summary": "No scientific result", "candidate_output": "Mock proposal", "findings": [], "wisdom": []})}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        info, report = self.execute(live=True, approve_requests=16, transport=transport)
        self.assertEqual(info["provider_requests"], 8)
        self.assertEqual(len(calls), 8)
        self.assertEqual(report["usage"]["chat_input_tokens"], 80)
        self.assertEqual(report["snapshots"][-1]["temporal_reports"], 0)
        self.assertIsNone(report["snapshots"][-1]["reported_plan_pair_agreement"])
        self.assertTrue(all(h["status"] == "missing_at_deadline" for h in report["handoffs"]))
        self.assertIsNone(report["scientific_quality_score"])

    def test_workspace_lock_remains_shared_with_original_labtune(self):
        import fcntl
        with (self.root / ".run.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(StudyError, "Another run"):
                asyncio.run(run(self.root, self.c))
        self.assertFalse(any((self.root / "trials").iterdir()))

    def test_blank_live_mission_retains_original_labtune_precondition(self):
        s = self.study()
        s["provider"].update(model="local-mock", base_url="http://127.0.0.1:1", api_key_env=None)
        self.write_study(s)
        (self.root / "mission/problem.md").write_text("  ")
        with self.assertRaises(ConfigurationError):
            asyncio.run(run(self.root, self.c, live=True, approve_requests=16))

    def test_resource_width_one_still_has_frozen_representation_visibility(self):
        s = self.study()
        s["base_overrides"]["resources"] = {"max_active_agents": 1}
        self.write_study(s)
        _, report = self.execute()
        early = [e for e in report["events"] if e["wave"] == 2 and e["kind"] == "representation_exposed"]
        self.assertTrue(early)
        self.assertTrue(all(e["author"] == "researcher" for e in early))
        self.assertEqual(report["snapshots"][1]["published_versions"], 2)

    def test_inherited_request_cap_is_enforced_without_a_second_cognition_allowance(self):
        s = self.study()
        s["provider"].update(model="local-mock", base_url="http://127.0.0.1:1", api_key_env=None)
        s["base_overrides"]["budget"]["max_llm_calls"] = 1
        self.write_study(s)
        (self.root / "mission/problem.md").write_text("User-selected research task for a mock cap test.")
        calls = []
        def transport(method, path, body):
            calls.append(body)
            return {"choices": [{"message": {"content": json.dumps({"action": "final", "summary": "Mock", "candidate_output": "Unevaluated", "findings": [], "wisdom": []})}}]}
        info, report = self.execute(live=True, approve_requests=1, transport=transport)
        self.assertEqual(info["status"], "failed_or_incomplete")
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["usage"]["provider_requests"], 1)
        self.assertEqual(report["budget"]["max_llm_calls"], 1)
        self.assertIsNone(report["scientific_quality_score"])

    def test_invalid_cognitive_claim_is_not_published_as_valid_process_evidence(self):
        from teamknitt.runtime import FixtureClient
        original = FixtureClient.generate
        async def invalid(client, *args, **kwargs):
            reply = await original(client, *args, **kwargs)
            action = json.loads(reply["content"])
            if action["cognition"].get("publications"):
                action["cognition"]["publications"][0]["uses"][0]["version"] = "unexposed"
            reply["content"] = json.dumps(action)
            return reply
        with patch.object(FixtureClient, "generate", invalid):
            info, report = self.execute()
        self.assertEqual(info["status"], "failed_or_incomplete")
        self.assertFalse(any(v["author"] != "researcher" for v in report["versions"]))

    def test_metadata_report_omits_source_and_generated_note_text(self):
        info, report = self.execute()
        blob = json.dumps(report)
        self.assertNotIn("An elegant account is not evidence", blob)
        self.assertNotIn('"content":', blob)
        self.assertNotIn('"summary":', blob)
        self.assertTrue((Path(info["run_directory"]) / "cognition-state.json").is_file())


class CognitionReportingAndPortabilityTests(WorkspaceCase):
    def test_reference_conformity_is_not_equated_with_member_similarity(self):
        from teamknitt.cognition import CognitiveWorkspace
        p = self.plan()
        state = CognitiveWorkspace(self.root, p, lambda e: None)
        wrong = {"order": ["verification"], "deadline_wave": 1, "perceived_in_sync": True}
        state.models = {r["actor"]: deepcopy(wrong) for r in self.c["cognition"]["roles"]}
        s = state.snapshot()
        self.assertEqual(s["reported_plan_pair_agreement"], 1)
        self.assertEqual(s["reported_plans_matching_reference"], 0)

    def test_stability_uses_declared_span_without_inventing_attractor_or_baseline(self):
        snapshots = [{"wave": i, "handoff_coordination_ready": value} for i,value in enumerate([True,True,False,False,True,True],1)]
        d = {"stable_waves": 2, "perturbations": [{"id": "out", "at_wave": 3, "duration": 1}]}
        r = coordination_stability(snapshots, d)
        self.assertEqual(r["perturbation_observations"][0]["return_delay_waves"], 2)
        r = coordination_stability(snapshots[:-1], d)
        self.assertEqual(r["perturbation_observations"][0]["status"], "right_censored")
        snapshots[0]["handoff_coordination_ready"] = False
        r = coordination_stability(snapshots,d)
        self.assertEqual(r["perturbation_observations"][0]["status"], "baseline_not_established")

    def test_configuration_view_exists_before_any_execution_and_html_is_safe(self):
        report = plan_report(self.plan())
        self.assertEqual(report["status"], "planned_not_executed")
        self.assertEqual(report["usage"]["provider_requests"], 0)
        report["name"] = '</script><script>alert("bad")</script>'
        page = html(report)
        self.assertNotIn(report["name"], page)
        self.assertIn('\\u003c/script\\u003e', page)
        self.assertIn('Foundations and Theoretical Perspectives', page)
        path = self.root / "view.teamknitt.html"
        snapshot(report, path)
        with self.assertRaises(FileExistsError):
            snapshot(report, path)

    def test_primary_starter_and_notices_are_synchronized_and_no_extra_provider_key(self):
        self.assertEqual((self.root / "team.yaml").read_bytes(), (ROOT / "examples/research_cognition/team.yaml").read_bytes())
        self.assertEqual((self.root / "study.yaml").read_bytes(), (ROOT / "examples/research_cognition/study.yaml").read_bytes())
        self.assertEqual((self.root / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        self.assertEqual((self.root / "LICENSING.md").read_bytes(), (ROOT / "LICENSING.md").read_bytes())
        self.assertNotIn("TEAMKNITT_API_KEY", (self.root / ".env.example").read_text())
        self.assertTrue((self.root / "mission/cognition/mechanism.md").is_file())
        with self.assertRaises(ConfigurationError):
            init(self.root, template="research")

    def test_inspector_js_parses_and_primary_view_has_no_eight_lens_score(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node syntax check is optional.")
        text = resource("observatory.html").read_text()
        self.assertNotIn("Eight lenses", text)
        self.assertNotIn("overall_score", text)
        for script in re.findall(r"<script>([\s\S]*?)</script>", text):
            result = subprocess.run([node, "-e", "new Function("+json.dumps(script)+");"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_preparation_is_offline_and_live_run_is_opt_in(self):
        with patch("labtune.study.ChatCompletionsClient", side_effect=AssertionError("No provider")), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["check", "--workspace", str(self.root)]), 0)
            self.assertEqual(main(["prepare", "--workspace", str(self.root)]), 0)
            self.assertEqual(main(["run", "--workspace", str(self.root)]), 2)
        self.assertFalse((self.root / "trials").exists())
        self.assertTrue((self.root / "plans/teamknitt.json").exists())


if __name__ == "__main__":
    unittest.main()
