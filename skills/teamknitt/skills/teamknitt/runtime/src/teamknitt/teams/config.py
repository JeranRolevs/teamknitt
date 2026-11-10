"""Explicit multi-team configuration. No fetching, provider calls or style conversion."""
from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from ..builder import draft_configuration
from ..config import compile_plan as team_plan, digest, resource
from ..engine.config import ConfigurationError, parse_yaml
from ..engine.study import load_study

PROFILES = json.loads(resource('teams-profiles.json').read_text())

PRIVATE = {'.git', '.venv', 'trials', 'runs', 'setup', 'results', 'local-reference', 'data', '__pycache__'}


def checked_file(workspace, relative, *, maximum=2_000_000):
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or PRIVATE.intersection(p.parts) or p.name.startswith('.env') or p.name == 'private_splits.json':
        raise ConfigurationError('Use a bounded workspace-relative configuration or user-authored text path, not private runtime/credential paths.')
    root = Path(workspace).resolve()
    if any(root.joinpath(*p.parts[:i]).is_symlink() for i in range(1, len(p.parts) + 1)):
        raise ConfigurationError('Multi-team input paths cannot use symlinks.')
    target = root / p
    if not target.is_file() or target.stat().st_size > maximum:
        raise ConfigurationError('Multi-team input is missing, not a regular file or exceeds its size bound.')
    return target


def read_config(workspace, name='teams.yaml'):
    return parse_yaml(checked_file(workspace, name).read_text(encoding='utf-8'))


def validate(value):
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ConfigurationError('Multi-team configuration must be finite JSON-compatible data.') from error
    schema = json.loads(resource('teams.schema.json').read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(list(e.absolute_path)))
    if errors:
        e = errors[0]
        raise ConfigurationError(f'{".".join(map(str, e.absolute_path)) or "teams"}: {e.message}')
    c = deepcopy(value)
    ids = [t['id'] for t in c['teams']]
    if len(set(ids)) != len(ids):
        raise ConfigurationError('Team IDs must be unique; repeated style references do not merge teams.')
    paths = [t[k] for t in c['teams'] for k in ('configuration_file', 'study_file')]
    if len(set(paths)) != len(paths):
        raise ConfigurationError('Each team needs its own configuration and study settings file.')
    pairs = [(r['source'], r['target']) for r in c['communication']['links']]
    if len(set(pairs)) != len(pairs) or any(a not in ids or b not in ids or a == b for a, b in pairs):
        raise ConfigurationError('Inter-team links must be unique directed pairs of distinct configured teams.')
    if c['communication']['profile'] == 'none' and pairs:
        raise ConfigurationError('Disabled inter-team communication requires an empty link list.')
    for t in c['teams']:
        style = t['style']
        if (style['file'] is not None) != (style['authorship'] == 'user_authored'):
            raise ConfigurationError('Executable style context must be a local user-authored text file; references are metadata only.')
        seen = set()
        for ref in style['references']:
            u = urlsplit(ref['url'])
            if u.scheme != 'https' or not u.hostname or u.username or u.password or '\\' in ref['url']:
                raise ConfigurationError('External style references must be HTTPS URLs without embedded credentials.')
            key = (ref['url'], ref['revision'])
            if key in seen:
                raise ConfigurationError('Duplicate reference within a team.')
            seen.add(key)
    return c


def implementation_identity():
    from ..runtime import implementation_identity as core_identity
    bindings = {'core': core_identity()}
    for p in files('teamknitt.teams').iterdir():
        if p.is_file() and p.name.endswith('.py'):
            bindings[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('teams.schema.json', 'teams-profiles.json', 'teams.html', 'teams.js'):
        bindings[name] = hashlib.sha256(resource(name).read_bytes()).hexdigest()
    return digest(bindings)


def compile_collection(workspace, config=None, *, team_overrides=None, study_sources=None):
    root = Path(workspace).resolve()
    c = validate(read_config(root) if config is None else config)
    task = checked_file(root, c['task']['brief_file'], maximum=100_000)
    task_hash = hashlib.sha256(task.read_bytes()).hexdigest()
    rows, horizons = [], []
    for entry in c['teams']:
        raw = deepcopy(team_overrides[entry['id']]) if team_overrides and entry['id'] in team_overrides else read_config(root, entry['configuration_file'])
        if raw.get('schema_version') != 3 or raw.get('mission', {}).get('brief_file') != c['task']['brief_file']:
            raise ConfigurationError('Every team must be a schema-3 task team bound to the same shared brief file.')
        study_input = study_sources.get(entry['id'], entry['study_file']) if study_sources else entry['study_file']
        checked_file(root, study_input)
        style = deepcopy(entry['style'])
        style.update(status='reference_only' if style['references'] else 'native_configuration', content_sha256=None,
                     remote_content_loaded=False, external_runtime_used=False)
        if style['file'] is not None:
            path = checked_file(root, style['file'], maximum=12_000)
            if path.suffix.lower() not in {'.md', '.txt'}:
                raise ConfigurationError('User-authored style context must be UTF-8 .md or .txt text.')
            text = path.read_text(encoding='utf-8')
            if not text.strip():
                raise ConfigurationError('User-authored style context cannot be empty.')
            raw = deepcopy(raw)
            if any(r['id'] == 'team-style' for r in raw['cognition']['representations']):
                raise ConfigurationError('team-style is reserved for the explicitly attached user-authored style context.')
            raw['cognition']['representations'].append({'id': 'team-style', 'kind': 'source', 'purpose': 'Explicit user-authored team instructions; no extra tool/source permissions.',
                'format': 'markdown', 'path': style['file'], 'readers': [r['actor'] for r in raw['cognition']['roles']], 'writers': []})
            style.update(status='user_authored_context', content_sha256=hashlib.sha256(text.encode()).hexdigest())
        p = team_plan(root, raw, study_path=study_input)
        if p['engine_configuration']['runtime']['mode'] != 'text_only' or p['engine_plan']['execution']['kind'] != 'phase_graph' or p['engine_plan']['delegation']['max_depth'] != 0:
            raise ConfigurationError('Multi-team execution currently supports text-only phase-graph teams without delegation. No settings are silently converted.')
        actors = {r['actor'] for r in raw['cognition']['roles']}
        if p['mission_binding']['sha256'] != task_hash:
            raise ConfigurationError('The shared task changed while compiling the teams; compile again.')
        if entry['exporter'] is not None and entry['exporter'] not in actors:
            raise ConfigurationError('The inter-team exporter must be a configured main member, or null to disable exports.')
        signature = [sorted({n.split(':')[1] if ':' in n else n for n in w['nodes']}) for w in p['waves']]
        horizons.append(signature)
        rows.append({**deepcopy(entry), 'style': style, 'plan': p})
    horizon_by_id = {t['id']: h for t,h in zip(c['teams'], horizons)}
    if any(horizon_by_id[r['source']] != horizon_by_id[r['target']] for r in c['communication']['links']):
        raise ConfigurationError('Connected task teams must use the same configured phase boundaries; member counts, models, routes, roles and styles may differ.')
    binding = {'configuration': c, 'task_sha256': task_hash,
               'teams': {t['id']: t['plan']['configuration_sha256'] for t in rows},
               'implementation_sha256': implementation_identity()}
    return {'schema_version': 1, 'kind': 'team_collection', 'name': c['name'], 'configuration': c, 'teams': rows,
            'binding': binding, 'configuration_sha256': digest(binding), 'task_binding': {'path': c['task']['brief_file'], 'sha256': task_hash},
            'budget': deepcopy(c['budget']), 'resources': deepcopy(c['resources']), 'communication': deepcopy(c['communication']),
            'reference_request_case': sum(t['plan']['reference_request_case']['one_final_per_main_episode'] for t in rows),
            'api_calls': 0, 'automatic_team_selection': False, 'goal_achieved': None}


def draft_team(workspace, team_id, *, exporter=None, set_exporter=False, style_file=None, clear_style=False, reference=None, style_label=None, **choices):
    c = validate(read_config(workspace))
    entry = next((t for t in c['teams'] if t['id'] == team_id), None)
    if entry is None:
        raise ConfigurationError('Choose a configured team ID.')
    raw = read_config(workspace, entry['configuration_file'])
    changed = any(v is not None for v in choices.values())
    candidate = draft_configuration(raw, **choices) if changed else deepcopy(raw)
    if set_exporter:
        entry['exporter'] = exporter
    if style_file is not None:
        entry['style'].update(file=str(style_file), authorship='user_authored')
    if clear_style:
        entry['style'].update(file=None, authorship=None)
    if style_label is not None:
        entry['style']['label'] = style_label
    if reference is not None:
        entry['style']['references'].append({'label': style_label or 'External reference', 'url': reference, 'revision': None})
    p = compile_collection(workspace, c, team_overrides={team_id: candidate})
    return c, candidate, p, changed


def clone_draft(workspace, new_id, source_id, *, name=None):
    import re
    c = validate(read_config(workspace))
    if re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', new_id) is None or any(t['id'] == new_id for t in c['teams']):
        raise ConfigurationError('Choose a new unique lowercase team ID.')
    source = next((t for t in c['teams'] if t['id'] == source_id), None)
    if source is None:
        raise ConfigurationError('Choose an existing native source team explicitly with --from.')
    if (Path(workspace) / 'teams' / new_id).exists() or (Path(workspace) / 'teams' / new_id).is_symlink():
        raise ConfigurationError('The new team directory must not already exist.')
    entry = deepcopy(source)
    entry.update(id=new_id, name=name or new_id, configuration_file=f'teams/{new_id}/team.yaml', study_file=f'teams/{new_id}/study.yaml')
    raw = read_config(workspace, source['configuration_file'])
    raw['name'] = entry['name']
    study = read_config(workspace, source['study_file'])
    c['teams'].append(entry)
    p = compile_collection(workspace, c, team_overrides={new_id: raw}, study_sources={new_id: source['study_file']})
    return c, raw, study, p, source
