"""Allowlisted multi-team metadata; never exports style, task or contribution text."""
from copy import deepcopy
import json
from pathlib import Path

from ..config import digest, resource
from ..engine.config import ConfigurationError
from ..reporting import build_report, plan_report as team_report
from .config import validate


def read(path, maximum=30_000_000):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ConfigurationError('Saved multi-team metadata must be a bounded regular file.')
    value = json.loads(path.read_text(encoding='utf-8'))
    json.dumps(value, allow_nan=False)
    return value


def saved_plan(directory):
    root = Path(directory)
    if root.is_symlink():
        raise ConfigurationError('Select a regular collection run, not a symlink.')
    identity = read(root / 'teams-run.json')
    plan = read(root / 'teams-plan.json')
    c = validate(plan['configuration'])
    if plan['binding']['configuration'] != c or digest(plan['binding']) != plan['configuration_sha256'] or identity['configuration_sha256'] != plan['configuration_sha256']:
        raise ConfigurationError('Saved team-collection configuration binding is invalid.')
    if any(plan[k] != c[k] for k in ('name','budget','resources','communication')):
        raise ConfigurationError('Saved collection settings differ from their binding.')
    if plan['task_binding'] != {'path':c['task']['brief_file'],'sha256':plan['binding']['task_sha256']}:
        raise ConfigurationError('Saved shared task metadata differs from its binding.')
    if plan['binding']['teams'] != {t['id']: t['plan']['configuration_sha256'] for t in plan['teams']}:
        raise ConfigurationError('Saved team bindings do not match the collection.')
    if {t['id'] for t in plan['teams']} != {t['id'] for t in c['teams']}:
        raise ConfigurationError('Saved team roster differs from the collection binding.')
    for t in plan['teams']:
        original = next(e for e in c['teams'] if e['id'] == t['id'])
        if any(t[k] != original[k] for k in ('name', 'exporter', 'configuration_file', 'study_file')):
            raise ConfigurationError('Saved team metadata differs from its binding.')
        p = t['plan']
        binding = p['engine_plan']['configuration_snapshot']['cognition_binding']
        if digest(binding) != p['configuration_sha256'] or binding['cognition'] != p['configuration'] or binding['mission'] != plan['task_binding'] or binding['sources'] != p['source_bindings']:
            raise ConfigurationError('Saved native team binding is invalid.')
        expected_style = {**original['style'], 'status': 'user_authored_context' if original['style']['file'] else 'reference_only' if original['style']['references'] else 'native_configuration',
            'content_sha256': p['source_bindings'].get('team-style', {}).get('sha256'), 'remote_content_loaded': False, 'external_runtime_used': False}
        if t['style'] != expected_style:
            raise ConfigurationError('Saved style metadata differs from its explicit configuration.')
    return plan, identity


def plan_report(plan):
    cfg = plan['configuration']
    geometry = json.loads(resource('topology-layouts.json').read_text())['fully_connected'][str(len(plan['teams']))]
    positions = [{**p, 'id': entry['id']} for p,entry in zip(geometry, plan['teams'])]
    reports = {}
    rows = []
    for entry in plan['teams']:
        r = team_report(entry['plan'])
        reports[entry['id']] = r
        rows.append({'id': entry['id'], 'name': entry['name'], 'configuration_file': entry['configuration_file'], 'study_file': entry['study_file'],
            'configuration_sha256': entry['plan']['configuration_sha256'], 'members': len(r['cognition']['roles']), 'actors': [a['actor'] for a in r['cognition']['roles']],
            'topology': r['topology']['kind'], 'sharing': r['communication']['effective_profile'], 'provider': r['generation_provider'], 'local_budget': r['budget'],
            'style': deepcopy(entry['style']), 'exporter': entry['exporter'], 'status': 'planned_not_executed', 'provider_requests': 0, 'run_id': None})
    return {'schema_version': 1, 'kind': 'team_collection', 'name': plan['name'], 'configuration_sha256': plan['configuration_sha256'],
        'status': 'planned_not_executed', 'mode': 'configuration', 'task': deepcopy(cfg['task']), 'task_binding': plan['task_binding'],
        'budget': deepcopy(plan['budget']), 'resources': deepcopy(plan['resources']), 'exchange_profiles': json.loads(resource('teams-profiles.json').read_text()), 'communication': deepcopy(plan['communication']), 'positions': positions,
        'reference_request_case': plan['reference_request_case'], 'reference_case_fits': plan['reference_request_case'] <= plan['budget']['max_llm_calls'],
        'teams': rows, 'team_reports': reports, 'run_id': None, 'provider_requests': 0, 'exchange': [], 'goal_achieved': None, 'task_review': 'not_started',
        'automatic_winner': None, 'evidence_label': 'Configuration only — no task execution or provider calls',
        'boundary': 'One shared task; independent team configurations. External URLs are references only. No foreign skills/code/runtime, automatic merge, team ranking or budget increase.'}


def report(directory):
    if Path(directory).is_symlink():
        raise ConfigurationError('Select a regular collection run, not a symlink.')
    root = Path(directory).resolve()
    if (root / 'teams').is_symlink():
        raise ConfigurationError('Saved team directories cannot be symlinks.')
    plan, identity = saved_plan(root)
    state = read(root / 'teams-state.json')
    result = plan_report(plan)
    result.update(status=state['status'], mode=identity['mode'], run_id=identity['run_id'], provider_requests=state['provider_requests'],
        task_review=state['task_review'], updated_at=state.get('updated_at'),
        evidence_label='Offline multi-team fixture — not model performance or verified code' if identity['mode'] == 'offline_fixture' else 'Multi-team execution — contributions require user review; task success not inferred')
    fields = {'kind', 'source_team', 'target_team', 'exporter', 'actor', 'from_wave', 'to_wave', 'version', 'words', 'truncated', 'meaning', 'time'}
    result['exchange'] = [{k: deepcopy(v) for k,v in e.items() if k in fields} for e in state['exchange']]
    for row in result['teams']:
        child = root / 'teams' / row['id']
        if child.is_symlink():
            raise ConfigurationError('Saved team directories cannot be symlinks.')
        if not (child / 'team-run.json').is_file():
            continue
        ci = read(child / 'team-run.json')
        expected = {'run_id': identity['run_id'], 'team_id': row['id'], 'configuration_sha256': identity['configuration_sha256']}
        if ci.get('collection') != expected or ci['configuration_sha256'] != row['configuration_sha256']:
            raise ConfigurationError('Child run does not belong to the selected collection/team.')
        r = build_report(child)
        result['team_reports'][row['id']] = r
        row.update(status=r['status'], provider_requests=r['usage']['provider_requests'], run_id=r['run_id'])
    return result


def feedback_workspace(child, identity):
    """Verify the fixed collection directory structure, never trust a caller-supplied root."""
    child = Path(child).resolve()
    meta = identity.get('collection')
    if not isinstance(meta, dict) or child.parent.name != 'teams' or child.parents[2].name != 'trials':
        raise ConfigurationError('Feedback requires the original collection workspace/trials/run/teams/team location.')
    collection = child.parents[1]
    plan, parent = saved_plan(collection)
    if meta != {'run_id': parent['run_id'], 'team_id': child.name, 'configuration_sha256': parent['configuration_sha256']}:
        raise ConfigurationError('Operator target is bound to another collection.')
    entry = next((t for t in plan['teams'] if t['id'] == child.name), None)
    if entry is None or identity['configuration_sha256'] != entry['plan']['configuration_sha256']:
        raise ConfigurationError('Operator target has an invalid native team binding.')
    return child.parents[3]
