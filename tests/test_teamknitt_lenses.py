"""More routing presets and complementary, non-evaluating overviews. No paid calls."""
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.config import ConfigurationError
from teamknitt.builder import make_configuration
from teamknitt.cli import main
from teamknitt.config import compile_plan, resource
from teamknitt.views import VIEWS, SOURCES, TEAMWORK, GROUPS, build_views, catalogue, load_probe_summary, with_views
from teamknitt.observatory import ViewerService, snapshot
from teamknitt.reporting import plan_report, build_report
from teamknitt.runtime import run
from teamknitt.scaffold import init
from teamknitt.topology import TOPOLOGIES, TOPOLOGY_CATALOG, links, members

ROOT = Path(__file__).resolve().parents[1]


class OverviewCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'team'
        init(self.root, goal='Explore accessible workshop formats.')
        self.plan = compile_plan(self.root)
        self.report = plan_report(self.plan)

    def fixture(self):
        info = asyncio.run(run(self.root, policy='fragmented'))
        return build_report(Path(info['run_directory']))

    def probe(self, *, selected=None):
        from teamknitt.probes.scaffold import init as probe_init
        from teamknitt.probes.config import load as probe_load
        from teamknitt.probes.runtime import run as probe_run
        root = Path(self.temp.name) / 'separate-probes'
        probe_init(root)
        config = probe_load(root)
        if selected is not None:
            config['protocol']['dimensions'] = selected
        info = asyncio.run(probe_run(root, config, policy='coordinated'))
        self.assertEqual(info['provider_requests'], 0)
        return Path(info['run_directory'])


class ExpandedTopologyTests(OverviewCase):
    def test_every_preset_has_exact_routes_for_every_supported_size(self):
        geometry = json.loads(resource('topology-layouts.json').read_text())
        self.assertEqual(len(TOPOLOGIES), 14)
        for n in range(1, 17):
            cols = math.ceil(math.sqrt(n))
            pods, remainder = divmod(n, 3)
            m = n - 1
            expected = {
                'fully_connected': n * (n - 1), 'hub_and_spoke': 2 * (n - 1),
                'ring': 0 if n == 1 else 2 if n == 2 else 2 * n,
                'hierarchical': 2 * (n - 1), 'chain': 2 * (n - 1),
                'directed_chain': n - 1, 'directed_ring': 0 if n == 1 else n,
                'wheel': 2 * m + (0 if m < 2 else 2 if m == 2 else 2 * m),
                'grid': 2 * (n - math.ceil(n / cols) + max(0, n - cols)),
                'clustered': 6 * pods + remainder * (remainder - 1) + 2 * (math.ceil(n / 3) - 1),
                'bipartite': 2 * math.ceil(n / 2) * (n // 2), 'broadcast': n - 1,
                'gather': n - 1, 'custom': 0,
            }
            for kind in TOPOLOGIES:
                with self.subTest(n=n, kind=kind):
                    routes = links({'topology': kind, 'members': n, 'links': []})
                    self.assertEqual(len(routes), expected[kind])
                    self.assertEqual(len(set(routes)), len(routes))
                    self.assertTrue(all(a != b and a in members(n) and b in members(n) for a, b in routes))
                    self.assertEqual([p['id'] for p in geometry[kind][str(n)]], members(n))
                    self.assertEqual(len({(p['x'], p['y']) for p in geometry[kind][str(n)]}), n)
                    self.assertTrue(all(0 <= p['x'] <= 1 and 0 <= p['y'] <= 1 for p in geometry[kind][str(n)]))

    def test_directional_presets_do_not_invent_replies(self):
        def routes(kind): return set(links({'topology': kind, 'members': 4, 'links': []}))
        self.assertEqual(routes('broadcast'), {('member.1', 'member.2'), ('member.1', 'member.3'), ('member.1', 'member.4')})
        self.assertEqual(routes('gather'), {(b, a) for a, b in routes('broadcast')})
        self.assertEqual(routes('directed_chain'), {('member.1', 'member.2'), ('member.2', 'member.3'), ('member.3', 'member.4')})
        self.assertEqual(routes('directed_ring'), routes('directed_chain') | {('member.4', 'member.1')})
        self.assertEqual(routes('chain'), routes('directed_chain') | {(b, a) for a, b in routes('directed_chain')})

    def test_grid_pods_and_partitions_follow_documented_member_order(self):
        grid = set(links({'topology': 'grid', 'members': 6, 'links': []}))
        self.assertNotIn(('member.3', 'member.4'), grid)  # no row wrap
        self.assertNotIn(('member.1', 'member.5'), grid)  # no diagonal
        self.assertIn(('member.1', 'member.4'), grid)
        pods = set(links({'topology': 'clustered', 'members': 9, 'links': []}))
        self.assertIn(('member.1', 'member.4'), pods)
        self.assertIn(('member.4', 'member.7'), pods)
        self.assertNotIn(('member.2', 'member.5'), pods)
        self.assertNotIn(('member.1', 'member.7'), pods)
        bipartite = set(links({'topology': 'bipartite', 'members': 5, 'links': []}))
        self.assertIn(('member.3', 'member.5'), bipartite)
        self.assertNotIn(('member.1', 'member.3'), bipartite)
        self.assertNotIn(('member.4', 'member.5'), bipartite)

    def test_catalog_schema_geometry_and_canonical_specs_agree(self):
        spec = importlib.util.spec_from_file_location('canonical_team_diagrams', ROOT / 'diagrams/specs.py')
        definitions = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(definitions)
        self.assertEqual(TOPOLOGY_CATALOG, definitions.TEAM_TOPOLOGIES)
        geometry = json.loads(resource('topology-layouts.json').read_text())
        choices = json.loads(resource('team.schema.json').read_text())['properties']['team']['properties']['topology']['enum']
        self.assertEqual(choices, list(TOPOLOGIES))
        for kind in TOPOLOGIES:
            for n in range(1, 17):
                self.assertEqual(geometry[kind][str(n)], definitions.team_topology_layout(kind, n))

    def test_all_presets_compile_without_selecting_models_or_raising_limits(self):
        for kind in TOPOLOGIES:
            for n in (1, 4, 16):
                with self.subTest(kind=kind, n=n):
                    p = compile_plan(self.root, make_configuration(topology=kind, count=n))
                    self.assertEqual(p['provider_request_cap'], 24)
                    self.assertEqual(p['engine_plan']['resources']['max_active_agents'], 6)
                    self.assertEqual(p['engine_plan']['generation_provider']['model'], 'YOUR_MODEL_ID')
                    self.assertEqual(p['topology']['kind'], kind)

    def test_new_draft_presets_do_not_write_files_or_start_models(self):
        service = ViewerService(self.report, workspace=self.root)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No keys')):
            for kind in TOPOLOGIES:
                r = service.draft({'topology': [kind], 'members': ['6']})
                self.assertEqual(r['topology']['kind'], kind)
                self.assertEqual(r['usage']['provider_requests'], 0)
                self.assertEqual(r['budget']['max_llm_calls'], 24)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


class ComplementaryLensTests(OverviewCase):
    def test_configuration_has_two_groups_and_focused_views_without_fake_observations(self):
        views = self.report['team_views']
        self.assertEqual(set(views), set(VIEWS))
        self.assertEqual(set(self.report['view_groups']), {'non_system', 'system'})
        self.assertEqual(self.report['view_groups']['non_system']['views'], ['collaborative_intelligence', 'shared_models'])
        self.assertIn('distributed_problem_solving', self.report['view_groups']['system']['views'])
        self.assertEqual(views['shared_models']['status'], 'configuration_only')
        self.assertIsNone(views['shared_models']['signals']['reported_plan_pair_agreement'])
        self.assertEqual(views['team_dynamics']['status'], 'not_observed')
        ci = views['collaborative_intelligence']
        self.assertEqual(len(ci['dimensions']), 8)
        self.assertIsNone(ci['team_capability_score'])
        self.assertTrue(all(d['status'] == 'not_evaluated' and d['protocol_evidence'] is None for d in ci['dimensions']))

    def test_sources_represent_wider_traditions_and_shared_models_are_not_the_whole_framework(self):
        notes = catalogue()
        self.assertFalse(notes['automatic_evaluation'])
        self.assertFalse(notes['switching_changes_configuration'])
        self.assertGreater(len(VIEWS['shared_models']['sources']), 1)
        self.assertGreater(len(VIEWS['team_dynamics']['sources']), 1)
        self.assertIn('Santa Fe', VIEWS['team_dynamics']['scope'])
        self.assertIn('not an endorsement', VIEWS['team_dynamics']['boundary'])
        self.assertEqual(VIEWS['shared_models']['group'], 'non_system')
        notes['views']['shared_models']['label'] = 'Changed copy'
        self.assertNotEqual(notes['views']['shared_models']['label'], VIEWS['shared_models']['label'])

    def test_real_process_metadata_is_not_relabelled_as_teammate_capability(self):
        r = self.fixture()
        ci = r['team_views']['collaborative_intelligence']
        self.assertGreater(ci['process_context']['artifact_exposures'], 0)
        self.assertIsNone(ci['team_capability_score'])
        self.assertTrue(all(d['status'] == 'not_evaluated' for d in ci['dimensions']))
        signals = r['team_views']['shared_models']['signals']
        self.assertLess(signals['reported_plan_pair_agreement'], 1)
        self.assertGreater(signals['perceived_in_sync_reports'], 0)
        self.assertGreater(signals['perceived_in_sync_despite_reported_disagreement'], 0)
        self.assertIsNone(r['goal_achieved'])

    def test_view_projection_does_not_mutate_config_observations_or_statistical_choices(self):
        r = self.fixture()
        before = deepcopy(r)
        views = build_views(r)
        views['team_dynamics']['observations']['dimensions'].clear()
        self.assertEqual(r, before)
        self.assertEqual(r['statistics'], self.report['statistics'])

    def test_disabled_or_unselected_dynamics_do_not_fabricate_an_exposure_graph(self):
        c = deepcopy(self.plan['configuration'])
        c['observations']['enabled'] = False
        r = plan_report(compile_plan(self.root, c))
        self.assertEqual(r['team_views']['team_dynamics']['status'], 'disabled')
        self.assertEqual(r['team_views']['team_dynamics']['observations']['dimensions'], [])
        c['observations'] = {'enabled': True, 'dimensions': ['fractals']}
        r = plan_report(compile_plan(self.root, c))
        self.assertEqual([d['id'] for d in r['team_views']['team_dynamics']['observations']['dimensions']], ['fractals'])
        self.assertEqual(r['team_views']['team_dynamics']['observations']['dimensions'][0]['status'], 'not_estimated')

    def test_explicit_saved_fixture_is_separate_context_not_model_evidence(self):
        path = self.probe()
        raw_path = path / 'run.json'
        raw = json.loads(raw_path.read_text())
        raw['private_fact'] = 'PRIVATE_SENTINEL_DO_NOT_EXPORT'
        raw['episodes'][0]['private_message'] = 'PRIVATE_SENTINEL_DO_NOT_EXPORT'
        raw_path.write_text(json.dumps(raw))
        summary = load_probe_summary(path)
        self.assertEqual(summary['scope'], 'separate_protocol_record')
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(summary))
        self.assertNotIn('episodes', summary)
        self.assertNotIn('overall_score', summary)
        r = with_views(self.report, summary)
        ci = r['team_views']['collaborative_intelligence']
        self.assertTrue(all(d['status'] == 'fixture_only' for d in ci['dimensions']))
        self.assertIsNone(ci['team_capability_score'])
        self.assertEqual(r['configuration_sha256'], self.report['configuration_sha256'])
        service = ViewerService(r, workspace=self.root, initial_lens='collaborative_intelligence', probe_summary=summary)
        changed = service.draft({'members': ['6'], 'topology': ['grid']})
        self.assertEqual(changed['team_views']['collaborative_intelligence']['probe_summary'], summary)
        self.assertEqual(changed['budget']['max_llm_calls'], 24)
        self.assertIn('Separate protocol context', summary['binding'])

    def test_nonselected_and_missing_protocol_dimensions_remain_unknown(self):
        path = self.probe(selected=['information'])
        value = json.loads((path / 'run.json').read_text())
        value['episodes'] = []
        (path / 'run.json').write_text(json.dumps(value))
        summary = load_probe_summary(path)
        ci = with_views(self.report, summary)['team_views']['collaborative_intelligence']
        by_id = {d['id']: d for d in ci['dimensions']}
        self.assertEqual(by_id['conflict']['status'], 'not_selected')
        self.assertIsNone(by_id['information']['protocol_evidence']['test_score'])
        self.assertGreater(summary['coverage']['missing_or_failed_episode_count'], 0)
        summary['mode'] = 'live'  # Test projection semantics only, not a claim about this fixture.
        live = build_views(self.report, summary)['collaborative_intelligence']
        self.assertEqual(next(d for d in live['dimensions'] if d['id'] == 'information')['status'], 'incomplete_or_ineligible')

    def test_cli_lens_listing_and_offline_snapshot_never_call_providers(self):
        before = (self.root / 'team.yaml').read_bytes()
        output = Path(self.temp.name) / 'overview.html'
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No keys')), redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(['lenses']), 0)
            self.assertEqual(json.loads(stream.getvalue())['api_calls'], 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['view', '--workspace', str(self.root), '--lens', 'complexity', '--output', str(output)]), 0)
        self.assertIn('"initial_group": "system"', output.read_text())
        self.assertIn('"live": false', output.read_text())
        self.assertEqual(before, (self.root / 'team.yaml').read_bytes())
        self.assertFalse((self.root / 'trials').exists())
        with self.assertRaises(ConfigurationError):
            ViewerService(self.report, initial_lens='unrequested-evaluator')

    def test_attached_probe_symlinks_are_rejected_and_sources_remain_local(self):
        target = Path(self.temp.name) / 'link.json'
        target.symlink_to(self.root / 'team.yaml')
        with self.assertRaises(ConfigurationError):
            load_probe_summary(target)
        output = Path(self.temp.name) / 'safe.html'
        snapshot(self.report, output)
        self.assertIn('not_evaluated', output.read_text())
        self.assertNotIn('Foundations.pdf', output.read_text())


if __name__ == '__main__':
    unittest.main()
