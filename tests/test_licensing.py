"""Keep the user-supplied Teamknitt terms and every new distribution copy aligned."""
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from teamknitt import __version__
from teamknitt.config import resource
from teamknitt.engine.scaffold import init_workspace
from teamknitt.scaffold import init as init_team
from teamknitt.probes.scaffold import init as init_probes
from teamknitt.teams.scaffold import init as init_teams

ROOT = Path(__file__).resolve().parents[1]
NAME = "Teamknitt Noncommercial Licence 1.0"
IDENTIFIER = "LicenseRef-Teamknitt-Noncommercial-1.0"

# User-supplied operative text. Line wrapping is immaterial; words/punctuation are not.
USER_TERMS = '''Acceptance
In order to get any license under these terms, you must agree to them as both strict obligations and conditions to all your licenses.

Copyright License
The licensor grants you a copyright license for the software to do everything you might do with the software that would otherwise infringe the licensor's copyright in it for any permitted purpose, other than distributing the software or making changes or new works based on the software.

Patent License
The licensor grants you a patent license for the software that covers patent claims the licensor can license, or becomes able to license, that you would infringe by using the software.

Noncommercial Purposes
Any noncommercial purpose is a permitted purpose.

Personal Uses
Personal use for research, experiment, and testing for the benefit of public knowledge, personal study, private entertainment, hobby projects, amateur pursuits, or religious observance, without any anticipated commercial application, is use for a permitted purpose.

Noncommercial Organizations
Use by any charitable organization, educational institution, public research organization, public safety or health organization, environmental protection organization, or government institution is use for a permitted purpose regardless of the source of funding or obligations resulting from the funding.

Fair Use
You may have "fair use" rights for the software under the law. These terms do not limit them.

No Other Rights
These terms do not allow you to sublicense or transfer any of your licenses to anyone else, or prevent the licensor from granting licenses to anyone else. These terms do not imply any other licenses.

Patent Defense
If you make any written claim that the software infringes or contributes to infringement of any patent, your patent license for the software granted under these terms ends immediately. If your company makes such a claim, your patent license ends immediately for work on behalf of your company.

Violations
The first time you are notified in writing that you have violated any of these terms, or done anything with the software not covered by your licenses, your licenses can nonetheless continue if you come into full compliance with these terms, and take practical steps to correct past violations, within 32 days of receiving notice. Otherwise, all your licenses end immediately.

No Liability
As far as the law allows, the software comes as is, without any warranty or condition, and the licensor will not be liable to you for any damages arising out of these terms or the use or nature of the software, under any kind of legal claim.

Definitions
The licensor is the individual or entity offering these terms, and the software is the software the licensor makes available under these terms.

You refers to the individual or entity agreeing to these terms.

Your company is any legal entity, sole proprietorship, or other kind of organization that you work for, plus all organizations that have control over, are under the control of, or are under common control with that organization. Control means ownership of substantially all the assets of an entity, or the power to direct its management and policies by vote, contract, or otherwise. Control can be direct or indirect.

Your licenses are all the licenses granted to you for the software under these terms.

Use means anything you do with the software requiring one of your licenses.
'''


class TeamknittLicensingTests(unittest.TestCase):
    def test_operative_clauses_match_the_user_supplied_terms(self):
        text = (ROOT / "LICENSE").read_text()
        operative = text[text.index("\nAcceptance\n") + 1:]
        self.assertEqual(" ".join(operative.split()), " ".join(USER_TERMS.split()))

    def test_current_licence_identity_and_authorship_match_package_metadata(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        text = (ROOT / "LICENSE").read_text()
        self.assertTrue(text.startswith(NAME + "\n"))
        self.assertIn("SPDX-License-Identifier: " + IDENTIFIER, text)
        self.assertIn("Copyright (c) 2026 Pioneertown B.V.", text)
        self.assertIn("Licensor: Pioneertown B.V.", text)
        self.assertIn("Author: Goran Mitevski.", text)
        self.assertIn("Software: teamknitt.", text)
        self.assertEqual(project["license"], IDENTIFIER)
        self.assertEqual(project["license-files"], ["LICENSE", "LICENSING.md"])
        self.assertEqual(project["version"], __version__)
        self.assertNotEqual(__version__, "0.7.0")  # Published copies are not relabelled in place.

    def test_bundled_legal_copies_and_provenance_are_byte_identical(self):
        starter = ROOT / "src/teamknitt/engine/resources/starter/project"
        for name in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
            self.assertEqual((starter / name).read_bytes(), (ROOT / name).read_bytes())

    def test_all_new_workspace_types_receive_current_terms_without_network_calls(self):
        factories = {name: (lambda path, kind=name: init_workspace(path, template=kind))
                     for name in ("text", "memory", "scientist", "multi-lab")}
        factories.update(task=lambda path: init_team(path, count=1),
                         research=lambda path: init_team(path, template="research"),
                         probes=init_probes, collection=lambda path: init_teams(path, count=1))
        with tempfile.TemporaryDirectory() as temp, patch("urllib.request.urlopen", side_effect=AssertionError("No network")), patch("teamknitt.engine.study.api_key", side_effect=AssertionError("No credentials")):
            for name, factory in factories.items():
                with self.subTest(workspace=name):
                    path = Path(temp) / name
                    result = factory(path)
                    self.assertEqual(result["api_calls"], 0)
                    for legal in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
                        self.assertEqual((path / legal).read_bytes(), (ROOT / legal).read_bytes())
                    readme = (path / "README.md").read_text()
                    self.assertIn(NAME, " ".join(readme.split()))
                    self.assertIn("Goran Mitevski", readme)
                    self.assertIn("Pioneertown B.V.", readme)
                    self.assertNotIn("World Bank", readme)
                    self.assertNotIn("Labtune Academic Research License", readme)

    def test_existing_workspace_legal_files_are_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "previous-workspace"
            init_team(path, count=1)
            for name in ("LICENSE", "LICENSING.md"):
                (path / name).write_text("PREVIOUS_WORKSPACE_TERMS: " + name)
            before = {p: p.read_bytes() for p in path.rglob("*") if p.is_file()}
            with self.assertRaises(ValueError):
                init_team(path, count=1)
            self.assertEqual(before, {p: p.read_bytes() for p in path.rglob("*") if p.is_file()})

    def test_current_documentation_does_not_restore_the_old_eligibility_rules(self):
        paths = ["README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSING.md", "PROVENANCE.md",
                 "docs/TEAMKNITT.md", "docs/TEAM_RESEARCH.md", "docs/MULTI_TEAM.md",
                 "examples/task_team/README.md", "examples/research_cognition/README.md",
                 "examples/teammate_probes/README.md", "examples/multi_team/README.md"]
        for name in paths:
            with self.subTest(path=name):
                text = (ROOT / name).read_text()
                self.assertIn(NAME, " ".join(text.split()))
                self.assertNotIn("Labtune Academic Research License 2.0", text)
                self.assertNotIn("LicenseRef-Labtune-Academic-Research-2.0", text)
                self.assertNotIn("World Bank", text)
                self.assertNotIn("low-income", text)
        guide = (ROOT / "LICENSING.md").read_text()
        self.assertIn("regardless of the source of funding or obligations resulting from the funding", guide)
        self.assertIn("within 32 days of receiving notice", guide)
        self.assertIn("even for a noncommercial purpose", guide)
        self.assertIn("not an OSI open-source licence", guide)

    def test_all_viewer_notices_name_the_current_licence(self):
        for name in ("observatory.html", "teams.html", "probes-observatory.html"):
            with self.subTest(viewer=name):
                text = resource(name).read_text()
                self.assertIn(NAME, " ".join(text.split()))
                self.assertNotIn("Labtune Academic Research License", text)
        text = resource("observatory.html").read_text()
        self.assertIn("does not grant redistribution, software changes or derivative works", text)

    def test_contribution_guide_does_not_offer_excluded_modification_rights(self):
        text = (ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("obtain separate written", text)
        self.assertIn("does **not** grant permission to redistribute", text)
        self.assertNotIn("Contributions must be offered under", text)
        self.assertIn("No copyright assignment or additional licence", text)


if __name__ == "__main__":
    unittest.main()
