"""Read-only visualization, concurrent computation signals and portable offline views."""
import asyncio
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.cli import main
from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.planning import catalogue, compile_plan
from teamknitt.engine.scaffold import init_workspace
from teamknitt.engine.study import load_study, plans, save, TextStudy
from teamknitt.engine.visualization import (CONFIRMATION_NODE, SetupVisualizationAgent, RuntimeObserverAgent,
                                 VisualizationSession, VisualizationServer, activity_metadata, render_page)

PROJECT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 30, 12, tzinfo=timezone.utc).timestamp()
AT = "2026-10-30T12:00:00+00:00"


class VisualizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plan = compile_plan(PROJECT)
        self.setup = SetupVisualizationAgent().visualize(self.plan)

    def tearDown(self):
        self.temp.cleanup()

    def trial(self, name="run-1", status="running"):
        root = self.root / "trials" / name
        save(root / "plan.json", self.plan)
        save(root / "summary.json", {"trial_id": name, "variant": "chosen", "status": status,
                                     "configuration_snapshot_id": self.plan["configuration_snapshot"]["id"]})
        save(root / "activity-heartbeat.json", {"time": AT, "status": status})
        return root

    def append(self, root, *events, journal="activity.jsonl"):
        with (root / journal).open("a") as stream:
            for event in events:
                stream.write(json.dumps({"time": AT, **event}) + "\n")

    def test_all_six_designs_and_user_restrictions_are_projected_without_research_content(self):
        graphs = set()
        for design in catalogue(PROJECT):
            plan = compile_plan(PROJECT, design_file=design["file"], profile="none", statistical_approach="frequentist")
            setup = SetupVisualizationAgent().visualize(plan)
            self.assertEqual(setup["design"]["id"], plan["design"]["id"])
            self.assertEqual(setup["communication"], "none")
            self.assertEqual(setup["statistics"], "frequentist")
            self.assertEqual({a["id"] for a in setup["actors"]}, {p["instance_id"] for p in plan["personas"]})
            self.assertNotIn("resolved_config", json.dumps(setup))
            graphs.add(json.dumps(setup["nodes"]))
        self.assertEqual(len(graphs), 6)

    def test_agent_rejects_cyclic_recorded_plans(self):
        self.plan["work_graph"][0]["depends_on"] = [self.plan["work_graph"][-1]["id"]]
        with self.assertRaises(ConfigurationError):
            SetupVisualizationAgent().visualize(self.plan)

    def test_simultaneous_model_and_evaluator_work_is_scoped_to_nodes_and_actors(self):
        root = self.trial()
        actor_a = {"id": "a.1", "team": "a.1", "episode": "a"}
        actor_b = {"id": "b.1.child1", "team": "b.1", "episode": "b"}
        self.append(root,
            {"kind": "episode_started", "actor": actor_a, "node": "left"},
            {"kind": "provider_request", "actor": actor_a, "node": "left", "request_id": "r", "path": "/chat/completions"},
            {"kind": "activity_started", "actor": actor_b, "node": "right", "activity_id": "e", "category": "evaluation"})
        observer = RuntimeObserverAgent()
        state = observer.observe(root, self.setup, clock=NOW + 2)
        self.assertEqual(state["status"], "running")
        self.assertEqual({a["node"] for a in state["active"]}, {"left", "right"})
        self.assertEqual({a["category"] for a in state["active"]}, {"generation", "evaluation"})
        self.assertEqual(state["metrics"]["requests"], 1)
        self.append(root,
            {"kind": "provider_response", "request_id": "r", "usage": {"input_tokens": 10, "output_tokens": 4}},
            {"kind": "activity_finished", "activity_id": "e", "category": "evaluation", "status": "completed"})
        after = observer.observe(root, self.setup, clock=NOW + 3)
        self.assertFalse(after["active"])
        self.assertEqual(after["metrics"]["evaluations"], 1)
        self.assertEqual(after["metrics"]["input_tokens"], 10)
        self.assertEqual(observer.observe(root, self.setup, clock=NOW + 4)["metrics"], after["metrics"])

    def test_stale_and_finished_runs_never_keep_live_compute_indicators(self):
        root = self.trial()
        self.append(root, {"kind": "phase_started", "node": "left"},
                    {"kind": "provider_request", "node": "left", "request_id": "r"})
        observer = RuntimeObserverAgent()
        stale = observer.observe(root, self.setup, clock=NOW + 20)
        self.assertEqual(stale["status"], "stale")
        self.assertEqual(stale["node_states"]["left"], "unknown")
        self.assertEqual(stale["active"][0]["status"], "unknown")
        save(root / "summary.json", {"status": "failed_or_incomplete"})
        ended = observer.observe(root, self.setup, clock=NOW + 21)
        self.assertEqual(ended["status"], "failed")
        self.assertEqual(ended["active"][0]["status"], "interrupted")
        self.assertEqual(ended["node_states"]["left"], "interrupted")

    def test_older_journals_are_supported_without_assuming_live_activity(self):
        root = self.trial()
        (root / "activity-heartbeat.json").unlink()
        self.append(root, {"kind": "provider_request", "request_id": "old", "request": {"messages": "PRIVATE"}}, journal="events.jsonl")
        state = RuntimeObserverAgent().observe(root, self.setup, clock=NOW)
        self.assertEqual(state["status"], "activity_unknown")
        self.assertNotIn("PRIVATE", json.dumps(state))

    def test_incremental_tail_handles_partial_lines_invalid_json_and_truncation(self):
        root = self.trial()
        path = root / "activity.jsonl"
        path.write_text('{"kind":"provider_request","request_id":"r"')
        observer = RuntimeObserverAgent()
        self.assertEqual(observer.observe(root, self.setup, clock=NOW)["metrics"]["requests"], 0)
        with path.open("a") as stream:
            stream.write('}\nnot-json\n')
        result = observer.observe(root, self.setup, clock=NOW)
        self.assertEqual(result["metrics"]["requests"], 1)
        self.assertEqual(result["skipped_events"], 1)
        path.write_text('{}\n')
        self.assertEqual(observer.observe(root, self.setup, clock=NOW)["metrics"]["requests"], 0)

    def test_pending_verification_is_not_presented_as_measured_confirmation(self):
        root = self.trial()
        self.append(root, {"kind": "domain_step_pending", "node": "verify"},
                    {"kind": "phase_completed", "node": "verify"})
        observer = RuntimeObserverAgent()
        self.assertEqual(observer.observe(root, self.setup, clock=NOW)["node_states"]["verify"], "deferred")
        self.append(root, {"kind": "activity_started", "node": CONFIRMATION_NODE, "activity_id": "c", "category": "confirmation"})
        self.assertEqual(observer.observe(root, self.setup, clock=NOW)["node_states"][CONFIRMATION_NODE], "running")

    def test_request_bodies_shadow_answers_and_paths_are_excluded(self):
        event = {"kind": "provider_response", "response": {"usage": {"prompt_tokens": 9, "completion_tokens": 3},
                 "choices": "SECRET"}, "request": "SECRET", "source_ref": "/private/SECRET",
                 "result": {"answer": "SECRET"}, "error": "SECRET"}
        safe = activity_metadata(event)
        self.assertNotIn("SECRET", json.dumps(safe))
        self.assertEqual(safe["usage"], {"input_tokens": 9, "output_tokens": 3})
        event["response"].pop("usage")
        event["usage"] = {"input_tokens": 7, "output_tokens": 1}
        self.assertEqual(activity_metadata(event)["usage"], event["usage"])

    def test_parent_waits_for_child_and_same_llm_decisions_are_labeled_as_decisions(self):
        root = self.trial()
        parent = {"id": "a.1", "team": "a.1", "episode": "parent"}
        child = {"id": "a.1.child1", "team": "a.1", "episode": "child"}
        self.append(root,
            {"kind": "episode_started", "actor": parent, "node": "work"},
            {"kind": "activity_started", "actor": parent, "node": "work", "category": "delegation", "activity_id": "d"},
            {"kind": "episode_started", "actor": child, "node": "work"},
            {"kind": "activity_started", "actor": child, "node": "work", "category": "decision", "activity_id": "j"},
            {"kind": "provider_request", "actor": child, "node": "work", "path": "/chat/completions", "request_id": "r"})
        state = RuntimeObserverAgent().observe(root, self.setup, clock=NOW)
        self.assertEqual(next(a for a in state["actors"] if a["id"] == "a.1")["status"], "waiting")
        request = next(a for a in state["active"] if a["kind"] == "provider_request")
        self.assertEqual(request["category"], "decision")

    def test_latest_only_attaches_matching_configuration_and_saved_run_uses_its_own_plan(self):
        old = self.trial("old")
        current = self.trial("current")
        modified = json.loads((old / "plan.json").read_text())
        modified["design"]["name"] = "Recorded design"
        save(old / "plan.json", modified)
        save(old / "summary.json", {"configuration_snapshot_id": "other-settings", "variant": "chosen"})
        session = VisualizationSession(self.plan, self.root, "chosen")
        self.assertEqual(session.snapshot()["selection"], current.name)
        self.assertEqual(session.snapshot("old")["setup"]["design"]["name"], "Recorded design")
        self.assertEqual(session.snapshot("setup")["runtime"]["status"], "plan_only")

    def test_trial_paths_and_symlinks_cannot_escape_the_workspace(self):
        session = VisualizationSession(self.plan, self.root)
        (self.root / "trials").mkdir()
        for name in ("../private", "/tmp", ".", "..", "%2e%2e"):
            with self.assertRaises(ConfigurationError):
                session.trial_root(name)
        with tempfile.TemporaryDirectory() as external:
            (self.root / "trials" / "escaped").symlink_to(external, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                session.trial_root("escaped")
        root = self.trial()
        (root / "summary.json").unlink()
        (root / "summary.json").symlink_to(PROJECT / "configs/lab.yaml")
        with self.assertRaises(ConfigurationError):
            session.snapshot("run-1")

    def test_standalone_html_is_offline_and_escapes_script_terminators(self):
        state = VisualizationSession(self.plan).snapshot()
        state["setup"]["design"]["name"] = '</script><script>alert("XSS")</script>'
        page = render_page(state)
        self.assertNotIn('</script><script>alert', page)
        self.assertNotIn("/* teamknitt_", page)
        self.assertIn('"api_url": null', page)
        self.assertNotIn("https://", page)
        self.assertIn("Runtime observer", page)

    def test_evidence_status_is_independent_of_workflow_completion_and_allowlisted(self):
        root = self.trial(status="completed_text_workflow")
        save(root / "summary.json", {"status": "completed_text_workflow", "verification_status": "not_evaluated"})
        observer = RuntimeObserverAgent()
        ended = observer.observe(root, self.setup, clock=NOW)
        self.assertEqual(ended["status"], "completed")
        self.assertEqual(ended["verification_status"], "not_evaluated")
        save(root / "summary.json", {"status": "completed_text_workflow", "verification_status": "PRIVATE-UNRECOGNIZED"})
        unknown = observer.observe(root, self.setup, clock=NOW)
        self.assertEqual(unknown["verification_status"], "unknown")
        self.assertNotIn("PRIVATE-UNRECOGNIZED", json.dumps(unknown))
        self.assertEqual(RuntimeObserverAgent().observe(None, self.setup)["verification_status"], "not_run")

    def test_http_routes_expose_only_the_view_and_metadata(self):
        # Exercise routing without opening sockets in the offline unit suite.
        server = object.__new__(VisualizationServer)
        server.server_port, server.prefix = 8765, "/session/"
        server.session = VisualizationSession(self.plan)
        host = "127.0.0.1:8765"
        self.assertEqual(server.response("/session/", host=host)[0], 200)
        self.assertEqual(server.response("/session/api/state", host=host)[0], 200)
        for path in ("/.env", "/session/../../.env", "/session/plan.json", "/session/api/state?trial=../seeds"):
            self.assertIn(server.response(path, host=host)[0], {400, 404})
        self.assertEqual(server.response("/session/", host="hostile.example")[0], 403)
        self.assertEqual(server.response("/session/", host=host, origin="https://hostile.example")[0], 403)

    def test_cli_and_installed_workspace_wrapper_export_without_credentials_or_provider_calls(self):
        workspace = self.root / "lab"
        init_workspace(workspace)
        target = self.root / "view.html"
        with patch("teamknitt.engine.study.ChatCompletionsClient", side_effect=AssertionError("No model calls")), redirect_stdout(StringIO()):
            code = main(["--project", str(workspace), "study", "visualize", "--workspace", str(workspace),
                         "--variant", "single", "--output", str(target)])
        self.assertEqual(code, 0)
        self.assertTrue(target.is_file())
        self.assertFalse((workspace / "trials").exists())
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["--project", str(workspace), "visualize", "--output", str(target)]), 2)


class InstrumentationTests(unittest.TestCase):
    def test_real_runner_emits_scoped_redacted_activity_and_terminal_heartbeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "lab"
            init_workspace(workspace)
            config = load_study(workspace)
            plan = plans(workspace, config)["single"]
            study = TextStudy(workspace, workspace, config, plan, "single", "PRIVATE-TEST-KEY")
            final = {"action": "final", "summary": "PRIVATE-RESULT", "findings": [], "wisdom": [], "candidate_output": "PRIVATE-SOURCE"}
            study.client._transport = lambda *args: {"choices": [{"message": {"content": json.dumps(final)}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
            result = asyncio.run(study.run())
            self.assertEqual(result["status"], "completed_text_workflow")
            journal = (study.root / "activity.jsonl").read_text()
            self.assertNotIn("PRIVATE-", journal)
            rows = [json.loads(line) for line in journal.splitlines()]
            requests = [r for r in rows if r["kind"] == "provider_request"]
            self.assertTrue(requests)
            self.assertTrue(all(r["node"] in {n["id"] for n in plan["work_graph"]} for r in requests))
            view = VisualizationSession(plan, workspace, trial=study.id).snapshot()
            self.assertEqual(view["runtime"]["status"], "completed")
            self.assertEqual(view["runtime"]["metrics"]["requests"], study.calls)
            self.assertFalse(view["runtime"]["active"])
            self.assertEqual(view["runtime"]["node_states"][CONFIRMATION_NODE], "skipped")
            self.assertEqual(json.loads((study.root / "activity-heartbeat.json").read_text())["status"], result["status"])

    def test_cancellation_stops_the_pulse_and_preserves_a_terminal_record(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary) / "lab"
                init_workspace(workspace)
                config = load_study(workspace)
                study = TextStudy(workspace, workspace, config, plans(workspace, config)["single"], "single", "fake-key")
                entered = asyncio.Event()
                async def blocked():
                    entered.set()
                    await asyncio.Event().wait()
                study.run_graph = blocked
                task = asyncio.create_task(study.run())
                await entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertEqual(json.loads((study.root / "summary.json").read_text())["status"], "cancelled")
                self.assertFalse([t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()])
        asyncio.run(exercise())

    def test_cancellation_during_confirmation_closes_activity_and_stops_the_pulse(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary) / "lab"
                init_workspace(workspace)
                config = load_study(workspace)
                study = TextStudy(workspace, workspace, config, plans(workspace, config)["single"], "single", "fake-key")
                entered = asyncio.Event()
                class Research:
                    async def complete(self):
                        entered.set()
                        await asyncio.Event().wait()
                async def graph():
                    return None
                study.run_graph, study.research = graph, Research()
                task = asyncio.create_task(study.run())
                await entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                rows = [json.loads(line) for line in (study.root / "activity.jsonl").read_text().splitlines()]
                closed = next(r for r in rows if r["kind"] == "activity_finished")
                self.assertEqual(closed["status"], "cancelled")
                self.assertEqual(closed["node"], CONFIRMATION_NODE)
                self.assertEqual(json.loads((study.root / "summary.json").read_text())["status"], "cancelled")
                self.assertFalse([t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()])
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
