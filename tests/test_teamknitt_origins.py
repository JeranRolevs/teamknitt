"""Direct product copy, compact research credit and a text-only wordmark."""
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.cli import main
from teamknitt.config import compile_plan, resource
from teamknitt.human_teams import AUTHOR_RESEARCH
from teamknitt.observatory import html
from teamknitt.reporting import build_report, plan_report
from teamknitt.runtime import run
from teamknitt.scaffold import init
from teamknitt.views import SOURCES, catalogue

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTION = 'Teamknitt is a tool for configuring AI agent team/s, where we can set the task, follow the work in different modes, and intervene.'
README_DESCRIPTION = 'Teamknitt supports human-led improvement of AI-agent team/s. Configure AI agent team/s, set the task or goal, observe and follow the work in different modes, intervene.'
README_FOLLOW_UP = 'Teamknitt follows my thesis research on distributed teams and new tools for configuring and refining collaboration in hybrid teams of people and machine-learning agents.'
FOLLOW_UP = 'Teamknitt follows my thesis research on distributed teams and their creative processes.'
RESEARCH_NOTE_SHA256 = '1986c98d50464e902e84e5ae51461e68f3b5249c4adceb968eb3de3a240b6e15'
OLD_TITLES = ('A team for what you have in mind.', 'Where contributions connect.',
              'Different explanations. One team.', 'Intervene with intention.', 'Complexity, observed with care.')


class ResearchOriginsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'team'
        init(self.root, goal='Explore accessible workshop formats.')
        self.plan = compile_plan(self.root)

    def files(self, root=None):
        root = root or self.root
        return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_requested_title_and_task_description(self):
        text = (ROOT / 'README.md').read_text()
        self.assertTrue(text.startswith('# teamknitt\n\n### ' + README_DESCRIPTION + '\n'))
        self.assertIn('user-defined tasks, brainstorming and goals', text)
        self.assertIn('Based on the approach I developed for Labtune.', text)
        self.assertIn(README_FOLLOW_UP, text)
        self.assertIn('[Research background](docs/TEAM_RESEARCH.md#research-follow-up)', text)
        self.assertIn('Teamknitt ships its own runtime under `teamknitt.engine`;', text)
        self.assertIn('Goran Mitevski', text)
        self.assertIn('Pioneertown B.V.', text)
        page = html(plan_report(self.plan))
        self.assertIn('<h1 id="page-title" class="product-title">' + DESCRIPTION + '</h1>', page)
        for title in OLD_TITLES:
            self.assertNotIn(title, page)
        # Copy changes do not remove an explicitly supported advanced task purpose.
        self.assertIn('research', json.loads(resource('team.schema.json').read_text())['properties']['mission']['properties']['purpose']['enum'])

    def test_readme_research_passages_use_the_authors_voice(self):
        text = ' '.join((ROOT / 'README.md').read_text().split())
        self.assertIn(README_FOLLOW_UP, text)
        self.assertIn('I use **non-system and system explanations** to organize the team views.', text)
        self.assertIn('**compositional and compilational emergence**', text)
        self.assertIn('**processes, states and outcomes**', text)
        self.assertIn('IPO and IMOI include feedback and conditional relationships', text)
        self.assertIn('does not infer interpersonal processes or psychological states', text)
        self.assertNotIn("Goran's revised", text)
        self.assertNotIn('Statistical methods are not a third theory of teams.', text)
        # Requested deletion is copy only, not a statistical-mode change.
        self.assertIn('Bayesian/probabilistic analysis is not an option in teamknitt.', text)
        self.assertIn('supported frequentist count/interval analysis remain available when applicable', text)
        self.assertIn('Unsupported legacy choices are rejected, never silently converted.', text)
        self.assertIn('This does not change the original Labtune project.', text)

    def test_first_person_follow_up_is_consistent_in_public_guides_and_viewer(self):
        for name in ('docs/TEAMKNITT.md', 'docs/MULTI_TEAM.md',
                     'PROVENANCE.md', 'examples/task_team/README.md', 'examples/research_cognition/README.md',
                     'examples/teammate_probes/README.md', 'examples/multi_team/README.md'):
            with self.subTest(path=name):
                text = (ROOT / name).read_text()
                self.assertIn(FOLLOW_UP, ' '.join(text.split()))
                self.assertNotIn('follows up Goran', text)
                self.assertNotIn("Goran's revised", text)
        page = html(plan_report(self.plan))
        self.assertIn(FOLLOW_UP, page)
        self.assertNotIn('follows up Goran Mitevski', page)
        self.assertNotIn('It also follows up his', page)
        self.assertNotIn('third theory of teams', page)
        self.assertIn('Goran Mitevski', page)
        self.assertIn('2022/2023', page)

    def test_readme_matches_the_abstract_without_overstating_routing_or_evidence(self):
        from teamknitt.topology import TOPOLOGIES
        text = ' '.join((ROOT / 'README.md').read_text().split())
        self.assertIn('framework and source-available reference implementation', text)
        self.assertIn('teams of 1–16 LLM agents', text)
        self.assertIn('advanced engine workflows also support research missions', text)
        self.assertIn(f'{len(TOPOLOGIES) - 1} deterministic presets or a custom directed graph', text)
        self.assertIn(f'{len(TOPOLOGIES)} routing options in total', text)
        self.assertIn('without assuming that its findings transfer to LLM-agent teams', text)
        self.assertIn('Sources, scoped representations, work dependencies, handoffs', text)
        self.assertIn('shared understanding remain unmeasured', text)
        self.assertIn('Agreement in those records does not establish shared understanding or correctness', text)
        for stage in ('Between runs', 'Before a run', 'During a run'):
            self.assertIn('**' + stage + ':**', text)
        for claim in ('Queued', 'applied', 'assembled', 'understood', 'improved'):
            self.assertIn('**' + claim + '**', text)

    def test_research_guide_opens_with_research_and_keeps_licensing_separate(self):
        text = (ROOT / 'docs/TEAM_RESEARCH.md').read_text()
        opening = text.split('## What Teamknitt is for', 1)[0]
        normal = ' '.join(opening.split())
        self.assertTrue(opening.startswith('# Human-Team Research in Teamknitt\n'))
        self.assertIn('**Goran Mitevski · 10 November 2026**', opening)
        self.assertIn('human teams to guide how LLM-agent teams are configured', normal)
        self.assertIn('dynamical systems theory as a lens for following their work', normal)
        self.assertIn('It does not assume that findings about human teams transfer to LLM-agent teams', normal)
        for word in ('Licence', 'permission', 'copyright'):
            self.assertNotIn(word, opening)
        self.assertGreater(text.index('## Provenance and licence'), text.index('## Sources cited in this note'))
        footer = text.split('## Provenance and licence', 1)[1]
        self.assertIn('Pioneertown B.V.', footer)
        self.assertIn('Teamknitt Noncommercial and Research Licence 2.0', footer)
        self.assertIn('Noncommercial research outside qualifying low-income/lower-middle-income academic institutions', footer)
        self.assertIn('requires separate written permission', footer)
        self.assertIn('[LICENSE](../LICENSE)', footer)
        self.assertIn('[LICENSING.md](../LICENSING.md)', footer)

    def test_research_note_retains_author_supplied_detail_as_proposals_not_estimators(self):
        text = (ROOT / 'docs/TEAM_RESEARCH.md').read_text()
        section = text.split('## Research follow-up', 1)[1].split('## 1.', 1)[0]
        normal = ' '.join(section.split())
        self.assertIn('Teamknitt builds on my 2022/2023 thesis research at Tilburg University', normal)
        self.assertIn('tools for configuring and refining collaboration in hybrid teams', normal)
        self.assertIn('I extend that work to LLM-agent teams', normal)
        self.assertIn('The next research step is to test whether methods from complexity science', normal)
        self.assertIn('Whether any of this holds for LLM-agent teams', normal)
        self.assertIn('are both open questions', normal)
        self.assertIn('When these estimators are added', normal)
        self.assertIn('Teamknitt assigns no automatic quality score', normal)
        self.assertIn('*Not yet implemented.* Continuous time-series analysis', text)
        self.assertIn('fractal methods are research methods, not estimators present in the', text)
        self.assertIn('Attractors, synchrony, fractal scaling, emergence and adaptation are not estimated.', text)

    def test_product_research_credit_stays_brief_beside_the_detailed_research_note(self):
        self.assertEqual(AUTHOR_RESEARCH['research_period'], '2022/2023')
        self.assertEqual(AUTHOR_RESEARCH['relation'], 'research_follow_up')
        self.assertEqual(AUTHOR_RESEARCH['author'], 'Goran Mitevski')
        self.assertTrue(AUTHOR_RESEARCH['connection'].startswith(README_FOLLOW_UP))
        self.assertIn('collaboration in hybrid teams of people and machine-learning agents', AUTHOR_RESEARCH['connection'])
        self.assertIn('how work unfolds over time', AUTHOR_RESEARCH['connection'])
        self.assertIn('how people can intervene', AUTHOR_RESEARCH['connection'])
        self.assertIn('dynamical systems theory', AUTHOR_RESEARCH['connection'])
        self.assertIn('what carries over remains an open question', AUTHOR_RESEARCH['connection'])
        self.assertLess(len(AUTHOR_RESEARCH['connection']), 450)
        self.assertNotIn('mitevski_2023', SOURCES)
        self.assertEqual(set(AUTHOR_RESEARCH), {'author', 'research_period', 'relation', 'connection', 'focus', 'boundary'})
        # The explicit exception is for the authored technical note, not product summaries.
        product = json.dumps(AUTHOR_RESEARCH) + (ROOT / 'README.md').read_text() + html(plan_report(self.plan))
        for detail in ('Detrended Fluctuation', 'Lyapunov', 'QuTeC', 'GRU', 'ARIMA', '12 January 2023', 'Mitevski, G. (2023).'):
            self.assertNotIn(detail, product)
        self.assertNotRegex(json.dumps(AUTHOR_RESEARCH), r'(?i)student.?number|student.?id')

    def test_research_follow_up_does_not_infer_measurements_or_change_settings(self):
        report = plan_report(self.plan)
        self.assertEqual(report['research_background']['author_research']['relation'], 'research_follow_up')
        question = next(q for q in report['team_views']['team_dynamics']['conceptual_questions'] if q['concept'] == 'Creative-process dynamics')
        self.assertEqual(question['status'], 'not_estimated')
        self.assertIsNone(report['scientific_quality_score'])
        self.assertIsNone(report['goal_achieved'])
        self.assertEqual(report['statistics']['approach'], 'frequentist')
        self.assertEqual(report['generation_provider']['model'], 'YOUR_MODEL_ID')
        self.assertEqual(report['budget']['max_llm_calls'], 24)

    def test_theory_cli_and_report_projection_are_offline_and_nonmutating(self):
        before = self.files()
        original = deepcopy(self.plan)
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No credential read')), redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(['theory']), 0)
            report = plan_report(self.plan)
        notes = json.loads(stream.getvalue())
        self.assertEqual(notes['api_calls'], 0)
        self.assertFalse(notes['automatic_improvement'])
        self.assertEqual(notes['author_research'], report['research_background']['author_research'])
        notes['author_research']['focus'].clear()
        report['research_background']['author_research']['focus'].clear()
        self.assertEqual(len(catalogue()['research_background']['author_research']['focus']), 3)
        self.assertEqual(len(AUTHOR_RESEARCH['focus']), 3)
        self.assertEqual(self.plan, original)
        self.assertEqual(self.files(), before)

    def test_saved_process_records_are_not_rewritten_or_scored_as_creative(self):
        result = asyncio.run(run(self.root, policy='connected'))
        selected = Path(result['run_directory'])
        before = self.files(selected)
        report = build_report(selected)
        self.assertEqual(before, self.files(selected))
        self.assertEqual(report['mode'], 'offline_fixture')
        self.assertEqual(report['usage']['provider_requests'], 0)
        self.assertEqual(report['research_background']['author_research']['relation'], 'research_follow_up')
        self.assertIsNone(report['goal_achieved'])
        self.assertIsNone(report['observations']['aggregate_score'])

    def test_starters_preserve_source_and_research_lineage_and_legal_texts(self):
        for name in ('LICENSE', 'LICENSING.md', 'PROVENANCE.md'):
            self.assertEqual((self.root / name).read_bytes(), (ROOT / name).read_bytes())
        for name in ('README.md', 'PROVENANCE.md', 'docs/TEAMKNITT.md'):
            text = (self.root / name).read_text()
            self.assertIn(FOLLOW_UP, text)
            self.assertNotIn('follows up Goran', text)
            self.assertNotIn('Detrended Fluctuation', text)
        self.assertEqual((self.root / 'docs/TEAM_RESEARCH.md').read_bytes(), (ROOT / 'docs/TEAM_RESEARCH.md').read_bytes())
        provenance = (self.root / 'PROVENANCE.md').read_text()
        self.assertIn('2022/2023', provenance)
        self.assertIn('Goran Mitevski', provenance)
        self.assertIn('Labtune 0.5.0', provenance)
        self.assertIn('software source baseline', provenance)
        self.assertIn('Pioneertown B.V.', provenance)

    def test_author_approved_research_note_is_preserved_verbatim_in_source_and_starter(self):
        note = (ROOT / 'docs/TEAM_RESEARCH.md').read_bytes()
        self.assertEqual(hashlib.sha256(note).hexdigest(), RESEARCH_NOTE_SHA256)
        bundled = ROOT / 'src/teamknitt/engine/resources/starter/project/docs/TEAM_RESEARCH.md'
        self.assertEqual(note, bundled.read_bytes())
        text = note.decode('utf-8')
        self.assertIn('Mitevski, G. (2023).', text)
        self.assertIn('Detrended Fluctuation Analysis', text)
        self.assertIn('α ≈ 0.70', text)
        guidance = (ROOT / 'AGENTS.md').read_text()
        self.assertIn('Exception explicitly approved by the user', guidance)
        self.assertIn('This exception does not extend to README/UI/report summaries', guidance)

    def test_research_page_title_overview_and_credit_match_the_rewritten_note(self):
        page = html(plan_report(self.plan))
        self.assertIn("foundations:['RESEARCH BACKGROUND','Human-team research'", page)
        self.assertIn('Human-Team Research in Teamknitt', page)
        self.assertIn('RESEARCH NOTE / 10 NOVEMBER 2026 · GORAN MITEVSKI', page)
        self.assertIn('dynamical systems theory', page.lower())
        self.assertIn('maps those ideas to Teamknitt’s records and controls', page)
        self.assertIn('Dynamical analyses remain research proposals, not implemented estimators.', page)
        self.assertIn('Detailed research note: <code>docs/TEAM_RESEARCH.md</code>', page)
        self.assertNotIn("'Background and sources'", page)
        self.assertNotIn('BACKGROUND / 9 NOVEMBER 2026', page)
        notes = catalogue()['research_background']
        report = plan_report(self.plan)['research_background']
        for record in (notes, report):
            self.assertEqual(record['title'], 'Human-Team Research in Teamknitt')
            self.assertEqual(record['background_credit'], 'Goran Mitevski · 10 November 2026')
        self.assertFalse(notes['automatic_improvement'])
        self.assertEqual(notes['api_calls'], 0)

    def test_viewer_uses_a_short_follow_up_note(self):
        text = html(plan_report(self.plan))
        self.assertIn('id="author-research"', text)
        self.assertIn("viewCard('Research follow-up'", text)
        self.assertNotIn('thesis-details', text)
        self.assertNotIn('Study findings, limitations and proposed future directions', text)
        self.assertNotIn('Mitevski, G. (2023).', text)
        self.assertNotIn('Lyapunov', text)

    def test_wordmark_is_outlined_text_without_a_rectangle(self):
        text = resource('observatory.html').read_text()
        self.assertIn('background:transparent;border:0;outline:0;box-shadow:none;color:#ffda00', text)
        self.assertIn('-webkit-text-stroke:1.6px #6f4b2a;paint-order:stroke fill;padding:0', text)
        self.assertNotIn('.brand{display:inline-flex;background:#302e29', text)


if __name__ == '__main__':
    unittest.main()
