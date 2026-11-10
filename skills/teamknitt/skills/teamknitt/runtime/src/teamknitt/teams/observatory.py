"""Read-only collection/individual-team metadata and non-mutating draft previews."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ..config import resource
from ..engine.config import ConfigurationError
from ..observatory import html as team_html, snapshot as team_snapshot
from .config import compile_collection, draft_team
from .editing import connection_draft
from .reporting import plan_report, read, report


class Service:
    def __init__(self, workspace=None, run_directory=None, *, initial_team=None):
        self.workspace = Path(workspace).resolve() if workspace is not None else None
        if run_directory is not None and Path(run_directory).is_symlink():
            raise ConfigurationError('Select a regular collection run, not a symlink.')
        self.run_directory = Path(run_directory).resolve() if run_directory is not None else None
        self.initial_team = initial_team

    def state(self, selection='latest'):
        if selection not in {'latest','setup'}:
            raise ConfigurationError('Select latest or setup.')
        if self.workspace is not None:
            p = compile_collection(self.workspace)
            r = plan_report(p)
            trials = self.workspace / 'trials'
            if selection == 'latest' and trials.is_dir() and not trials.is_symlink():
                for path in sorted(trials.iterdir(), reverse=True)[:100]:
                    if path.is_symlink() or not path.is_dir() or not (path / 'teams-run.json').is_file(): continue
                    try:
                        identity = read(path / 'teams-run.json', 100_000)
                        if identity.get('configuration_sha256') == p['configuration_sha256']:
                            r = report(path);break
                    except (OSError, ValueError, KeyError, TypeError):
                        continue
            drafts = True
        elif self.run_directory is not None:
            r, drafts = report(self.run_directory), False
        else:
            raise ConfigurationError('Select a collection workspace or run.')
        if self.initial_team is not None and self.initial_team not in r['team_reports']:
            raise ConfigurationError('Choose a configured initial team ID.')
        return {**r, 'viewer': {'live': True, 'draft_available': drafts, 'selection': selection, 'initial_team': self.initial_team,
            'read_at': datetime.now(timezone.utc).isoformat()}}

    def team_state(self, team_id, selection='latest'):
        return child_report(self.state(selection), team_id)

    def team_draft(self, values, team_id=None):
        if self.workspace is None:
            raise ConfigurationError('Saved collections cannot be changed.')
        allowed = {'team','members','topology','communication','purpose','max_read_words','exporter'}
        if set(values)-allowed or any(len(v)!=1 for v in values.values()):
            raise ConfigurationError('Use single, known metadata draft controls; no file or credential paths.')
        one=lambda key: values.get(key,[None])[0]
        selected = team_id or one('team')
        if not selected or team_id is not None and one('team') not in {None, team_id}:
            raise ConfigurationError('Choose one configured team ID.')
        c, raw, p, changed = draft_team(self.workspace, selected,
            count=int(one('members')) if one('members') is not None else None,
            topology=one('topology'), communication=one('communication'), purpose=one('purpose'),
            max_read_words=int(one('max_read_words')) if one('max_read_words') is not None else None,
            exporter=None if one('exporter') == 'none' else one('exporter'), set_exporter=one('exporter') is not None)
        r = {**plan_report(p), 'viewer': {'live': True, 'draft_available': True, 'selection': 'draft_only', 'initial_team': selected}}
        return child_report(r, selected) if team_id else r

    def connection_draft(self, values):
        if self.workspace is None:
            raise ConfigurationError('Saved collections cannot be changed.')
        allowed={'profile','source','target','reciprocal','all_links','remove','words'}
        if set(values)-allowed or any(len(v)!=1 for v in values.values()):
            raise ConfigurationError('Use single, known route-preview controls.')
        one=lambda key: values.get(key,[None])[0]
        def flag(key):
            value=one(key)
            if value not in {None,'false','true'}: raise ConfigurationError('Boolean draft flags must be true or false.')
            return value=='true'
        c,p=connection_draft(self.workspace,profile=one('profile'),source=one('source'),target=one('target'),
            reciprocal=flag('reciprocal'),all_links=flag('all_links'),remove=flag('remove'),words=int(one('words')) if one('words') is not None else None)
        return {**plan_report(p),'viewer':{'live':True,'draft_available':True,'selection':'draft_only','initial_team':self.initial_team}}


def child_report(collection, team_id):
    if team_id not in collection['team_reports']:
        raise ConfigurationError('Choose a configured team ID.')
    return {**collection['team_reports'][team_id], 'viewer': {**collection['viewer'], 'multi_team': {
        'team_id': team_id, 'collection_run_id': collection['run_id'],
        'configuration_file': next(t['configuration_file'] for t in collection['teams'] if t['id'] == team_id),
        'study_file': next(t['study_file'] for t in collection['teams'] if t['id'] == team_id), 'collection_configuration_sha256': collection['configuration_sha256']}}}


def html(record):
    core=resource('observatory.html').read_text()
    css=core.split('<style>',1)[1].split('</style>',1)[0]
    payload=json.dumps(record,allow_nan=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    return resource('teams.html').read_text().replace('__TEAMS_CSS__',css).replace('__TEAMS_JSON__',payload).replace('__TEAMS_JS__',resource('teams.js').read_text())


def snapshot(path, *, workspace=None, run_directory=None, team_id=None):
    service=Service(None if run_directory else workspace,run_directory,initial_team=team_id)
    record=service.state()
    record['viewer'].update(live=False,draft_available=False,selection='snapshot')
    if team_id:
        return team_snapshot(child_report(record,team_id),path)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(html(record))
    return {'status':'snapshot_saved','output':str(path.absolute()),'api_calls':0}


def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def send(self, content, kind, status=200):
            self.send_response(status)
            for key,value in {'Content-Type':kind,'Content-Length':str(len(content)),'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
                'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self' https:"}.items():self.send_header(key,value)
            self.end_headers();self.wfile.write(content)
        def do_GET(self):
            if len(self.path)>4096:self.send_error(414);return
            parsed=urlsplit(self.path)
            try:
                query=parse_qs(parsed.query,keep_blank_values=True,max_num_fields=24)
                path=parsed.path
                if path=='/':
                    self.send(html(service.state()).encode(),'text/html; charset=utf-8');return
                if path=='/api/team-draft':value=service.team_draft(query)
                elif path=='/api/connection-draft':value=service.connection_draft(query)
                else:
                    parts=path.strip('/').split('/')
                    team_id=parts[1] if len(parts)>=2 and parts[0]=='team' else None
                    if team_id is not None and len(parts)==2:
                        self.send(team_html(service.team_state(team_id)).encode(),'text/html; charset=utf-8');return
                    if team_id is not None and parts[2:]==['api','draft']:
                        value=service.team_draft(query,team_id)
                    elif path=='/api/state' or team_id is not None and parts[2:]==['api','state']:
                        if set(query)-{'selection'} or len(query.get('selection',['latest']))!=1:raise ConfigurationError('Unknown state selection.')
                        selected=query.get('selection',['latest'])[0]
                        value=service.team_state(team_id,selected) if team_id else service.state(selected)
                    else:self.send_error(404);return
                self.send(json.dumps(value,allow_nan=False).encode(),'application/json')
            except (ConfigurationError,OSError,ValueError,KeyError,TypeError) as error:
                self.send(json.dumps({'error':str(error)}).encode(),'application/json',400)
        def do_POST(self):self.send_error(405,'Read-only metadata and previews. Use explicit CLI application/execution.')
        def log_message(self,*args):pass
    return Handler


def serve(workspace, port=8767, *, run_directory=None, team_id=None):
    service=Service(None if run_directory else workspace,run_directory,initial_team=team_id)
    service.state()  # Validate before starting a service, without provider calls.
    with ThreadingHTTPServer(('127.0.0.1',port),handler(service)) as server:
        suffix='team/'+team_id+'/' if team_id else ''
        print(f'teamknitt multiple teams: http://127.0.0.1:{server.server_address[1]}/{suffix}',flush=True)
        print('Read-only metadata and draft previews; no models, writes, style downloads or run-start endpoints.',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
    return {'status':'viewer_stopped','api_calls':0}
