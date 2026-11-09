"""Regression guards for the clarified Labtune-based policy, not a legal eligibility engine."""
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
NAME = "Teamknitt Noncommercial and Research Licence 2.0"
IDENTIFIER = "LicenseRef-Teamknitt-Noncommercial-Research-2.0"


def words(text):
    return " ".join(text.split())


class TeamknittLicensingTests(unittest.TestCase):
    def licence(self):
        return words((ROOT / "LICENSE").read_text())

    def test_current_identity_and_authorship_match_package_metadata(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        text = (ROOT / "LICENSE").read_text()
        self.assertTrue(text.startswith(NAME + "\n"))
        for phrase in ("SPDX-License-Identifier: " + IDENTIFIER, "Copyright (c) 2026 Pioneertown B.V.",
                       "Licensor: Pioneertown B.V.", "Author: Goran Mitevski.", "Software: teamknitt, based on Labtune."):
            self.assertIn(phrase, text)
        self.assertEqual(project["license"], IDENTIFIER)
        self.assertEqual(project["license-files"], ["LICENSE", "LICENSING.md"])
        self.assertEqual(project["version"], __version__)
        self.assertEqual(__version__, "0.9.0")

    def test_research_exception_overrides_free_general_noncommercial_use(self):
        text = self.licence()
        for phrase in (
            "noncommercial use that is not Research Use",
            "The research conditions override the general noncommercial permission.",
            "Research Use outside those conditions requires separate written permission even if it is noncommercial",
            "No organization receives a research exemption merely because it is educational, charitable, nonprofit, public or governmental.",
            "Research cannot be reclassified as ordinary noncommercial use",
            "Commercial Use requires a separate written licence before it begins.",
            "noncommercial Research Use outside the qualifying academic and geographic conditions",
        ):
            self.assertIn(phrase, text)
        guide = words((ROOT / "LICENSING.md").read_text())
        self.assertIn("Noncommercial research outside qualifying low-income/lower-middle-income academic institutions requires separate written permission.", guide)
        self.assertIn("Ordinary learning or software testing is not automatically research", guide)

    def test_labtune_research_eligibility_geography_and_independence_are_retained(self):
        text = self.licence()
        for phrase in (
            "public or nonprofit university", "legally recognized", "genuinely headquartered in a Qualifying Economy",
            "principal educational and academic-research operations there", "independent academic governance",
            "currently enrolled student, faculty or staff member, or formally appointed researcher",
            "acting solely on behalf of an Eligible Academic Institution", "World Bank's official Country and Lending Groups",
            "low-income or lower-middle-income", "income classification in force at the time of use",
            "Upper-middle-income, high-income and unclassified economies do not qualify",
            "A local registration, postal address, campus, affiliate or intermediary does not make",
            "retain control of the research agenda, conduct and results and freedom to publish",
            "company research lab", "for-profit educational institution", "commercial subsidiary or spinout",
            "Controlled by a Commercial Entity", "commissioned company research", "privileged commercial benefits",
            "Eligible institutions must not lend or extend their permission to others",
        ):
            self.assertIn(phrase, text)

    def test_research_donations_and_continuing_eligibility_remain_strict(self):
        text = self.licence()
        for phrase in (
            "only as a genuinely unrestricted donation", "No linked agreement, side arrangement or indirect condition",
            "Control or direction", "commissioned research, dedicated research capacity",
            "exclusive, preferential or advance access", "ownership, a licence, an option, first refusal",
            "publication veto, approval right", "Passing support through a foundation",
            "A donation cannot make an otherwise excluded project or organization eligible",
            "A purchase gives the supplier no independent right", "Research eligibility must hold throughout each use",
            "free permission for further Research Use ends", "general noncommercial grant is not a fallback research licence",
            "substantiate research eligibility with reasonable evidence",
        ):
            self.assertIn(phrase, text)

    def test_modification_and_sharing_are_conditionally_granted_not_blanket_prohibited(self):
        text = self.licence()
        for phrase in (
            "worldwide, nonexclusive, royalty-free copyright licence",
            "use, execute, copy, study, modify and share original or modified copies",
            "You may copy, modify and share the Software for Permitted Uses without charging a licence fee",
            "include this licence and LICENSING.md", "Identify your changes",
            "Changes to the Software that you distribute must be offered under these same terms",
            "You must not remove or weaken", "directly from its copyright holders only for their own Permitted Uses",
            "Permission to modify or share is not permission for Commercial Use or ineligible Research Use",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("other than distributing the software or making changes", text)

    def test_style_example_does_not_replace_labtune_termination_and_reserved_rights(self):
        text = self.licence()
        for phrase in ("binding obligations and conditions", "Rights not expressly granted are reserved",
                       "fair use", "end automatically if you breach", "Reinstatement requires written permission",
                       "no automatic notice, cure period or reinstatement is promised", '"as is" and "as available"',
                       "No copyright holder or contributor is liable"):
            self.assertIn(phrase, text)
        for phrase in ("Patent License", "Patent Defense", "within 32 days", "regardless of the source of funding or obligations"):
            self.assertNotIn(phrase, text)

    def test_earlier_grants_outputs_and_third_party_rights_are_not_rewritten(self):
        text = self.licence()
        for phrase in ("do not purport to revoke or rewrite permissions already granted",
                       "including Teamknitt Noncommercial Licence 1.0", "does not change the separate Labtune upstream licence",
                       "only rights that holder has authority to grant", "Identified third-party material remains subject to its own terms",
                       "does not claim rights in independently created inputs, data, findings or outputs",
                       "dependency", "does not pay their fees"):
            self.assertIn(phrase.lower(), text.lower())

    def test_bundled_legal_copies_and_provenance_are_byte_identical(self):
        starter = ROOT / "src/teamknitt/engine/resources/starter/project"
        for name in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
            self.assertEqual((starter / name).read_bytes(), (ROOT / name).read_bytes())

    def test_all_new_workspace_types_receive_current_terms_without_network_calls(self):
        factories = {name: (lambda path, kind=name: init_workspace(path, template=kind))
                     for name in ("text", "memory", "scientist", "multi-lab")}
        factories.update(task=lambda path: init_team(path, count=1), research=lambda path: init_team(path, template="research"),
                         probes=init_probes, collection=lambda path: init_teams(path, count=1))
        with tempfile.TemporaryDirectory() as temp, patch("urllib.request.urlopen", side_effect=AssertionError("No network")), patch("teamknitt.engine.study.api_key", side_effect=AssertionError("No credentials")):
            for name, factory in factories.items():
                with self.subTest(workspace=name):
                    path = Path(temp) / name
                    self.assertEqual(factory(path)["api_calls"], 0)
                    for legal in ("LICENSE", "LICENSING.md", "PROVENANCE.md"):
                        self.assertEqual((path / legal).read_bytes(), (ROOT / legal).read_bytes())
                    readme = words((path / "README.md").read_text())
                    self.assertIn(NAME, readme)
                    self.assertIn("Goran Mitevski", readme)
                    self.assertIn("Pioneertown B.V.", readme)
                    self.assertIn("research outside qualifying low-income/lower-middle-income academic institutions requires separate", readme.lower())
                    self.assertIn("Permitted Uses", readme)

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

    def test_current_notices_explain_the_exception_and_conditional_rights(self):
        paths = ["README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSING.md", "PROVENANCE.md",
                 "docs/TEAMKNITT.md", "docs/TEAM_RESEARCH.md", "docs/MULTI_TEAM.md",
                 "examples/task_team/README.md", "examples/research_cognition/README.md",
                 "examples/teammate_probes/README.md", "examples/multi_team/README.md"]
        for name in paths:
            with self.subTest(path=name):
                text = words((ROOT / name).read_text())
                self.assertIn(NAME, text)
                self.assertIn("research", text.lower())
                self.assertIn("separate", text.lower())
                self.assertNotIn("regardless of funding source or resulting obligations", text)
                self.assertNotIn("There is no geographic or academic-only eligibility test", text)
                self.assertNotIn("does **not** grant redistribution, software changes or derivative works", text)
        for name in ("observatory.html", "teams.html", "probes-observatory.html"):
            with self.subTest(viewer=name):
                self.assertIn(NAME, resource(name).read_text())
        text = resource("observatory.html").read_text()
        self.assertIn("research outside qualifying low-income/lower-middle-income academic institutions requires separate permission", text)
        self.assertIn("Modification and sharing are conditionally allowed for Permitted Uses", text)

    def test_contribution_guide_allows_permitted_changes_without_universal_prepermission(self):
        text = words((ROOT / "CONTRIBUTING.md").read_text())
        self.assertIn("permits use, study, copying, modification and sharing for Permitted Uses", text)
        self.assertIn("distribute software changes under the same terms", text)
        self.assertIn("Separate permission is required only where the proposed use is outside the grants", text)
        self.assertIn("no copyright assignment is implied", text)


if __name__ == "__main__":
    unittest.main()
