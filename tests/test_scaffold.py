"""Portability checks: wheel resources, private seeds and refusal to overwrite."""
import asyncio
from importlib.resources import files
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.planning import catalogue, compile_plan
from teamknitt.engine.scaffold import init_workspace
from teamknitt.engine.study import load_study, plans, prepare, run_variant


class ScaffoldTests(unittest.TestCase):
    def test_new_text_workspace_is_complete_and_prepare_needs_no_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "lab"
            with patch("teamknitt.engine.study.ChatCompletionsClient", side_effect=AssertionError("No provider call")):
                result = init_workspace(root)
                self.assertEqual(result["api_calls"], 0)
                self.assertEqual(len(catalogue(root)), 6)
                self.assertEqual(prepare(root, root)["status"], "prepared")
            self.assertEqual(load_study(root)["runtime"]["mode"], "text_only")
            self.assertFalse((root / ".env").exists())
            with self.assertRaises(ValueError):
                asyncio.run(run_variant(root, root, "single"))
            self.assertFalse((root / "trials").exists())

    def test_existing_directory_and_symlink_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            existing = Path(temp) / "existing"
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_text("keep")
            with self.assertRaises(ConfigurationError):
                init_workspace(existing)
            self.assertEqual(marker.read_text(), "keep")
            link = Path(temp) / "link"
            link.symlink_to(existing, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                init_workspace(link)

    def test_memory_seeds_are_unique_disjoint_private_and_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "a", Path(temp) / "b"
            init_workspace(a, "memory")
            init_workspace(b, "memory")
            seeds = a / "mission/memory/private_splits.json"
            panels = json.loads(seeds.read_text())
            values = [v for phase in panels.values() for panel in phase.values() for v in panel]
            self.assertEqual(len(values), 800)
            self.assertEqual(len(set(values)), 800)
            self.assertNotEqual(seeds.read_bytes(), (b / seeds.relative_to(a)).read_bytes())
            if os.name == "posix":
                self.assertEqual(seeds.stat().st_mode & 0o777, 0o600)
            self.assertIn("mission/memory/private_splits.json", (a / ".gitignore").read_text())
            self.assertEqual(len(plans(a, load_study(a))), 3)
            self.assertEqual(load_study(a)["provider"]["model"], "YOUR_MODEL_ID")
            self.assertIsNone(load_study(a)["base_overrides"]["decisions"]["specialist"])
            self.assertEqual(compile_plan(a)["statistics"]["approach"], "frequentist")
            matrix = a / "configs/memory-matrix.yaml"
            from teamknitt.engine.config import parse_yaml
            self.assertEqual(len(plans(a, parse_yaml(matrix.read_text()))), 45)

    def test_specialist_can_be_selected_during_init_without_any_account_or_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "typed-lab"
            with patch("teamknitt.engine.study.ChatCompletionsClient", side_effect=AssertionError("No provider call")):
                result = init_workspace(root, "memory", "typed")
                self.assertEqual(result["api_calls"], 0)
                prepared = prepare(root, root)
            self.assertEqual(prepared["status"], "prepared")
            self.assertEqual(load_study(root)["base_overrides"]["decisions"]["specialist"], "specialist")
            self.assertIn("TEAMKNITT_DECISION_API_KEY=replace-me", (root / ".env.example").read_text())

    def test_wheel_starter_has_no_private_seed_or_machine_path(self):
        def walk(root):
            for child in root.iterdir():
                if child.is_dir():
                    yield from walk(child)
                else:
                    yield child
        for resource in walk(files("teamknitt.engine.resources").joinpath("starter")):
            self.assertNotEqual(resource.name, "private_splits.json")
            self.assertNotEqual(resource.name, ".env")
            if resource.name.endswith((".py", ".yaml", ".md", ".json")):
                self.assertNotIn("/Users/goran/", resource.read_text())


if __name__ == "__main__":
    unittest.main()
