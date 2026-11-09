"""Structural checks only. No lab-style comparisons, models, or experiments."""

from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from teamknitt.engine.config import ConfigurationError, load_config, parse_yaml, project_file, validate
from teamknitt.engine.cli import main
from teamknitt.engine.planning import catalogue, compile_plan

PROJECT = Path(__file__).resolve().parents[1]


class SkeletonContracts(unittest.TestCase):
    def test_all_presets_compile_to_distinct_governance_and_procedures(self):
        plans = [compile_plan(PROJECT, design_file=row["file"]) for row in catalogue(PROJECT)]
        self.assertEqual(len(plans), 6)
        self.assertEqual(len({p["design"]["governance"] for p in plans}), 6)
        self.assertEqual(len({p["design"]["procedure"] for p in plans}), 6)
        for plan in plans:
            self.assertEqual(plan["runtime_execution"], "not_started")
            self.assertEqual(plan["configuration_snapshot"]["purpose"], "audit_only")
            self.assertEqual(plan["configuration_control"]["authority"], "user")
            seen = set()
            for node in plan["work_graph"]:
                self.assertTrue(set(node["depends_on"]) <= seen)
                self.assertNotIn(node["id"], seen)
                seen.add(node["id"])
            self.assertTrue(all(p["model_binding"] == "shared_model" for p in plan["personas"]))

    def test_all_sharing_profiles_resolve_without_preset_escalation(self):
        profiles = {"none": [], "low": ["low.md"], "intermediate": ["intermediate.md"],
                    "high": ["high.md"], "wisdom_only": ["wisdom.md"]}
        for row in catalogue(PROJECT):
            for profile, expected in profiles.items():
                with self.subTest(design=row["id"], profile=profile):
                    plan = compile_plan(PROJECT, design_file=row["file"], profile=profile)
                    self.assertEqual(plan["communication"]["files"], expected)
                    if profile == "none":
                        self.assertFalse(plan["communication"]["research_exchange"])
                        coordination = [n for n in plan["work_graph"] if n["kind"] == "coordination"]
                        self.assertTrue(all(n["research_activity"] == "operational_only" for n in coordination))
            for profile in ("low", "intermediate", "high"):
                plan = compile_plan(PROJECT, design_file=row["file"], profile=profile, wisdom=True)
                self.assertEqual(plan["communication"]["files"], [f"{profile}.md", "wisdom.md"])

    def test_contradictory_wisdom_only_override_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            compile_plan(PROJECT, profile="wisdom_only", wisdom=False)

    def test_check_scopes_persona_overrides_to_selected_design(self):
        selected = compile_plan(PROJECT)
        persona = next(p["id"] for p in selected["personas"] if p["role"] == "prime")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(PROJECT / "lab_designs", root / "lab_designs")
            (root / "config.yaml").write_text(json.dumps({
                "schema_version": 1,
                "lab": {"design_file": selected["design"]["file"]},
                "teams": {"role_instances": {persona: 2}},
            }))
            output, errors = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                status = main(["--project", str(root), "check", "--config", "config.yaml"])
            self.assertEqual(status, 0, errors.getvalue())
            self.assertEqual(json.loads(output.getvalue())["presets"], 6)

    def test_duplicate_yaml_and_nonfinite_values_are_rejected(self):
        for value in ("lab: 1\nlab: 2", "metric: .nan", "metric: .inf"):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                parse_yaml(value)

    def test_unknown_fields_and_removed_self_improvement_settings_are_rejected(self):
        config = load_config(PROJECT)
        for path in ("unexpected", "learning"):
            value = deepcopy(config)
            value[path] = True
            with self.assertRaises(ConfigurationError):
                validate(value, "lab_config.schema.json")

    def test_project_escape_and_symlink_escape_are_rejected(self):
        with self.assertRaises(ConfigurationError):
            project_file(PROJECT, "../README.md")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside.md").symlink_to(PROJECT / "README.md")
            with self.assertRaises(ConfigurationError):
                project_file(root, "outside.md")

    def test_all_record_templates_validate_and_remain_templates(self):
        paths = sorted((PROJECT / "templates/records").glob("*.json"))
        self.assertEqual(len(paths), 12)
        for path in paths:
            record = json.loads(path.read_text())
            validate(record, "records.schema.json")
            self.assertTrue(record["template"])
        invalid = json.loads((PROJECT / "templates/records/research_event.json").read_text())
        invalid["created_at"] = "not-a-timestamp"
        with self.assertRaises(ConfigurationError):
            validate(invalid, "records.schema.json")

    def test_plan_identity_is_repeatable_and_changes_with_configuration(self):
        first = compile_plan(PROJECT, profile="none")
        second = compile_plan(PROJECT, profile="none")
        different = compile_plan(PROJECT, profile="high")
        self.assertEqual(first["configuration_snapshot"]["id"], second["configuration_snapshot"]["id"])
        self.assertNotEqual(first["configuration_snapshot"]["id"], different["configuration_snapshot"]["id"])

    def test_user_can_change_style_and_sharing_without_a_promotion_gate(self):
        initial = compile_plan(PROJECT, profile="none")
        changed = compile_plan(PROJECT, design_file="lab_designs/E-flat-holacratic-colab.md", profile="high", wisdom=True)
        self.assertNotEqual(initial["design"]["id"], changed["design"]["id"])
        self.assertEqual(changed["communication"]["effective_profile"], "high+wisdom")
        for plan in (initial, changed):
            self.assertTrue(plan["configuration_control"]["settings_editable"])
            self.assertNotIn("lab_version", plan)
            self.assertNotIn("learning", plan)
            self.assertFalse(any("promotion" in path for path in plan["planned_run_layout"]))

    def test_supported_statistics_and_removed_options_are_explicit(self):
        p = compile_plan(PROJECT, statistical_approach="frequentist")
        self.assertEqual(p["statistics"]["approach"], "frequentist")
        self.assertFalse(p["statistics"]["silent_approach_switch_allowed"])
        for choice in ("bayesian", "probabilistic", "unrecognized"):
            with self.assertRaises(ConfigurationError):
                compile_plan(PROJECT, statistical_approach=choice)

    def test_removed_statistics_cli_option_is_rejected_not_reinterpreted(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for choice in ("bayesian", "probabilistic"):
                with self.assertRaises(SystemExit) as caught:
                    main(["--project", str(PROJECT), "plan", "--statistics", choice])
                self.assertEqual(caught.exception.code, 2)

    def test_statistical_analysis_needs_results_or_an_explicit_reason(self):
        base = json.loads((PROJECT / "templates/records/evaluation_receipt.json").read_text())
        for approach in ("frequentist",):
            for status in ("completed", "inconclusive"):
                record = deepcopy(base)
                assessment = record["payload"]["statistics"]
                assessment.update(approach=approach, status=status, reason=None)
                with self.subTest(approach=approach, status=status), self.assertRaises(ConfigurationError):
                    validate(record, "records.schema.json")
                assessment.update(protocol_ref="fixture:protocol", result_refs=["fixture:analysis-result"])
                validate(record, "records.schema.json")
            for status in ("not_required", "not_run", "unsupported"):
                record = deepcopy(base)
                record["payload"]["statistics"].update(approach=approach, status=status, reason="Fixture: analysis not applicable or not available")
                validate(record, "records.schema.json")
                record["payload"]["statistics"]["reason"] = None
                with self.subTest(approach=approach, status=status), self.assertRaises(ConfigurationError):
                    validate(record, "records.schema.json")

    def test_copied_project_operates_from_unrelated_cwd_without_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "standalone"
            shutil.copytree(PROJECT, copy, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", ".venv", "runs", "build", "dist", "*.egg-info",
                "setup", "plans", "trials", "comparisons", "results", "data", ".env", ".env.*",
                "private_splits.json", "local-reference", "archive", "CODE_PROVENANCE_AUDIT.md",
                "provenance_audit.json", "RELATED_WORK_REVIEW.md", "REVIEW.md", "PLAN.md", "idea_flow.md"))
            env = dict(os.environ, PYTHONPATH=str(copy / "src"), PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run([sys.executable, "-m", "teamknitt", "engine", "--project", str(copy), "check"],
                                    cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["presets"], 6)
            self.assertFalse((copy / "runs").exists())


if __name__ == "__main__":
    unittest.main()
