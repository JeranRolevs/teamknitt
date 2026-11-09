"""Direct product copy, compact research credit and a text-only wordmark."""
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import io
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
        self.assertIn(DESCRIPTION, text)
        self.assertIn('user-defined **tasks, brainstorming and goals**', text)
        self.assertNotIn('user-defined **tasks, brainstorming, goals and research**', text)
        page = html(plan_report(self.plan))
        self.assertIn('<h1 id="page-title" class="product-title">' + DESCRIPTION + '</h1>', page)
        for title in OLD_TITLES:
            self.assertNotIn(title, page)
        # Copy changes do not remove an explicitly supported advanced task purpose.
        self.assertIn('research', json.loads(resource('team.schema.json').read_text())['properties']['mission']['properties']['purpose']['enum'])

    def test_research_credit_is_a_follow_up_not_a_thesis_review(self):
        self.assertEqual(AUTHOR_RESEARCH['research_period'], '2022/2023')
        self.assertEqual(AUTHOR_RESEARCH['relation'], 'research_follow_up')
        self.assertIn('Goran Mitevski', AUTHOR_RESEARCH['connection'])
        self.assertIn('distributed teams', AUTHOR_RESEARCH['connection'])
        self.assertNotIn('mitevski_2023', SOURCES)
        self.assertEqual(set(AUTHOR_RESEARCH), {'author', 'research_period', 'relation', 'connection', 'focus', 'boundary'})
        public = json.dumps(AUTHOR_RESEARCH) + (ROOT / 'README.md').read_text() + (ROOT / 'docs/TEAM_RESEARCH.md').read_text()
        for detail in ('Detrended Fluctuation', 'Lyapunov', 'QuTeC', 'GRU', 'ARIMA', '12 January 2023', 'Mitevski, G. (2023).'):
            self.assertNotIn(detail, public)
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
        for name in ('README.md', 'PROVENANCE.md', 'docs/TEAM_RESEARCH.md', 'docs/TEAMKNITT.md'):
            text = (self.root / name).read_text()
            self.assertIn('2022/2023', text)
            self.assertIn('follow', text)
            self.assertNotIn('Detrended Fluctuation', text)
        provenance = (self.root / 'PROVENANCE.md').read_text()
        self.assertIn('Labtune 0.5.0', provenance)
        self.assertIn('software source baseline', provenance)
        self.assertIn('Pioneertown B.V.', provenance)

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
