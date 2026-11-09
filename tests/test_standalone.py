"""Self-contained engine, grouped views, explicit migration and removed analysis guards."""
import ast
import asyncio
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from teamknitt.engine.config import ConfigurationError, validate_config, load_config, parse_yaml
from teamknitt.engine.cli import main as engine_main
from teamknitt.config import load, compile_plan, digest
from teamknitt.compat import PLAN_ALIASES
from teamknitt.reporting import build_report
from teamknitt.runtime import run
from teamknitt.scaffold import init
from teamknitt.migration import migrate
from teamknitt.views import GROUPS, VIEWS, resolve_view

ROOT = Path(__file__).resolve().parents[1]


class StandaloneEngineTests(unittest.TestCase):
    def test_distribution_owns_one_namespace_and_one_console_command(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
        self.assertEqual(project['project']['scripts'], {'teamknitt': 'teamknitt.cli:main'})
        self.assertEqual(project['tool']['setuptools']['packages']['find']['include'], ['teamknitt*'])
        self.assertNotIn('bayesian', project['project']['optional-dependencies'])
        self.assertFalse((ROOT / 'src/labtune').exists())
        self.assertFalse((ROOT / 'src/teamknitt/engine/priors.py').exists())
        self.assertFalse((ROOT / 'src/teamknitt/engine/schemas/prior_protocol.schema.json').exists())

    def test_runtime_has_no_upstream_imports_or_subprocess_delegation(self):
        for path in (ROOT / 'src/teamknitt').rglob('*.py'):
            if '__pycache__' in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith('labtune'), str(path))
                if isinstance(node, ast.Import):
                    self.assertTrue(all(not a.name.startswith('labtune') for a in node.names), str(path))
        result = subprocess.run([sys.executable, '-c', '''
import importlib.abc, sys, tempfile, asyncio
from pathlib import Path
class RejectUpstream(importlib.abc.MetaPathFinder):
    def find_spec(self, name, *args):
        if name == "labtune" or name.startswith("labtune."):
            raise AssertionError("Upstream import forbidden: " + name)
sys.meta_path.insert(0, RejectUpstream())
from teamknitt.scaffold import init
from teamknitt.runtime import run
from teamknitt.reporting import build_report
with tempfile.TemporaryDirectory() as d:
    root=Path(d)/"team"
    init(root,goal="Explore workshop ideas.")
    r=asyncio.run(run(root))
    assert r["provider_requests"] == 0
    assert "engine_variant" in r
    report=build_report(Path(r["run_directory"]))
    assert set(report["view_groups"]) == {"standard", "complexity"}
print("independent engine exercised")
'''], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('independent engine exercised', result.stdout)

    def test_removed_analysis_is_rejected_without_mutating_config_or_selecting_frequentist(self):
        base = load_config(ROOT)
        for mode in ('bayesian', 'probabilistic'):
            c = deepcopy(base)
            c['statistics']['approach'] = mode
            before = deepcopy(c)
            with self.assertRaisesRegex(ConfigurationError, 'No statistical method was changed'):
                validate_config(c)
            self.assertEqual(c, before)
        for malformed in ([], {'method': 'invented'}):
            c = deepcopy(base)
            c['statistics']['approach'] = malformed
            before = deepcopy(c)
            with self.assertRaises(ConfigurationError):
                validate_config(c)
            self.assertEqual(c, before)
        c = deepcopy(base)
        c['statistics']['prior_records'] = {'run_false_alarm': 'private:old-review'}
        with self.assertRaises(ConfigurationError):
            validate_config(c)

    def test_old_prior_command_cannot_be_called_through_standalone_engine(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                engine_main(['priors', 'check'])
        self.assertEqual(caught.exception.code, 2)

    def test_two_explanatory_families_not_a_statistical_method_selector(self):
        self.assertEqual(set(GROUPS), {'standard', 'complexity'})
        self.assertEqual(VIEWS['collaborative_intelligence']['group'], 'standard')
        self.assertEqual(VIEWS['shared_models']['group'], 'standard')
        for key in ('distributed_problem_solving', 'team_dynamics', 'interaction_coordination'):
            self.assertEqual(VIEWS[key]['group'], 'complexity')
        self.assertNotIn('cognition', VIEWS)
        self.assertNotIn('bayesian', VIEWS)
        self.assertNotIn('probabilistic', VIEWS)
        self.assertEqual(resolve_view('standard')[1], 'collaborative_intelligence')
        self.assertEqual(resolve_view('complexity')[1], 'distributed_problem_solving')
        self.assertIn('split', resolve_view(legacy='cognition')[2])
        with self.assertRaises(ConfigurationError):
            resolve_view('standard', 'team_dynamics')


class LegacyWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'team'
        init(self.root, template='research', goal='Compare alternative workshop explanations.')
        c = parse_yaml((self.root / 'team.yaml').read_text())
        c['labtune'] = c.pop('engine')
        c['cognition']['perspectives'] = ['distributed_cognition' if p == 'distributed_problem_solving' else p for p in c['cognition']['perspectives']]
        (self.root / 'team.yaml').write_text(json.dumps(c))
        (self.root / 'engine.py').unlink()
        (self.root / 'lab.py').write_text('from labtune.cli import main\n# Run python lab.py prepare\n')
        s = parse_yaml((self.root / 'study.yaml').read_text())
        s['provider']['model'] = 'explicit-user-model'
        s['provider']['api_key_env'] = 'LABTUNE_API_KEY'
        s['base_overrides']['budget']['max_llm_calls'] = 9
        (self.root / 'study.yaml').write_text(json.dumps(s))
        (self.root / '.env').write_text('LABTUNE_API_KEY=PRIVATE_LOCAL_SENTINEL\n')

    def files(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_legacy_names_are_read_without_model_budget_or_credential_changes(self):
        before = self.files()
        c = load(self.root)
        self.assertIn('engine', c)
        self.assertNotIn('labtune', c)
        self.assertIn('distributed_problem_solving', c['cognition']['perspectives'])
        p = compile_plan(self.root)
        self.assertEqual(p['provider_request_cap'], 9)
        self.assertEqual(p['engine_plan']['generation_provider']['model'], 'explicit-user-model')
        self.assertEqual(self.files(), before)

    def test_migration_is_draft_only_by_default_and_apply_backs_up_private_originals(self):
        before = self.files()
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No credential reads')):
            draft = migrate(self.root)
        self.assertEqual(draft['status'], 'migration_draft_only')
        self.assertEqual(self.files(), before)
        result = migrate(self.root, apply=True)
        backup = Path(result['backup'])
        self.assertEqual((backup / 'team.yaml').read_bytes(), before['team.yaml'])
        self.assertEqual((backup / 'lab.py').read_bytes(), before['lab.py'])
        self.assertEqual((backup / 'team.yaml').stat().st_mode & 0o777, 0o600)
        for name in ('study.yaml', '.env', 'mission/problem.md'):
            self.assertEqual((self.root / name).read_bytes(), before[name])
        self.assertFalse((self.root / 'lab.py').exists())
        self.assertIn('teamknitt.engine.cli', (self.root / 'engine.py').read_text())
        self.assertNotIn('labtune', parse_yaml((self.root / 'team.yaml').read_text()))

    def test_migration_never_converts_a_bayesian_study(self):
        p = self.root / 'study.yaml'
        s = parse_yaml(p.read_text())
        s['base_overrides']['statistics'] = {'approach': 'bayesian'}
        p.write_text(json.dumps(s))
        before = self.files()
        with self.assertRaises(ConfigurationError):
            migrate(self.root, apply=True)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.root / 'setup/teamknitt-migrations').exists())

    def test_migration_respects_run_lock_and_launcher_conflicts(self):
        import fcntl
        with (self.root / '.run.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(migrate(self.root)['status'], 'migration_draft_only')
            with self.assertRaisesRegex(ConfigurationError, 'run owns'):
                migrate(self.root, apply=True)
        (self.root / 'engine.py').write_text('# User launcher, do not overwrite\n')
        with self.assertRaises(ConfigurationError):
            migrate(self.root, apply=True)
        self.assertEqual((self.root / 'engine.py').read_text(), '# User launcher, do not overwrite\n')

    def test_legacy_record_binding_is_verified_before_read_only_name_normalization(self):
        # Generate a local fixture, then represent its binding in the pre-fork serialization.
        c = load(self.root)
        info = asyncio.run(run(self.root, c))
        folder = Path(info['run_directory'])
        plan_path = folder / 'team-plan.json'
        p = json.loads(plan_path.read_text())
        p['configuration']['labtune'] = p['configuration'].pop('engine')
        p['configuration']['cognition']['perspectives'] = ['distributed_cognition' if x == 'distributed_problem_solving' else x for x in p['configuration']['cognition']['perspectives']]
        binding = p['engine_plan']['configuration_snapshot']['cognition_binding']
        binding['labtune_sha256'] = binding.pop('engine_sha256')
        binding['cognition'] = deepcopy(p['configuration'])
        h = digest(binding)
        p['configuration_sha256'] = h
        for old, new in PLAN_ALIASES.items():
            p[old] = p.pop(new)
        plan_path.write_text(json.dumps(p))
        identity_path = folder / 'team-run.json'
        identity = json.loads(identity_path.read_text())
        identity['configuration_sha256'] = h
        identity_path.write_text(json.dumps(identity))
        before = {f.name: f.read_bytes() for f in folder.iterdir() if f.is_file()}
        report = build_report(folder)
        self.assertEqual(report['configuration_sha256'], h)
        self.assertTrue(report['compatibility']['legacy_names'])
        self.assertEqual(set(report['view_groups']), {'standard', 'complexity'})
        self.assertEqual(before, {f.name: f.read_bytes() for f in folder.iterdir() if f.is_file()})
        p['labtune_plan']['configuration_snapshot']['cognition_binding']['labtune_sha256'] = 'tampered'
        plan_path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ConfigurationError, 'binding'):
            build_report(folder)


if __name__ == '__main__':
    unittest.main()
