"""Explicit, bounded operator controls. All transports are local test doubles."""
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from teamknitt.cli import main
from teamknitt.config import compile_plan, load
from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.study import ControlledStop, save
from teamknitt.interventions import OperatorController, metadata, schedule, submit
from teamknitt.reporting import build_report, plan_report
from teamknitt.runtime import run
from teamknitt.scaffold import init
from teamknitt.views import GROUPS, SOURCES, VIEWS, catalogue, resolve_view


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'team'
        init(self.workspace, goal='Explore accessible workshop formats.')
        self.plan = compile_plan(self.workspace)
        self.events = []
        (self.workspace / 'mission/feedback.md').write_text('PRIVATE_FEEDBACK_SENTINEL Review assumptions and preserve alternatives. ' * 8)

    def active(self, name='test-run'):
        root = self.workspace / 'trials' / name
        root.mkdir(parents=True)
        save(root / 'team-plan.json', self.plan)
        save(root / 'team-run.json', {'run_id': name, 'configuration_sha256': self.plan['configuration_sha256']})
        save(root / 'summary.json', {'status': 'running'})
        control = OperatorController(root, self.plan, name, self.events.append)
        return root, control

    def bytes(self):
        return {p.relative_to(self.workspace): p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}

    def local_provider(self, cap=24):
        path = self.workspace / 'study.yaml'
        from teamknitt.engine.config import parse_yaml
        s = parse_yaml(path.read_text())
        s['provider'].update(model='injected-offline-transport', base_url='http://127.0.0.1:1', api_key_env=None)
        s.setdefault('base_overrides', {}).setdefault('budget', {})['max_llm_calls'] = cap
        path.write_text(json.dumps(s))

    def response(self):
        return {'choices': [{'message': {'content': json.dumps({'action': 'final', 'summary': 'Local fixture',
            'candidate_output': 'A contribution requiring human review.', 'findings': [], 'wisdom': []})}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}

    def current(self):
        return sorted((self.workspace / 'trials').iterdir())[-1]


class TheoryTests(Case):
    def test_axes_are_distinct_and_sources_are_complete(self):
        notes = catalogue()
        axes = notes['research_background']['axes']
        self.assertEqual(set(axes), {'explanatory_locus', 'form_of_emergence', 'kind_of_record'})
        self.assertEqual(set(GROUPS), {'non_system', 'system'})
        self.assertEqual(len(VIEWS), 6)
        self.assertIn('transactive_memory', GROUPS['system']['views'])
        for row in list(axes.values()) + notes['research_background']['constructs'] + notes['research_background']['interventions'] + list(VIEWS.values()):
            self.assertTrue(all(key in SOURCES for key in row.get('sources', [])))
        self.assertIn('Goran', notes['research_background']['background_credit'])
        self.assertFalse(notes['research_background']['automatic_improvement'])
        self.assertIn('compilational', VIEWS['transactive_memory']['scope'])

    def test_configurations_do_not_become_emergence_or_psychological_states(self):
        r = plan_report(self.plan)
        theory = r['research_background']
        self.assertEqual(theory['patterns']['status'], 'configured_patterns_not_estimated_emergence')
        self.assertEqual(theory['transfer_status'], 'design_hypotheses_not_validated_for_ai_teams')
        for row in theory['constructs']:
            if row['id'] not in {'shared_mental_models', 'transactive_memory'}:
                self.assertEqual(row['status'], 'not_measured')
        self.assertIsNone(r['team_views']['transactive_memory']['signals']['retrieval_effectiveness'])
        self.assertEqual({p['phase_type'] for p in theory['episode_cycle']['phases']}, {'transition', 'action', 'operational'})
        self.assertIsNone(theory['episode_cycle']['outcomes']['goal_achieved'])

    def test_legacy_display_groups_do_not_rewrite_team_configuration(self):
        before = self.bytes()
        self.assertEqual(resolve_view('standard', 'shared_models')[:2], ('non_system', 'shared_models'))
        self.assertEqual(resolve_view('complexity', 'team_dynamics')[:2], ('system', 'team_dynamics'))
        self.assertEqual(resolve_view(legacy='cognition')[:2], ('system', 'distributed_problem_solving'))
        self.assertEqual(before, self.bytes())
        with self.assertRaises(ConfigurationError):
            resolve_view('non_system', 'transactive_memory')

    def test_theory_cli_is_offline_nonmutating_and_not_a_statistics_choice(self):
        before = self.bytes()
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No credentials')), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['theory']), 0)
        self.assertEqual(json.loads(out.getvalue())['api_calls'], 0)
        self.assertEqual(before, self.bytes())
        self.assertEqual(compile_plan(self.workspace)['engine_plan']['statistics']['approach'], 'frequentist')


class QueueTests(Case):
    def test_all_requests_are_drafts_by_default_without_even_a_lock_write(self):
        root, _ = self.active()
        before = self.bytes()
        with patch('teamknitt.runtime.api_key', side_effect=AssertionError('No keys')):
            for action in ('pause', 'resume', 'stop', 'feedback'):
                kw = {'message_file': 'mission/feedback.md'} if action == 'feedback' else {}
                result = submit(root, action=action, **kw)
                self.assertEqual(result['status'], 'operator_request_draft_only')
                self.assertEqual(result['api_calls'], 0)
                self.assertFalse(result['models_permissions_or_budgets_changed'])
        self.assertEqual(before, self.bytes())
        self.assertNotIn('PRIVATE_FEEDBACK_SENTINEL', json.dumps(result))

    def test_queued_feedback_is_private_targeted_bounded_and_not_a_claim_of_understanding(self):
        root, control = self.active()
        receipt = submit(root, action='feedback', message_file='mission/feedback.md', actors=['member.1'], apply=True)
        self.assertEqual(receipt['request']['status'], 'queued_not_acknowledged')
        self.assertIsNone(control.frame('member.1', 2, 5))
        self.assertEqual(len(metadata(root, 'running')['pending']), 1)
        asyncio.run(control.before_wave(3, time.monotonic() + 2))
        self.assertIsNone(control.frame('member.2', 3, 5))
        frame = control.frame('member.1', 3, 5)
        self.assertEqual(len(frame['messages'][0]['content'].split()), 5)
        self.assertTrue(frame['messages'][0]['truncated'])
        public = metadata(root, 'running')
        self.assertFalse(public['pending'])
        self.assertEqual(public['receipts'][0]['status'], 'accepted_for_delivery_not_understood')
        self.assertEqual(public['feedback_exposures'][0]['words'], 5)
        self.assertNotIn('PRIVATE_FEEDBACK_SENTINEL', json.dumps(public) + json.dumps(self.events))
        for path in (root / 'operator').rglob('*'):
            if os.name == 'posix':
                self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)

    def test_pause_holds_boundary_resume_does_not_restart(self):
        root, control = self.active()
        submit(root, action='pause', apply=True)
        async def exercise():
            waiting = asyncio.create_task(control.before_wave(3, time.monotonic() + 3, poll_seconds=.01))
            for _ in range(100):
                if control.state['mode'] == 'paused':
                    break
                await asyncio.sleep(.01)
            self.assertFalse(waiting.done())
            self.assertEqual(metadata(root, 'running')['mode'], 'paused')
            submit(root, action='resume', apply=True)
            await asyncio.wait_for(waiting, 2)
        asyncio.run(exercise())
        self.assertEqual(control.state['mode'], 'running')
        self.assertEqual([r['action'] for r in control.state['receipts']], ['pause', 'resume'])
        self.assertTrue(all(r['boundary_wave'] == 3 for r in control.state['receipts']))

    def test_pause_never_extends_wall_time_limit(self):
        root, control = self.active()
        submit(root, action='pause', apply=True)
        with self.assertRaises(ControlledStop) as caught:
            asyncio.run(control.before_wave(2, time.monotonic() - .1))
        self.assertEqual(caught.exception.kind, 'wall_time_limit')
        self.assertEqual(control.state['stop_reason'], 'wall_time_limit')

    def test_stop_is_terminal_and_later_requests_are_not_applied(self):
        root, control = self.active()
        submit(root, action='stop', apply=True)
        submit(root, action='resume', apply=True)
        with self.assertRaises(ControlledStop):
            asyncio.run(control.before_wave(3, time.monotonic() + 3))
        control.close('stopped')
        self.assertEqual(control.state['receipts'][-1]['status'], 'not_applied_after_stop')
        self.assertFalse(metadata(root, 'stopped')['available'])
        with self.assertRaisesRegex(ConfigurationError, 'terminal'):
            submit(root, action='resume', apply=True)

    def test_final_wave_request_is_retained_as_not_applied(self):
        root, control = self.active()
        submit(root, action='feedback', message_file='mission/feedback.md', apply=True)
        control.close('completed')
        self.assertEqual(control.state['receipts'][0]['status'], 'not_applied_run_ended')
        self.assertFalse(metadata(root, 'completed')['pending'])
        self.assertFalse(control.feedback)

    def test_bound_requests_reject_other_runs_and_unknown_privilege_fields(self):
        root, control = self.active()
        second, other = self.active('different-run')
        submit(root, action='pause', apply=True)
        path = next((root / 'operator/requests').iterdir())
        (second / 'operator/requests' / path.name).write_bytes(path.read_bytes())
        asyncio.run(other.before_wave(3, time.monotonic() + 3))
        self.assertEqual(other.state['mode'], 'running')
        self.assertEqual(other.state['receipts'][0]['status'], 'rejected_invalid_request')
        value = json.loads(path.read_text()); value['budget'] = {'max_llm_calls': 9000}; path.write_text(json.dumps(value))
        asyncio.run(control.before_wave(3, time.monotonic() + 3))
        self.assertEqual(control.state['receipts'][0]['status'], 'rejected_invalid_request')
        self.assertEqual(control.state['mode'], 'running')

    def test_invalid_recipients_message_paths_and_nonfeedback_payloads_are_rejected(self):
        root, _ = self.active()
        for kwargs in ({'action': 'feedback', 'message_file': 'mission/feedback.md', 'actors': ['member.99']},
                       {'action': 'feedback', 'message_file': '../outside.md'},
                       {'action': 'feedback', 'message_file': '.env'},
                       {'action': 'feedback', 'message_file': 'trials/private.txt'},
                       {'action': 'feedback'}, {'action': 'pause', 'message_file': 'mission/feedback.md'},
                       {'action': 'resume', 'actors': ['member.1']}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ConfigurationError, OSError)):
                submit(root, apply=True, **kwargs)
        self.assertFalse(list((root / 'operator/requests').iterdir()))

    def test_queue_bounds_and_symlinks_do_not_silently_expand(self):
        root, control = self.active()
        with patch('teamknitt.interventions.MAX_PENDING', 1):
            submit(root, action='resume', apply=True)
            with self.assertRaisesRegex(ConfigurationError, 'queue is full'):
                submit(root, action='pause', apply=True)
        link = self.workspace / 'linked-run'; link.symlink_to(root, target_is_directory=True)
        with self.assertRaisesRegex(ConfigurationError, 'symlink'):
            submit(link, action='pause', apply=True)
        p = root / 'operator/requests' / ('1-' + 'a' * 32 + '.json'); p.symlink_to(self.workspace / 'mission/feedback.md')
        asyncio.run(control.before_wave(3, time.monotonic() + 3))
        self.assertEqual(control.state['mode'], 'running')
        self.assertIn('rejected_invalid_request', [r['status'] for r in control.state['receipts']])

    def test_old_records_have_no_new_control_authority(self):
        root = self.workspace / 'trials/legacy'; root.mkdir(parents=True)
        self.assertFalse(metadata(root, 'completed')['available'])
        before = self.bytes()
        with self.assertRaisesRegex(ConfigurationError, 'historical'):
            submit(root, action='resume', apply=True)
        self.assertEqual(before, self.bytes())


class ScheduleTests(Case):
    def disturbance(self):
        return {'id': 'reviewed-gap', 'kind': 'actor_unavailable', 'actor': 'member.1', 'at_wave': 4, 'duration': 1}

    def test_schedule_is_nonmutating_by_default_and_apply_keeps_other_choices(self):
        before = self.bytes()
        result = schedule(self.workspace, self.disturbance())
        self.assertEqual(result['status'], 'disturbance_draft_only')
        self.assertEqual(before, self.bytes())
        c = load(self.workspace)
        result = schedule(self.workspace, self.disturbance(), apply=True)
        after = load(self.workspace)
        self.assertEqual(after['dynamics']['perturbations'], [self.disturbance()])
        after['dynamics']['perturbations'] = []
        self.assertEqual(after, c)
        self.assertEqual(Path(result['backup']).read_bytes(), before[Path('team.yaml')])
        self.assertEqual((self.workspace / 'study.yaml').read_bytes(), before[Path('study.yaml')])
        self.assertFalse(result['bindings_regenerated'])

    def test_unsupported_or_out_of_horizon_scenarios_fail(self):
        for row in ({**self.disturbance(), 'actor': 'member.99'}, {**self.disturbance(), 'at_wave': 99},
                    {**self.disturbance(), 'duration': 0}, {**self.disturbance(), 'kind': 'model_change'}):
            before = self.bytes()
            with self.assertRaises(ConfigurationError):
                schedule(self.workspace, row, apply=True)
            self.assertEqual(before, self.bytes())

    def test_schedule_application_is_blocked_by_active_run_lock_but_preview_is_allowed(self):
        import fcntl
        with (self.workspace / '.run.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(schedule(self.workspace, self.disturbance())['api_calls'], 0)
            with self.assertRaisesRegex(ConfigurationError, 'run owns'):
                schedule(self.workspace, self.disturbance(), apply=True)

    def test_cli_builds_all_three_explicit_condition_shapes_without_provider_calls(self):
        before = self.bytes()
        for kind, target in [('actor_unavailable', 'member.1'), ('representation_unavailable', 'context'), ('link_dropout', 'member.1->member.2')]:
            with redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(main(['schedule', '--workspace', str(self.workspace), '--id', 'planned', '--kind', kind, '--target', target, '--at-wave', '4', '--duration', '1']), 0)
            self.assertEqual(json.loads(stream.getvalue())['api_calls'], 0)
        self.assertEqual(before, self.bytes())


class IntegrationTests(Case):
    def test_stop_finishes_only_current_wave_and_retains_partial_contributions(self):
        self.local_provider()
        seen = []
        def transport(method, path, body):
            seen.append(body)
            if len(seen) == 1:
                submit(self.current(), action='stop', apply=True)
            return self.response()
        result = asyncio.run(run(self.workspace, live=True, approve_requests=24, transport=transport))
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['provider_requests'], 3)
        root = Path(result['run_directory'])
        self.assertTrue((root / 'outputs.partial.json').is_file())
        self.assertEqual(json.loads((root / 'summary.json').read_text())['stop_reason'], 'operator_stop')
        report = build_report(root)
        self.assertEqual(len(report['snapshots']), 2)
        self.assertIsNone(report['goal_achieved'])
        self.assertIn('Execution status: stopped', Path(result['deliverable']).read_text())
        with self.assertRaises(ConfigurationError):
            submit(root, action='resume', apply=True)

    def test_feedback_reaches_only_selected_future_main_member_frames_not_metadata(self):
        self.local_provider()
        seen = []
        def transport(method, path, body):
            for m in body['messages']:
                if m['role'] == 'user':
                    try: frame = json.loads(m['content'])
                    except ValueError: continue
                    if 'peer_views' in frame: seen.append(frame)
            if len(seen) == 1:
                submit(self.current(), action='feedback', message_file='mission/feedback.md', actors=['member.1'], apply=True)
            return self.response()
        result = asyncio.run(run(self.workspace, live=True, approve_requests=24, transport=transport))
        report = build_report(Path(result['run_directory']))
        reached = [f for f in seen if f['peer_views'].get('operator_feedback')]
        self.assertTrue(reached)
        # Actor identity is carried in the cognition frame, not guessed from message text.
        self.assertTrue(all(f['peer_views']['cognition']['role']['actor'] == 'member.1' for f in reached))
        self.assertEqual(result['provider_requests'], 12)
        self.assertNotIn('PRIVATE_FEEDBACK_SENTINEL', json.dumps(report))
        self.assertGreater(len(report['operator_control']['feedback_exposures']), 0)
        self.assertIsNone(report['goal_achieved'])

    def test_pause_resume_keeps_same_run_lock_model_request_cap_and_counters(self):
        self.local_provider()
        calls = []
        def transport(method, path, body):
            calls.append(body)
            if len(calls) == 1:
                submit(self.current(), action='pause', apply=True)
            return self.response()
        async def exercise():
            task = asyncio.create_task(run(self.workspace, live=True, approve_requests=24, transport=transport))
            for _ in range(400):
                if (self.workspace / 'trials').exists() and list((self.workspace / 'trials').iterdir()):
                    root = self.current()
                    if (root / 'operator/state.json').exists() and metadata(root, 'running')['mode'] == 'paused':
                        break
                await asyncio.sleep(.01)
            else:
                self.fail('Runtime did not reach its explicit pause boundary.')
            report = build_report(root)
            self.assertEqual(report['status'], 'running')
            self.assertEqual(len(calls), 3)
            await asyncio.sleep(.05)
            self.assertEqual(len(calls), 3)
            with self.assertRaisesRegex(ConfigurationError, 'run owns'):
                schedule(self.workspace, {'id': 'no-live-edit', 'kind': 'actor_unavailable', 'actor': 'member.1', 'at_wave': 4, 'duration': 1}, apply=True)
            submit(root, action='resume', apply=True)
            return await asyncio.wait_for(task, 5)
        result = asyncio.run(exercise())
        self.assertEqual(result['status'], 'completed_text_workflow')
        self.assertEqual(result['provider_requests'], 12)
        self.assertEqual(build_report(Path(result['run_directory']))['budget']['max_llm_calls'], 24)

    def test_resume_never_replenishes_an_exhausted_request_budget(self):
        self.local_provider(cap=3)
        calls = []
        def transport(method, path, body):
            calls.append(body)
            if len(calls) == 1:
                submit(self.current(), action='pause', apply=True)
                submit(self.current(), action='resume', apply=True)
            return self.response()
        result = asyncio.run(run(self.workspace, live=True, approve_requests=3, transport=transport))
        self.assertEqual(result['status'], 'failed_or_incomplete')
        self.assertEqual(result['provider_requests'], 3)
        r = build_report(Path(result['run_directory']))
        self.assertEqual(r['budget']['max_llm_calls'], 3)
        self.assertEqual([x['action'] for x in r['operator_control']['receipts']], ['pause', 'resume'])
        self.assertIsNone(r['goal_achieved'])

    def test_invalid_control_records_do_not_relabel_core_records_or_expose_raw_fields(self):
        result = asyncio.run(run(self.workspace))
        root = Path(result['run_directory'])
        path = root / 'operator/state.json'
        state = json.loads(path.read_text())
        state['configuration_sha256'] = 'wrong-configuration'
        state['private_text'] = 'PRIVATE_OPERATOR_SENTINEL'
        path.write_text(json.dumps(state))
        r = build_report(root)
        self.assertEqual(r['operator_control']['mode'], 'unavailable_invalid_records')
        self.assertFalse(r['operator_control']['available'])
        self.assertIsNone(r['goal_achieved'])
        self.assertNotIn('PRIVATE_OPERATOR_SENTINEL', json.dumps(r))
        with self.assertRaises(ConfigurationError):
            submit(root, action='resume', apply=True)

    def test_invalid_control_queue_fails_closed_before_more_work_and_preserves_partial_records(self):
        self.local_provider()
        calls = []
        def transport(method, path, body):
            calls.append(body)
            if len(calls) == 1:
                root = self.current()
                for i in range(2):
                    (root / 'operator/requests' / f'{i}-invalid.json').write_text('{}')
            return self.response()
        with patch('teamknitt.interventions.MAX_REQUESTS', 1):
            result = asyncio.run(run(self.workspace, live=True, approve_requests=24, transport=transport))
            report = build_report(Path(result['run_directory']))
        self.assertEqual(result['status'], 'failed_or_incomplete')
        self.assertEqual(result['provider_requests'], 3)
        self.assertEqual(report['operator_control']['mode'], 'unavailable_invalid_records')
        self.assertEqual(len(report['snapshots']), 2)
        self.assertTrue(Path(result['deliverable']).is_file())
        self.assertIsNone(report['goal_achieved'])

    def test_feedback_does_not_mutate_task_sources_or_engine_settings(self):
        self.local_provider()
        files = ['team.yaml', 'study.yaml', 'mission/task.md', 'mission/context.md', 'mission/feedback.md']
        before = {p: (self.workspace / p).read_bytes() for p in files}
        calls = []
        def transport(method, path, body):
            calls.append(body)
            if len(calls) == 1:
                submit(self.current(), action='feedback', message_file='mission/feedback.md', apply=True)
            return self.response()
        asyncio.run(run(self.workspace, live=True, approve_requests=24, transport=transport))
        self.assertEqual(before, {p: (self.workspace / p).read_bytes() for p in files})

    def test_feedback_symlink_cannot_alias_a_credential_file(self):
        root, _ = self.active()
        (self.workspace / '.env').write_text('DO_NOT_READ_CREDENTIAL')
        link = self.workspace / 'mission/linked.md'
        link.symlink_to(self.workspace / '.env')
        with self.assertRaisesRegex(ConfigurationError, 'symlink'):
            submit(root, action='feedback', message_file='mission/linked.md', apply=True)
        self.assertFalse(list((root / 'operator/requests').iterdir()))
