"""Guards for the teamknitt skill plugin: layout, licence files and the bundled runtime copy."""
from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "skills/teamknitt"
SKILL = PLUGIN / "skills/teamknitt"


class SkillBundleTests(unittest.TestCase):
    def test_plugin_layout_and_manifest(self):
        manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "teamknitt")
        self.assertEqual(manifest["license"], "LicenseRef-Teamknitt-Skill-1.0")
        for name in ("README.md", "LICENSE", "LICENSING.md"):
            self.assertTrue((PLUGIN / name).is_file(), name)
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: teamknitt\n"))
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual([p["source"] for p in marketplace["plugins"]], ["./skills/teamknitt"])

    def test_skill_licence_identity_and_main_licence_travel_with_the_skill(self):
        text = (PLUGIN / "LICENSE").read_text()
        self.assertTrue(text.startswith("Teamknitt Skill Licence 1.0\n"))
        for phrase in ("SPDX-License-Identifier: LicenseRef-Teamknitt-Skill-1.0",
                       "Copyright (c) 2026 Pioneertown B.V.", "Author: Goran Mitevski."):
            self.assertIn(phrase, text)
        for name in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
            self.assertEqual((SKILL / "runtime" / name).read_bytes(), (ROOT / name).read_bytes())

    def test_bundled_runtime_is_synchronized_and_within_directory_limits(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/sync_skill.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        files = [p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        self.assertLessEqual(len(files), 512)
        for path in files:
            self.assertFalse(path.is_symlink(), path)
            self.assertLess(path.stat().st_size, 256 * 1024, path)

    def test_skill_installs_only_the_bundled_runtime(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn('"${CLAUDE_SKILL_DIR}/runtime"', text)
        self.assertNotIn("git clone", text)


if __name__ == "__main__":
    unittest.main()
