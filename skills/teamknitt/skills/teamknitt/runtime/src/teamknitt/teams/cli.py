"""Configure and inspect multiple native teams; explicit application and execution only."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from ..builder import PURPOSES
from ..engine.config import ConfigurationError
from ..engine.study import StudyError, save
from ..topology import TOPOLOGIES
from ..interventions import submit
from .config import compile_collection, draft_team, read_config, clone_draft, PROFILES
from .editing import baseline, connection_draft, persist, persist_clone
from .reporting import plan_report, report, saved_plan
from .runtime import run
from .scaffold import init


def main(argv=None):
    parser = argparse.ArgumentParser(prog='teamknitt teams', description='Multiple teams, one shared task, explicit routes and a bounded total budget.')
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('init', help='Create a native collection, disconnected by default; no provider or style downloads')
    start.add_argument('destination', type=Path)
    start.add_argument('--ids', default='alpha,beta,gamma', help='Comma-separated unique team IDs; 1–8 teams')
    start.add_argument('--members', type=int, default=3)
    start.add_argument('--topology', choices=tuple(TOPOLOGIES), default='fully_connected')
    start.add_argument('--sharing', choices=('none','low','intermediate','high','wisdom_only'), default='high')
    start.add_argument('--purpose', choices=tuple(PURPOSES), default='task')
    start.add_argument('--goal')
    start.add_argument('--request-cap', type=int, default=24, help='Total cap for all teams, never multiplied by team count')
    start.add_argument('--wall-seconds', type=int, default=600)
    for name in ('check','plan','prepare','demo','run','view','configure','connect','schedule','add','remove'):
        p = commands.add_parser(name)
        p.add_argument('--workspace', type=Path, default=Path.cwd())
        if name == 'demo': p.add_argument('--policy', choices=('connected','fragmented'), default='connected')
        if name == 'run':
            p.add_argument('--live', action='store_true')
            p.add_argument('--approve-requests', type=int)
        if name == 'view':
            p.add_argument('run', type=Path, nargs='?')
            p.add_argument('--team', help='Inspect one configured team using the normal metadata viewer')
            p.add_argument('--output', type=Path)
            p.add_argument('--port', type=int, default=8767)
        if name == 'configure':
            p.add_argument('--team', required=True)
            p.add_argument('--members', type=int)
            p.add_argument('--topology', choices=tuple(TOPOLOGIES))
            p.add_argument('--communication', choices=('none','low','intermediate','high','wisdom_only'))
            p.add_argument('--purpose', choices=tuple(PURPOSES))
            p.add_argument('--max-read-words', type=int)
            p.add_argument('--exporter', help='Main member ID, or none to disable inter-team exports')
            p.add_argument('--style-label')
            p.add_argument('--style-reference', help='HTTPS reference only; no remote material is loaded or converted')
            p.add_argument('--style-file', help='Workspace-relative, explicitly user-authored .md/.txt instructions')
            p.add_argument('--user-authored', action='store_true', help='Attest local style text is user-authored, not copied/adapted foreign prompts or skills')
            p.add_argument('--clear-style', action='store_true')
            p.add_argument('--apply', action='store_true')
            p.add_argument('--reset-bindings', action='store_true')
        if name == 'add':
            p.add_argument('--id', required=True)
            p.add_argument('--from', dest='source_team', required=True, help='Explicit native team to clone; no foreign import')
            p.add_argument('--name')
            p.add_argument('--apply', action='store_true')
        if name == 'remove':
            p.add_argument('--team', required=True)
            p.add_argument('--apply', action='store_true')
        if name == 'schedule':
            p.add_argument('--team', required=True)
            p.add_argument('--id', required=True)
            p.add_argument('--kind', choices=('actor_unavailable','representation_unavailable','link_dropout'), required=True)
            p.add_argument('--target', required=True)
            p.add_argument('--at-wave', type=int, required=True)
            p.add_argument('--duration', type=int, required=True)
            p.add_argument('--apply', action='store_true')
        if name == 'connect':
            p.add_argument('--profile', choices=tuple(PROFILES))
            p.add_argument('--source')
            p.add_argument('--target')
            p.add_argument('--reciprocal', action='store_true')
            p.add_argument('--all-to-all', action='store_true')
            p.add_argument('--remove', action='store_true')
            p.add_argument('--max-read-words', type=int)
            p.add_argument('--apply', action='store_true')
    item = commands.add_parser('report');item.add_argument('run', type=Path)
    op = commands.add_parser('intervene', help='One explicitly selected team, draft-first; same native boundary controls')
    op.add_argument('run', type=Path);op.add_argument('--team', required=True)
    op.add_argument('--action', choices=('pause','resume','stop','feedback'), required=True)
    op.add_argument('--message-file', type=Path);op.add_argument('--actors');op.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = init(args.destination, ids=args.ids.split(','), count=args.members, topology=args.topology, sharing=args.sharing,
                          purpose=args.purpose, goal=args.goal, request_cap=args.request_cap, wall_seconds=args.wall_seconds)
        elif args.command == 'report':
            result = report(args.run)
        elif args.command == 'intervene':
            plan, identity = saved_plan(args.run)
            if args.team not in {t['id'] for t in plan['teams']}:
                raise ConfigurationError('Select a configured team in this saved collection.')
            result = submit(args.run / 'teams' / args.team, action=args.action, message_file=args.message_file,
                            actors=args.actors.split(',') if args.actors is not None else None, apply=args.apply)
        elif args.command == 'configure':
            if bool(args.style_file) != args.user_authored:
                raise ConfigurationError('--style-file requires explicit --user-authored; foreign skills/prompts are references only.')
            if args.style_file and args.clear_style:
                raise ConfigurationError('Attach or clear a local style, not both.')
            original = read_config(args.workspace)
            entry = next((t for t in original['teams'] if t['id'] == args.team), None)
            if entry is None: raise ConfigurationError('Choose a configured team ID.')
            stamp = baseline(args.workspace, ['teams.yaml', entry['configuration_file']])
            c, team, compiled, regenerated = draft_team(args.workspace, args.team, count=args.members, topology=args.topology,
                communication=args.communication, purpose=args.purpose, max_read_words=args.max_read_words,
                exporter=None if args.exporter == 'none' else args.exporter, set_exporter=args.exporter is not None,
                style_file=args.style_file, clear_style=args.clear_style, reference=args.style_reference, style_label=args.style_label)
            result = {'status': 'team_configuration_draft_only', 'team': args.team, 'plan': plan_report(compiled), 'api_calls': 0,
                      'note': 'No files, providers, budgets or task text changed. External references are not imported styles.'}
            if args.apply:
                if regenerated and not args.reset_bindings:
                    raise ConfigurationError('Applying regenerated roles/representations requires --reset-bindings.')
                backup = persist(args.workspace, {'teams.yaml': c, entry['configuration_file']: team}, baseline=stamp)
                result = {'status': 'team_configuration_applied', 'team': args.team, 'backup': backup, 'api_calls': 0,
                          'configuration_sha256': compiled['configuration_sha256'], 'models_budgets_or_task_changed': False}
        elif args.command == 'add':
            original = read_config(args.workspace)
            source = next((t for t in original['teams'] if t['id'] == args.source_team), None)
            if source is None: raise ConfigurationError('Choose an existing source team explicitly.')
            stamp = baseline(args.workspace,['teams.yaml',source['configuration_file'],source['study_file']])
            c,raw,study,p,source = clone_draft(args.workspace,args.id,args.source_team,name=args.name)
            result = {'status':'native_team_clone_draft_only','plan':plan_report(p),'api_calls':0,'shared_cap_changed':False}
            if args.apply:
                backup = persist_clone(args.workspace,args.id,c,raw,study,baseline=stamp)
                result = {'status':'native_team_added','team':args.id,'source_team':args.source_team,'backup':backup,'api_calls':0,
                          'shared_cap_changed':False,'note':'Explicit native clone; no routes added, foreign import or model/budget selection.'}
        elif args.command == 'remove':
            stamp = baseline(args.workspace,['teams.yaml'])
            c = read_config(args.workspace)
            if args.team not in {t['id'] for t in c['teams']}: raise ConfigurationError('Choose an existing team.')
            c['teams'] = [t for t in c['teams'] if t['id'] != args.team]
            c['communication']['links'] = [r for r in c['communication']['links'] if args.team not in {r['source'],r['target']}]
            p = compile_collection(args.workspace,c)
            result = {'status':'team_removal_draft_only','plan':plan_report(p),'api_calls':0}
            if args.apply:
                backup = persist(args.workspace,{'teams.yaml':c},baseline=stamp)
                result = {'status':'team_removed_from_collection','backup':backup,'api_calls':0,'note':'Team configuration files and all historical runs retained; shared limits unchanged.'}
        elif args.command == 'schedule':
            original = read_config(args.workspace)
            entry = next((t for t in original['teams'] if t['id'] == args.team), None)
            if entry is None: raise ConfigurationError('Choose a configured team ID.')
            stamp = baseline(args.workspace, [entry['configuration_file']])
            raw = read_config(args.workspace, entry['configuration_file'])
            condition = {'id': args.id, 'kind': args.kind, 'at_wave': args.at_wave, 'duration': args.duration}
            if args.kind == 'link_dropout':
                pair = args.target.split('->')
                if len(pair) != 2: raise ConfigurationError('Quote a directed source->target pair.')
                condition.update(source=pair[0], target=pair[1])
            else: condition['actor' if args.kind == 'actor_unavailable' else 'representation'] = args.target
            raw['dynamics']['perturbations'].append(condition)
            p = compile_collection(args.workspace, original, team_overrides={args.team:raw})
            result = {'status':'disturbance_draft_only','team':args.team,'disturbance':condition,'api_calls':0}
            if args.apply:
                backup = persist(args.workspace,{entry['configuration_file']:raw},baseline=stamp)
                result.update(status='disturbance_scheduled',backup=backup,configuration_sha256=p['configuration_sha256'])
        elif args.command == 'connect':
            stamp = baseline(args.workspace, ['teams.yaml'])
            c, compiled = connection_draft(args.workspace, profile=args.profile, source=args.source, target=args.target,
                reciprocal=args.reciprocal, all_links=args.all_to_all, remove=args.remove, words=args.max_read_words)
            result = {'status': 'inter_team_routes_draft_only', 'plan': plan_report(compiled), 'api_calls': 0}
            if args.apply:
                backup = persist(args.workspace, {'teams.yaml': c}, baseline=stamp)
                result = {'status': 'inter_team_routes_applied', 'backup': backup, 'configuration_sha256': compiled['configuration_sha256'],
                          'api_calls': 0, 'models_budgets_or_task_changed': False}
        elif args.command == 'view':
            from .observatory import serve, snapshot
            result = snapshot(args.output, workspace=args.workspace, run_directory=args.run, team_id=args.team) if args.output else serve(args.workspace, args.port, run_directory=args.run, team_id=args.team)
        elif args.command in {'demo','run'}:
            if args.command == 'run' and not args.live:
                raise ConfigurationError('Use --live --approve-requests N; demo is a labelled offline fixture.')
            result = asyncio.run(run(args.workspace, live=args.command == 'run', approve_requests=getattr(args,'approve_requests',None), policy=getattr(args,'policy','connected')))
        else:
            p = compile_collection(args.workspace)
            if args.command == 'plan': result = p
            elif args.command == 'prepare':
                save(args.workspace / 'plans/teams.json', p)
                result = {'status': 'prepared', 'api_calls': 0, 'plan': str(args.workspace / 'plans/teams.json')}
            else:
                result = {'status': 'team_collection_valid', 'teams': [t['id'] for t in p['teams']], 'configuration_sha256': p['configuration_sha256'],
                          'shared_request_cap': p['budget']['max_llm_calls'], 'communication': p['communication'], 'api_calls': 0}
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get('status') in {'failed_or_incomplete','cancelled','stopped_or_incomplete'} else 0
    except (ConfigurationError, StudyError, OSError, ValueError, KeyError, TypeError) as error:
        print(f'teamknitt teams error: {error}', file=sys.stderr)
        return 2
