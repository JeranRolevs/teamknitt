"""Offline team protocol tests. No tests contact a paid (or other remote) provider."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.config import ConfigurationError, parse_yaml
from teamknitt.probes.actions import InvalidAction, parse_action
from teamknitt.probes.cli import main
from teamknitt.probes.config import digest, links, load, plan, resource, validate
from teamknitt.probes.metrics import dynamics, entropy
from teamknitt.probes.observatory import html, snapshot
from teamknitt.probes.policies import fixture
from teamknitt.probes.reporting import aggregate, load_run, report
from teamknitt.probes.runtime import run
from teamknitt.probes.scaffold import init
from teamknitt.probes.scenarios import suite

ROOT = Path(__file__).resolve().parents[1]


def starter():
    return validate(parse_yaml(resource("team.yaml").read_text()))


def smaller(dimension="unsafe_pressure"):
    c = starter()
    c["protocol"]["dimensions"] = [dimension]
    c["protocol"]["seeds"] = [11]
    return c


class TeamConfigTests(unittest.TestCase):
    def test_starter_and_public_example_are_identical(self):
        self.assertEqual(resource("team.yaml").read_bytes(), (ROOT / "examples/teammate_probes/team.yaml").read_bytes())
        self.assertEqual(resource("WORKSPACE.md").read_bytes(), (ROOT / "examples/teammate_probes/README.md").read_bytes())

    def test_plan_counts_and_identity_do_not_read_keys_or_construct_provider(self):
        with patch.dict(os.environ, {}, clear=True), patch("teamknitt.probes.runtime.ChatCompletionsClient", side_effect=AssertionError("No model construction")):
            p = plan(starter())
        self.assertEqual(p["provider_request_upper_bound"], 504)
        self.assertEqual(p["episode_count"], 40)
        self.assertEqual(p["output_token_upper_bound"], 504 * 700)
        self.assertEqual(p["api_calls"], 0)
        self.assertTrue(p["budget_covers_request_upper_bound"])
        c = starter()
        c["providers"]["chosen"]["model"] = "another-model"
        self.assertNotEqual(p["configuration_sha256"], plan(c)["configuration_sha256"])

    def test_small_budget_is_explicitly_insufficient_not_raised_automatically(self):
        c = starter()
        c["budget"]["max_requests"] = 1
        p = plan(c)
        self.assertFalse(p["budget_covers_request_upper_bound"])
        self.assertEqual(p["configuration"]["budget"]["max_requests"], 1)

    def test_duplicate_keys_and_nonfinite_config_are_rejected(self):
        with self.assertRaises(ConfigurationError):
            parse_yaml("name: one\nname: two")
        c = starter()
        c["budget"]["max_wall_seconds"] = float("inf")
        with self.assertRaises(ConfigurationError):
            validate(c)

    def test_invalid_roster_and_provider_cases(self):
        mutations = [
            lambda c: c["team"]["members"].append(deepcopy(c["team"]["members"][0])),
            lambda c: c["team"].update(accountable="researcher"),
            lambda c: c["team"]["members"][0].pop("provider"),
            lambda c: c["team"]["members"][2].update(provider="chosen"),
            lambda c: c["providers"].update(unused=deepcopy(c["providers"]["chosen"])),
            lambda c: c["providers"]["chosen"]["request_options"].update(api_key="no-secrets"),
            lambda c: c["providers"]["chosen"]["request_options"].update(seed=4),
            lambda c: c["providers"]["chosen"].update(api_key="no-secrets"),
            lambda c: c["providers"]["chosen"].update(base_url="http://example.com"),
            lambda c: c["protocol"].update(seeds=[1, 1]),
            lambda c: c["protocol"].update(dimensions=["unknown"]),
            lambda c: c.update(automatic_redesign=True),
        ]
        for change in mutations:
            with self.subTest(change=change):
                c = starter()
                change(c)
                with self.assertRaises(ConfigurationError):
                    validate(c)

    def test_explicit_topology_is_directed_and_validated(self):
        c = starter()
        c["communication"].update(topology="explicit", links=[{"source": "colleague", "target": "researcher"}])
        self.assertEqual(links(validate(c)), [("colleague", "researcher")])
        for extra in ({"source": "missing", "target": "researcher"}, {"source": "colleague", "target": "colleague"}, c["communication"]["links"][0]):
            bad = deepcopy(c)
            bad["communication"]["links"].append(extra)
            with self.assertRaises(ConfigurationError):
                validate(bad)

    def test_perturbation_schedules_fail_closed(self):
        mutations = [lambda c: c.update(perturbations=[]),
                     lambda c: c["perturbations"][0].update(at_round=7, duration=2),
                     lambda c: c["perturbations"][0].update(member="researcher"),
                     lambda c: c["perturbations"].append({"id": "out", "kind": "link_dropout", "source": "colleague", "target": "colleague", "at_round": 3, "duration": 1}),
                     lambda c: c["perturbations"].append(deepcopy(c["perturbations"][0]))]
        for change in mutations:
            c = starter()
            change(c)
            with self.assertRaises(ConfigurationError):
                validate(c)

    def test_fixture_generation_is_stable_under_dimension_reordering(self):
        c = starter()
        original = {s.id: s.total for s in suite(c)}
        c["protocol"]["dimensions"].reverse()
        self.assertEqual(original, {s.id: s.total for s in suite(c)})
        c["protocol"]["task_seed"] += 1
        self.assertNotEqual(original, {s.id: s.total for s in suite(c)})


class TeamActionTests(unittest.TestCase):
    def valid(self):
        return {"messages": [], "work": [], "decision": {"choice": "checked", "total": 30, "evidence": ["measurement", "reserve"]}}

    def parse(self, value):
        return parse_action(value, known={"measurement", "reserve"}, recipients={"colleague"}, limit=4)

    def test_valid_decisions_and_unseen_evidence(self):
        self.assertEqual(self.parse(self.valid())["decision"]["total"], 30)
        invalid = self.valid()
        invalid["decision"]["evidence"].append("incident")
        with self.assertRaises(InvalidAction):
            self.parse(invalid)

    def test_unknown_tools_false_success_and_nonstrict_json_are_rejected(self):
        values = ['{"messages": [], "messages": [], "work": [], "decision": null}',
                  '```json\n{"messages": [], "work": [], "decision": null}\n```',
                  {"messages": [], "work": [], "decision": None, "success": True},
                  {"messages": [], "work": [{"operation": "shell", "value": 0, "evidence": []}], "decision": None}]
        for value in values:
            with self.subTest(value=value), self.assertRaises(InvalidAction):
                self.parse(value)

    def test_malformed_unhashable_fields_are_protocol_failures_not_runtime_crashes(self):
        for field in ("to", "act"):
            value = self.valid()
            message = {"to": "colleague", "act": "inform", "content": "Text", "evidence": []}
            message[field] = []
            value["messages"] = [message]
            with self.assertRaises(InvalidAction):
                self.parse(value)
        value = self.valid()
        value["decision"]["choice"] = []
        with self.assertRaises(InvalidAction):
            self.parse(value)

    def test_nonfinite_bool_and_unsupported_work_fail_closed(self):
        for value in (True, float("nan"), "30"):
            action = self.valid()
            action["decision"]["total"] = value
            with self.assertRaises(InvalidAction):
                self.parse(action)
        action = self.valid()
        action["work"] = [{"operation": "repair", "value": 30, "evidence": ["measurement"]}]
        with self.assertRaises(InvalidAction):
            self.parse(action)


class TeamRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def execute(self, c=None, **kwargs):
        result = asyncio.run(run(self.root, c or smaller(), **kwargs))
        return load_run(Path(result["run_directory"]))

    def test_full_coordinated_and_fragile_fixtures_are_not_model_measurements(self):
        with patch("teamknitt.probes.runtime.ChatCompletionsClient", side_effect=AssertionError("No provider")):
            good = self.execute(starter())
            bad = self.execute(starter(), policy="fragile")
        self.assertEqual(report(good)["scores"]["overall_score"], 100)
        self.assertEqual(report(bad)["scores"]["overall_score"], 43.75)
        self.assertEqual(good["usage"]["provider_requests"], 0)
        self.assertEqual(good["mode"], "offline_fixture")
        self.assertIn("not model evidence", report(good)["evidence_label"])
        self.assertEqual(len(good["episodes"]), 40)
        self.assertEqual(len(good["implementation_sha256"]), 64)
        self.assertEqual(report(good)["implementation_sha256"], good["implementation_sha256"])
        self.assertEqual(report(good)["scores"]["eligible_tasks"], 8)

    def test_live_needs_two_exact_gates_and_placeholder_fails_before_any_record(self):
        c = smaller()
        with self.assertRaises(ConfigurationError):
            asyncio.run(run(self.root, c, live=True))
        with self.assertRaises(ConfigurationError):
            asyncio.run(run(self.root, c, live=True, approve_requests=1))
        with self.assertRaises(Exception):
            asyncio.run(run(self.root, c, live=True, approve_requests=c["budget"]["max_requests"]))
        self.assertFalse((self.root / "runs").exists())

    def test_frozen_round_observations_and_code_evidence_provenance(self):
        result = self.execute(smaller("information"))
        ep = next(e for e in result["episodes"] if e["condition"] == "test")
        release = next(e for e in ep["events"] if e["kind"] == "message" and e["source"] == "colleague" and "reserve" in e["evidence"])
        decision = next(e for e in ep["events"] if e["kind"] == "decision")
        self.assertGreater(decision["round"], release["round"])
        self.assertTrue(ep["outcome"]["passed"])
        self.assertGreater(release["round"], 3)
        frames = []
        from teamknitt.probes.policies import fixture as original
        def observe(frame, *args):
            frames.append(deepcopy(frame))
            return original(frame, *args)
        with patch("teamknitt.probes.runtime.fixture", side_effect=observe):
            self.execute(smaller())
        first = next(f for f in frames if f["condition"] == "baseline" and f["actor"] == "researcher" and f["round"] == 1)
        self.assertEqual([f["id"] for f in first["known_facts"]], ["measurement"])
        self.assertNotIn("reserve", [f["id"] for f in first["known_facts"]])
        self.assertEqual(first["inbox"], [])

    def test_link_outages_only_affect_challenged_deliveries(self):
        c = smaller()
        c["perturbations"].append({"id": "broken", "kind": "link_dropout", "source": "colleague", "target": "researcher", "at_round": 3, "duration": 1})
        result = self.execute(c)
        baseline = next(e for e in result["episodes"] if e["condition"] == "baseline")
        test = next(e for e in result["episodes"] if e["condition"] == "test")
        self.assertFalse(any(e["kind"] == "perturbation" for e in baseline["events"]))
        dropped = [e for e in test["events"] if e["kind"] == "message" and not e["delivered"]]
        self.assertTrue(dropped)
        self.assertTrue(all(e["drop_reason"] == "link_dropout" and e["round"] == 3 for e in dropped))
        self.assertFalse(test["outcome"]["passed"])

    def test_member_unavailable_skips_actor_and_drops_incoming(self):
        c = smaller()
        c["perturbations"].append({"id": "absent", "kind": "member_unavailable", "member": "steward", "at_round": 4, "duration": 2})
        test = next(e for e in self.execute(c)["episodes"] if e["condition"] == "test")
        self.assertFalse(any(e["kind"] == "actor_action" and e["actor"] == "steward" and e["round"] in {4, 5} for e in test["events"]))

    def test_explicit_links_do_not_imply_reverse_permission(self):
        c = smaller("information")
        c["communication"].update(topology="explicit", links=[{"source": "researcher", "target": "colleague"}])
        result = self.execute(c)
        baseline = next(e for e in result["episodes"] if e["condition"] == "baseline")
        self.assertFalse(baseline["outcome"]["passed"])
        self.assertTrue(any(e["kind"] == "message" and e["source"] == "colleague" and e["drop_reason"] == "topology" for e in baseline["events"]))

    def test_private_permissions_journal_and_report_redaction(self):
        result = self.execute()
        directory = next((self.root / "runs").iterdir())
        self.assertTrue((directory / "events.jsonl").exists())
        if os.name == "posix":
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            for file in directory.iterdir():
                self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        raw = json.dumps(result)
        self.assertIn('"content"', raw)
        self.assertNotIn('"content"', json.dumps(report(result)))
        self.assertNotIn('"value"', json.dumps(report(result)))

    def test_run_symlink_and_env_escape_are_rejected(self):
        (self.root / "runs").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ConfigurationError):
            self.execute()
        workspace = self.root / "new"
        init(workspace)
        c = starter()
        c["providers"]["chosen"]["env_file"] = "../private.env"
        (workspace / "team.yaml").write_text(json.dumps(c))
        with self.assertRaises(ConfigurationError):
            load(workspace)

    def mock_live(self, c, responder=None):
        c = deepcopy(c)
        c["providers"]["chosen"].update(base_url="http://127.0.0.1:1", model="mock-model", api_key_env="TEAMKNITT_TEST_KEY")
        cases = {s.id: s for s in suite(c)}
        calls = []
        def transport(method, path, body):
            frame = json.loads(body["messages"][-1]["content"])
            calls.append({"body": body, "frame": frame})
            if responder is not None:
                return responder(frame, cases[frame["task_id"]], c)
            action = fixture(frame, cases[frame["task_id"]], c)
            return {"model": "mock-model", "choices": [{"message": {"content": json.dumps(action)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        with patch.dict(os.environ, {"TEAMKNITT_TEST_KEY": "private-test-key"}):
            result = self.execute(c, live=True, approve_requests=c["budget"]["max_requests"], transport=transport)
        return result, calls

    def test_mock_transport_exercises_actual_provider_adapter_and_accounting(self):
        result, calls = self.mock_live(smaller())
        self.assertEqual(result["usage"]["provider_requests"], 35)
        self.assertEqual(len(calls), 35)
        self.assertEqual(result["usage"]["input_tokens"], 350)
        self.assertEqual(result["usage"]["output_tokens"], 175)
        self.assertEqual(result["usage"]["missing_usage_receipts"], 0)
        self.assertEqual(result["usage"]["returned_model_bindings"][0]["returned_model"], "mock-model")
        self.assertEqual(report(result)["scores"]["overall_score"], 100)
        self.assertTrue(all(call["body"]["seed"] == 11 for call in calls))
        self.assertNotIn("private-test-key", json.dumps(result))
        for path in (self.root / "runs").rglob("*"):
            if path.is_file():
                self.assertNotIn("private-test-key", path.read_text())

    def test_failed_reserved_requests_stop_at_cap_no_retries_and_suppress_incomplete_score(self):
        c = smaller()
        c["budget"]["max_requests"] = 3
        result, calls = self.mock_live(c)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["usage"]["provider_requests"], 3)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(report(result)["scores"]["overall_score"])
        self.assertEqual(report(result)["scores"]["missing_or_failed_episode_count"], 3)

    def test_malformed_model_output_is_an_incomplete_cell_with_missing_usage(self):
        def bad(*args):
            return {"choices": [{"message": {"content": '{"messages": [], "work": [], "decision": null, "success": true}'}}]}
        result, calls = self.mock_live(smaller(), bad)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["episodes"][0]["status"], "invalid_action")
        self.assertEqual(result["usage"]["missing_usage_receipts"], len(calls))
        self.assertIsNone(report(result)["scores"]["overall_score"])

    def test_provider_errors_are_not_behavioral_zero_and_do_not_fallback(self):
        from teamknitt.engine.providers.http import ProviderError
        def failed(*args):
            raise ProviderError("authentication", "fixture failure")
        result, calls = self.mock_live(smaller(), failed)
        self.assertEqual(len(calls), 5)  # alone wave 1, then two model members in each team wave 1
        self.assertTrue(all(e["status"] == "provider_error" for e in result["episodes"]))
        self.assertIsNone(report(result)["scores"]["overall_score"])

    def test_global_concurrency_limit_applies_to_all_model_requests(self):
        import threading
        import time
        c = smaller()
        c["budget"]["max_parallel"] = 1
        active, maximum = 0, 0
        lock = threading.Lock()
        def tracked(frame, scenario, config):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.002)
            action = fixture(frame, scenario, config)
            with lock:
                active -= 1
            return {"choices": [{"message": {"content": json.dumps(action)}}]}
        result, calls = self.mock_live(c, tracked)
        self.assertEqual(maximum, 1)
        self.assertEqual(len(calls), 35)
        self.assertEqual(result["status"], "completed")

    def test_wall_time_stops_future_calls_and_keeps_unknown_outcomes(self):
        import time
        c = smaller()
        c["budget"]["max_wall_seconds"] = .15
        def slow(frame, scenario, config):
            time.sleep(.25)
            return {"choices": [{"message": {"content": json.dumps(fixture(frame, scenario, config))}}]}
        result, calls = self.mock_live(c, slow)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["usage"]["provider_requests"], 1)
        self.assertIsNone(report(result)["scores"]["overall_score"])

    def test_direct_library_calls_cannot_escape_env_file_boundary(self):
        c = smaller()
        c["providers"]["chosen"]["env_file"] = "../outside.env"
        with self.assertRaises(ConfigurationError):
            self.execute(c)
        self.assertFalse((self.root / "runs").exists())

    def test_direct_work_must_be_correct_not_self_reported(self):
        from teamknitt.probes.policies import fixture as original
        def wrong(frame, scenario, config, policy):
            value = original(frame, scenario, config, policy)
            for work in value["work"]:
                work["value"] = -1
            return value
        with patch("teamknitt.probes.runtime.fixture", side_effect=wrong):
            result = self.execute(smaller("initiative"))
        self.assertEqual(result["episodes"][0]["outcome"]["score"], 0)
        self.assertFalse(result["episodes"][0]["outcome"]["checks"]["verified_by_subject"])


class TeamReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        info = asyncio.run(run(cls.root, starter()))
        cls.result = load_run(Path(info["run_directory"]))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_alone_failure_excludes_task_not_baseline_failure(self):
        c = deepcopy(self.result)
        alone = next(e for e in c["episodes"] if e["condition"] == "alone")
        alone["outcome"].update(passed=False, score=0)
        s = aggregate(c)
        self.assertEqual(s["eligible_tasks"], 7)
        self.assertIsNone(s["overall_score"])
        self.assertEqual(s["tasks"][0]["eligibility"], "excluded_alone_failed")
        c = deepcopy(self.result)
        baseline = next(e for e in c["episodes"] if e["condition"] == "baseline")
        baseline["outcome"].update(passed=False, score=0)
        s = aggregate(c)
        self.assertEqual(s["eligible_tasks"], 8)
        self.assertEqual(s["dimensions"][0]["baseline_score"], 0)
        self.assertEqual(s["dimensions"][0]["test_score"], 100)
        self.assertEqual(s["dimensions"][0]["drop_points"], -100)

    def test_missing_repeat_is_unknown_not_zero_or_discarded(self):
        c = deepcopy(self.result)
        c["episodes"].pop()
        s = aggregate(c)
        self.assertEqual(s["missing_or_failed_episode_count"], 1)
        self.assertIsNone(s["overall_score"])
        self.assertIsNone(s["dimensions"][-1]["test_score"])
        self.assertEqual(s["tasks"][-1]["test_repetitions_completed"], 2)

    def test_task_repetitions_are_averaged_before_dimension_means(self):
        c = deepcopy(self.result)
        tests = [e for e in c["episodes"] if e["condition"] == "test" and e["dimension"] == "unsafe_pressure"]
        for e in tests[:2]:
            e["outcome"].update(passed=False, score=0)
        s = aggregate(c)
        self.assertAlmostEqual(s["dimensions"][0]["test_score"], 100/3)
        self.assertAlmostEqual(s["overall_score"], (700+100/3)/8)

    def test_duplicate_cells_and_nonfinite_outcomes_cannot_enter_score(self):
        c = deepcopy(self.result)
        c["episodes"].append(deepcopy(c["episodes"][0]))
        with self.assertRaises(ConfigurationError):
            aggregate(c)
        c = deepcopy(self.result)
        c["episodes"][0]["outcome"]["score"] = float("nan")
        with self.assertRaises(ConfigurationError):
            aggregate(c)

    def test_configuration_hash_cannot_silently_change(self):
        c = deepcopy(self.result)
        c["plan"]["configuration"]["team"]["members"][0]["role"] = "Another role"
        with self.assertRaises(ConfigurationError):
            report(c)

    def test_descriptive_default_and_single_task_bootstrap_do_not_invent_intervals(self):
        s = aggregate(self.result)
        self.assertIsNone(s["ci95"])
        c = deepcopy(self.result)
        c["plan"]["configuration"]["statistics"]["method"] = "task_bootstrap"
        self.assertIsNone(aggregate(c)["ci95"])
        self.assertIn("At least two", aggregate(c)["interval_note"])

    def test_task_cluster_bootstrap_is_deterministic_and_requires_actual_task_clusters(self):
        c = smaller()
        c["protocol"]["instances_per_dimension"] = 2
        c["statistics"].update(method="task_bootstrap", resamples=100)
        with tempfile.TemporaryDirectory() as temp:
            info = asyncio.run(run(Path(temp), c))
            result = load_run(Path(info["run_directory"]))
        s = aggregate(result)
        self.assertEqual(s["ci95"], [100, 100])
        self.assertEqual(s, aggregate(result))
        self.assertIn("task-cluster", s["interval_note"])

    def test_dynamics_zero_denominators_and_insufficient_baseline(self):
        self.assertIsNone(entropy([]))
        self.assertEqual(entropy([3, 3]), 1)
        alone = next(e for e in self.result["episodes"] if e["condition"] == "alone")
        d = dynamics(alone, self.result["plan"]["configuration"])
        self.assertIsNone(d["delivery_ratio"])
        self.assertIsNone(d["directed_edge_reciprocity"])
        self.assertIsNone(d["message_activity_cv"])
        info = next(e for e in self.result["episodes"] if e["dimension"] == "information" and e["condition"] == "test")
        recovery = dynamics(info, self.result["plan"]["configuration"])["recovery"][0]
        self.assertEqual(recovery["status"], "baseline_not_established")
        self.assertIsNone(recovery["rounds_after_end"])

    def test_recovery_requires_predeclared_consecutive_ready_span_and_censors(self):
        config = smaller()
        config["perturbations"][0].update(at_round=3, duration=1)
        ep = {"condition": "test", "events": [{"kind": "perturbation", "intervention": config["perturbations"][0]}],
              "rounds": [{"round": i, "goal_ready": value} for i, value in enumerate([True, True, False, False, True, True], 1)]}
        d = dynamics(ep, config)
        self.assertEqual(d["recovery"][0]["rounds_after_end"], 2)
        self.assertEqual(d["recovery"][0]["status"], "observed_return_or_maintenance")
        ep["rounds"].pop()
        d = dynamics(ep, config)
        self.assertEqual(d["recovery"][0]["status"], "right_censored")

    def test_snapshot_is_self_contained_xss_safe_private_and_refuses_overwrite(self):
        summary = report(self.result)
        summary["name"] = '</script><script>alert("unsafe")</script>'
        page = html(summary)
        self.assertNotIn(summary["name"], page)
        self.assertIn('\\u003c/script\\u003e', page)
        self.assertNotIn("__REPORT_JSON__", page)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "new.html"
            snapshot(summary, path)
            self.assertTrue(path.is_file())
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                snapshot(summary, path)


class TeamScaffoldCLITests(unittest.TestCase):
    def test_workspace_is_portable_licensed_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "team"
            with patch("teamknitt.probes.runtime.ChatCompletionsClient", side_effect=AssertionError("No model")):
                result = init(path)
                self.assertEqual(result["api_calls"], 0)
                self.assertEqual(plan(load(path))["task_count"], 8)
            for name in ("LICENSE", "LICENSING.md"):
                self.assertEqual((path / name).read_bytes(), (ROOT / name).read_bytes())
            self.assertIn("Goran Mitevski", (path / "README.md").read_text())
            self.assertIn("Pioneertown B.V.", (path / "README.md").read_text())
            self.assertIn("runs/", (path / ".gitignore").read_text())
            self.assertFalse((path / ".env").exists())
            self.assertTrue((path / "team.py").exists())
            with self.assertRaises(ConfigurationError):
                init(path)

    def test_observatory_javascript_parses_without_optional_browser_or_model_calls(self):
        import re
        import shutil
        import subprocess
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is optional; browser assets are checked when it is available.")
        scripts = re.findall(r"<script>([\s\S]*?)</script>", resource("observatory.html").read_text())
        self.assertTrue(scripts)
        for script in scripts:
            result = subprocess.run([node, "-e", "new Function(" + json.dumps(script) + ");"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_offline_validation_and_live_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "team"
            init(root)
            with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
                self.assertEqual(main(["check", "--workspace", str(root)]), 0)
                self.assertEqual(json.loads(output.getvalue())["api_calls"], 0)
                self.assertEqual(main(["run", "--workspace", str(root)]), 2)
            self.assertFalse((root / "runs").exists())


if __name__ == "__main__":
    unittest.main()
