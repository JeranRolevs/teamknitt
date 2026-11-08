"""Retired or stale build files must not survive into a release wheel."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_checks", ROOT / "tools/check_release.py")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class ReleaseArtifactTests(unittest.TestCase):
    def wheel(self, files):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "labtune-fixture.whl"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in {"LICENSE": "fixture", "LICENSING.md": "fixture", **files}.items():
                archive.writestr(name, content)
        return path

    def test_foundations_material_is_private_at_any_depth(self):
        names = (
            "docs/TEAMKNITT_FOUNDATIONS.md",
            "labtune/resources/starter/project/docs/TEAMKNITT_FOUNDATIONS.md",
            "Foundations and Theoretical Perspectives of Distributed Team Cognition.pdf",
            "docs/Foundations/book",
            "Fundations/notes.md",
            "docs/fundations.txt",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(checks.private_path(name))
        self.assertFalse(checks.private_path("docs/TEAMKNITT.md"))

    def test_foundations_ignore_rules_cover_material_and_starter_copies(self):
        names = [
            "docs/TEAMKNITT_FOUNDATIONS.md",
            "src/labtune/resources/starter/project/docs/TEAMKNITT_FOUNDATIONS.md",
            "Foundations and Theoretical Perspectives of Distributed Team Cognition.pdf",
            "docs/Foundations/book",
            "Fundations/notes.md",
            "docs/fundations.txt",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"], cwd=ROOT,
            input="\n".join(names) + "\n", text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stdout.splitlines(), names)

    def test_foundations_are_not_synced_into_starters(self):
        spec = importlib.util.spec_from_file_location("starter_sync", ROOT / "tools/sync_starter.py")
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        self.assertNotIn("project/docs/TEAMKNITT_FOUNDATIONS.md", sync.desired())

    def test_retired_module_in_a_reused_build_directory_is_rejected(self):
        path = self.wheel({"labtune/_retired_adapter.py": "raise RuntimeError('retired')"})
        self.assertIn("labtune/_retired_adapter.py: not in current package source", checks.check_artifact(path))

    def test_unexpected_package_namespace_is_rejected_after_a_rename(self):
        path = self.wheel({"outdated_namespace/__init__.py": "# Stale package from an earlier build"})
        self.assertIn("outdated_namespace/__init__.py: not in current package source", checks.check_artifact(path))

    def test_stale_module_bytes_are_rejected_and_current_source_passes(self):
        name = "labtune/__init__.py"
        current = (ROOT / "src" / name).read_bytes()
        stale = self.wheel({name: current + b"\n# stale build content\n"})
        self.assertIn(name + ": differs from current package source", checks.check_artifact(stale))
        self.assertEqual(checks.check_artifact(self.wheel({name: current})), [])
