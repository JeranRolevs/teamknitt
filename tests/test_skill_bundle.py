"""Guards for the teamknitt skill plugin: layout, licence files, shipped file types and the install pin."""
from pathlib import Path
import json
import re
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
        for copy, source in (("TEAMKNITT-NONCOMMERCIAL-RESEARCH-LICENCE-2.0.txt", "LICENSE"),
                             ("LICENSING.md", "LICENSING.md"), ("PROVENANCE.md", "PROVENANCE.md")):
            self.assertEqual((PLUGIN / "licenses" / copy).read_bytes(), (ROOT / source).read_bytes())

    def test_documents_are_synchronized_and_only_directory_file_types_ship(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/sync_skill.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        files = [p for p in PLUGIN.rglob("*") if p.is_file()]
        self.assertLessEqual(len(files), 512)
        for path in files:
            self.assertFalse(path.is_symlink(), path)
            data = path.read_bytes()
            if path.suffix == ".png":
                self.assertTrue(data.startswith(b"\x89PNG"), path)
                self.assertLess(len(data), 2 * 1024 * 1024, path)
                continue
            # The directory accepts only documents and data from organizations that are not Verified.
            self.assertTrue(path.suffix in {".md", ".txt", ".json", ".yaml", ".yml"} or path.name == "LICENSE", path)
            self.assertLess(len(data), 256 * 1024, path)
            self.assertNotIn(b"\x00", data, path)
            self.assertFalse(data.startswith(b"#!"), path)
            data.decode("utf-8")

    def test_skill_installs_only_the_pinned_repository_commit(self):
        text = (SKILL / "SKILL.md").read_text()
        pins = set(re.findall(r"github\.com/JeranRolevs/teamknitt(?:/archive/|@)([0-9a-f]{40})", text))
        self.assertEqual(len(pins), 1, pins)
        self.assertNotIn("git clone", text)
        self.assertIn(next(iter(pins)), (PLUGIN / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
