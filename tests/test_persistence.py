"""Single-scientist sequencing, retained contexts, budget boundaries and confirmation order."""
import asyncio
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.cli import main
from teamknitt.engine.config import ConfigurationError, load_config, validate_config
from teamknitt.engine.planning import compile_plan
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.scaffold import init_workspace
from teamknitt.engine.study import load_study, plans, prepare, save, TextStudy, run_variant, timestamp, compare
from teamknitt.engine.visualization import RuntimeObserverAgent, SetupVisualizationAgent, VisualizationSession

PROJECT = Path(__file__).resolve().parents[1]
DESIGN = "lab_designs/F-single-scientist.md"


class PlanningTests(unittest.TestCase):
    def test_preexisting_resolved_configuration_does_not_require_the_new_design_section(self):
        previous = load_config(PROJECT)
        previous.pop("single_scientist")
        validate_config(previous)

    def test_three_levels_expand_one_scientist_into_a_strict_serial_graph(self):
        hashes = set()
        for level, passes in (("low", 1), ("medium", 3), ("persistent", 6)):
            plan = compile_plan(PROJECT, design_file=DESIGN, persistence=level, sequences=2)
            self.assertEqual(len(plan["personas"]), 1)
            self.assertEqual(plan["personas"][0]["instance_id"], "scientist.1")
            self.assertEqual(plan["execution"]["planned_passes"], passes * 2)
            graph = plan["work_graph"]
            self.assertEqual(len(graph), passes * 2 + 1)
            for index, node in enumerate(graph[1:], 1):
                self.assertEqual(node["depends_on"], [graph[index-1]["id"]])
                self.assertEqual(node["actors"], ["scientist.1"])
            hashes.add(plan["configuration_snapshot"]["id"])
        self.assertEqual(len(hashes), 3)

    def test_budget_mode_has_one_loop_boundary_per_sequence_and_never_expands_the_budget(self):
        plan = compile_plan(PROJECT, design_file=DESIGN, persistence="persistent", effort_mode="budget", sequences=3)
        self.assertIsNone(plan["execution"]["passes_per_sequence"])
        self.assertEqual(len(plan["work_graph"]), 4)
        self.assertEqual(plan["execution"]["budget_scope"], "all_sequences")
        self.assertEqual(plan["budget"]["max_llm_calls"], 100)

    def test_invalid_counts_and_incompatible_design_overrides_fail_before_runtime(self):
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ConfigurationError):
                compile_plan(PROJECT, design_file=DESIGN, sequences=count)
        for overrides in ({"teams": {"role_instances": {"scientist": 2}}},
                          {"teams": {"max_depth": 1}}, {"teams": {"max_children_per_agent": 1}}):
            with self.subTest(overrides=overrides), self.assertRaises(ConfigurationError):
                compile_plan(PROJECT, design_file=DESIGN, config_overrides=overrides)
        with self.assertRaises(ConfigurationError):
            compile_plan(PROJECT, sequences=2)
        with self.assertRaises(ConfigurationError):
            compile_plan(PROJECT, design_file=DESIGN, persistence="medium", effort_mode="budget")
        with self.assertRaises(ConfigurationError):
            compile_plan(PROJECT, design_file=DESIGN, persistence="persistent", effort_mode="budget", sequences=101)

    def test_new_template_and_plan_and_visualization_work_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "scientist"
            with patch("teamknitt.engine.study.ChatCompletionsClient", side_effect=AssertionError("No model calls")):
                init_workspace(root, "scientist")
                self.assertEqual(prepare(root, root)["variants"], ["scientist-low", "scientist-medium", "scientist-persistent"])
                self.assertEqual(compile_plan(root)["design"]["id"], "single_scientist")
                with redirect_stdout(StringIO()):
                    self.assertEqual(main(["--project", str(root), "visualize", "--workspace", str(root),
                                           "--variant", "scientist-medium", "--sequences", "2",
                                           "--output", str(root / "preview.html")]), 0)
                with self.assertRaises(ValueError):
                    asyncio.run(run_variant(root, root, "scientist-medium", sequences=2))
            self.assertFalse((root / "trials").exists())
            self.assertFalse((root / ".env").exists())
            self.assertTrue((root / "docs/SINGLE_SCIENTIST.md").exists())
            self.assertIn("Sequence", (root / "preview.html").read_text())


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "lab"
        init_workspace(self.root, "scientist")
        (self.root / "mission/problem.md").write_text("Investigate this offline fixture problem; do not make empirical claims.")

    def tearDown(self):
        self.temp.cleanup()

    def study(self, level="medium", sequences=2, mode="fixed_passes", calls=80, context="continue"):
        config = load_study(self.root)
        config["base_overrides"]["budget"].update(max_llm_calls=calls, max_wall_seconds=30)
        config["base_overrides"]["single_scientist"].update(sequences=sequences, context_policy=context)
        plan = plans(self.root, config, variant_id="scientist-" + level, effort_mode=mode)["scientist-" + level]
        study = TextStudy(self.root, self.root, config, plan, "scientist-" + level, "private-fixture-key")
        self.messages = []
        def transport(method, path, body):
            self.messages.append(body["messages"])
            final = {"action": "final", "summary": "Fixture result", "findings": [], "wisdom": [],
                     "candidate_output": f"MEMORY-MARKER-{len(self.messages):04d}"}
            return {"choices": [{"message": {"content": json.dumps(final)}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1}}
        study.client._transport = transport
        return study

    def events(self, study):
        return [json.loads(line) for line in (study.root / "activity.jsonl").read_text().splitlines()]

    def test_multiple_fixed_sequences_keep_one_context_and_never_overlap(self):
        study = self.study()
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "completed_text_workflow")
        self.assertEqual(summary["provider_post_requests"], 6)
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 2)
        self.assertEqual([r["requests_used"] for r in summary["sequence_results"]], [3, 3])
        self.assertEqual([r["completed_passes"] for r in summary["sequence_results"]], [3, 3])
        self.assertIn("MEMORY-MARKER-0003", json.dumps(self.messages[3]))
        self.assertEqual({r["actor"] for r in study.outputs}, {"scientist.1"})
        pending, peak = set(), 0
        for event in self.events(study):
            if event["kind"] == "provider_request": pending.add(event["request_id"])
            if event["kind"] == "provider_response": pending.remove(event["request_id"])
            peak = max(peak, len(pending))
        self.assertEqual(peak, 1)
        self.assertFalse(pending)

    def test_explicit_fresh_context_only_resets_sequence_context_not_saved_evidence(self):
        study = self.study(context="fresh_sequence")
        summary = asyncio.run(study.run())
        self.assertEqual(summary["provider_post_requests"], 6)
        self.assertNotIn("MEMORY-MARKER-0003", json.dumps(self.messages[3]))
        self.assertIn("MEMORY-MARKER-0004", json.dumps(self.messages[4]))
        self.assertEqual(len(study.outputs), 6)
        resets = [e["context_reset"] for e in self.events(study) if e["kind"] == "sequence_started"]
        self.assertEqual(resets, [False, True])

    def test_fixed_work_stops_incomplete_at_the_shared_cap_without_spawning_extra_work(self):
        study = self.study(sequences=2, calls=2)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "failed_or_incomplete")
        self.assertEqual(summary["provider_post_requests"], 2)
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 0)
        self.assertEqual(len(json.loads((study.root / "outputs.partial.json").read_text())), 2)

    def test_budget_mode_partitions_remaining_requests_and_preserves_context(self):
        study = self.study(level="persistent", sequences=3, mode="budget", calls=7)
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "completed_text_workflow")
        self.assertEqual(summary["provider_post_requests"], 7)
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 3)
        self.assertEqual([r["request_allowance"] for r in summary["sequence_results"]], [3, 2, 2])
        self.assertEqual([r["requests_used"] for r in summary["sequence_results"]], [3, 2, 2])
        self.assertIn("MEMORY-MARKER-0003", json.dumps(self.messages[3]))
        self.assertEqual(len(study.outputs), 7)

    def test_budget_boundary_inside_a_decision_continuation_is_not_a_runtime_failure(self):
        study = self.study(level="persistent", sequences=2, mode="budget", calls=4)
        def transport(method, path, body):
            judging = body["messages"][0]["content"].startswith("Answer a bounded")
            answer = {"choice": "a", "confidence": 1, "probabilities": {"a": 1, "b": 0}} if judging else {
                "action": "decision.assess", "spec_id": "semantic_choice.v1", "question": {
                    "type": "choice", "instructions": "Pick an approach", "criteria": {"a": "First", "b": "Second"}}}
            return {"choices": [{"message": {"content": json.dumps(answer)}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
        study.client._transport = transport
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "completed_text_workflow")
        self.assertEqual(summary["provider_post_requests"], 4)
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 2)
        self.assertEqual(summary["sequence_progress"]["completed_passes"], 0)
        self.assertEqual(len([e for e in self.events(study) if e["kind"] == "pass_limit_reached"]), 2)
        view = VisualizationSession(study.plan, self.root, trial=study.id).snapshot()
        self.assertEqual(view["runtime"]["metrics"]["errors"], 0)
        self.assertFalse(view["runtime"]["active"])

    def test_transport_failure_is_not_retried_or_treated_as_a_completed_sequence(self):
        study = self.study(level="persistent", sequences=2, mode="budget", calls=6)
        def failure(*args): raise ProviderError("transport_uncertain", "Fixture failure; no retry")
        study.client._transport = failure
        summary = asyncio.run(study.run())
        self.assertEqual(summary["status"], "failed_or_incomplete")
        self.assertEqual(summary["provider_post_requests"], 1)
        self.assertEqual(summary["sequence_progress"]["completed_sequences"], 0)
        self.assertIsNone(study.sequence_request_end)

    def test_time_boundary_returns_unused_requests_to_remaining_sequences(self):
        study = self.study(level="persistent", sequences=2, mode="budget", calls=6)
        original = study.scientist_pass
        async def pass_then_exhaust_time(sequence, step, actor):
            result = await original(sequence, step, actor)
            if sequence == 1:
                study.sequence_deadline = 0
            return result
        study.scientist_pass = pass_then_exhaust_time
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_text_workflow")
        self.assertEqual([row["requests_used"] for row in result["sequence_results"]], [1, 5])
        self.assertEqual([row["request_allowance"] for row in result["sequence_results"]], [3, 5])
        self.assertEqual(result["sequence_results"][0]["stop_reason"], "time_allowance")
        self.assertEqual(result["provider_post_requests"], 6)

    def test_confirmation_runs_once_after_every_sequence_and_never_enters_generation_context(self):
        study = self.study()
        calls = []
        class Research:
            async def complete(self):
                calls.append(study.progress["completed_sequences"])
            def finalize(self):
                return {"confirmation_metrics": {}, "private_confirmation": "CONFIRMATION-ONLY-MARKER"}
        study.research = Research()
        result = asyncio.run(study.run())
        self.assertEqual(result["status"], "completed_research_pilot")
        self.assertEqual(calls, [2])
        self.assertNotIn("CONFIRMATION-ONLY-MARKER", json.dumps(self.messages))

    def test_live_progress_uses_events_instead_of_initial_summary_counters(self):
        study = self.study()
        asyncio.run(study.run())
        rows = self.events(study)
        stop = next(i for i, e in enumerate(rows) if e["kind"] == "pass_started" and e["sequence"] == 2)
        (study.root / "activity.jsonl").write_text(''.join(json.dumps(e)+'\n' for e in rows[:stop+1]))
        save(study.root / "summary.json", {"status": "running", "sequence_progress": {
            "current_sequence": 0, "current_pass": 0, "completed_passes": 0, "completed_sequences": 0}})
        save(study.root / "activity-heartbeat.json", {"time": timestamp()})
        observer = RuntimeObserverAgent()
        view = observer.observe(study.root, SetupVisualizationAgent().visualize(study.plan))
        self.assertEqual(view["sequence_progress"]["current_sequence"], 2)
        self.assertEqual(view["sequence_progress"]["current_pass"], 1)
        self.assertEqual(view["sequence_progress"]["completed_passes"], 3)

    def test_comparison_keeps_overridden_sequence_counts_and_configuration_identities(self):
        for sequences in (1, 2):
            study = self.study(level="low", sequences=sequences, calls=4)
            asyncio.run(study.run())
        result = compare(self.root)
        self.assertEqual(result["trials"], 2)
        rows = json.loads((self.root / "comparisons/summary.json").read_text())["trials"]
        self.assertEqual({row["scientist_sequences"] for row in rows}, {1, 2})
        self.assertEqual({row["scientist_sequences_completed"] for row in rows}, {1, 2})
        self.assertEqual(len({row["configuration_snapshot_id"] for row in rows}), 2)


if __name__ == "__main__":
    unittest.main()
