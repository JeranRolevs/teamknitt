"""Native multi-team scopes, explicit routes and shared limits. No paid calls."""
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from teamknitt.cli import main
from teamknitt.engine.config import ConfigurationError, parse_yaml
from teamknitt.interventions import metadata, submit
from teamknitt.teams.config import compile_collection, draft_team, read_config, validate
from teamknitt.teams.editing import baseline, connection_draft, persist
from teamknitt.teams.observatory import Service, handler, snapshot
from teamknitt.teams.reporting import report, saved_plan
from teamknitt.teams.runtime import run
from teamknitt.teams.scaffold import init


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'collection'
        init(self.root, count=1, goal='PRIVATE_COMMON_GOAL: propose a CSV validation command-line tool.')

    def files(self, root=None):
        root = root or self.root
        return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def cfg(self): return read_config(self.root)
    def write(self, value): (self.root/'teams.yaml').write_text(json.dumps(value))
    def connect(self, **kwargs):
        c,p = connection_draft(self.root, **kwargs)
        self.write(c)
        return p
    def providers(self, cap=24):
        for tid in ('alpha','beta','gamma'):
            path=self.root/f'teams/{tid}/study.yaml';c=parse_yaml(path.read_text())
            c['provider'].update(model='local-'+tid,base_url='http://127.0.0.1:1',api_key_env=None)
            path.write_text(json.dumps(c))
        c=self.cfg();c['budget']['max_llm_calls']=cap;self.write(c)
    def current(self): return sorted((self.root/'trials').iterdir())[-1]
    def response(self, tid, text=None):
        return {'choices':[{'message':{'content':json.dumps({'action':'final','summary':text or tid.upper()+'_RESULT_SENTINEL',
            'candidate_output':tid.upper()+'_PRIVATE_CANDIDATE','findings':[],'wisdom':[]})}}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}
    def transports(self, frames, callback=None, long=False):
        result={}
        for tid in ('alpha','beta','gamma'):
            def transport(method,path,body,name=tid):
                frames.setdefault(name,[])
                for m in body['messages']:
                    if m['role']=='user':
                        try: value=json.loads(m['content'])
                        except ValueError: continue
                        if 'peer_views' in value: frames[name].append(value)
                if callback: callback(name,body)
                return self.response(name,(name+' ') * 200 if long else None)
            result[tid]=transport
        return result


class ConfigurationTests(Case):
    def test_shared_task_and_independent_native_configurations(self):
        p=compile_collection(self.root)
        self.assertEqual([t['id'] for t in p['teams']],['alpha','beta','gamma'])
        self.assertEqual(len({t['configuration_file'] for t in p['teams']}),3)
        self.assertEqual(len({t['study_file'] for t in p['teams']}),3)
        self.assertTrue(all(t['plan']['mission_binding']==p['task_binding'] for t in p['teams']))
        self.assertEqual(p['budget']['max_llm_calls'],24)
        self.assertEqual(p['communication']['profile'],'none')
        self.assertFalse(p['communication']['links'])
        self.assertFalse((self.root/'team.yaml').exists())
        self.assertFalse(p['automatic_team_selection'])
        self.assertIsNone(p['goal_achieved'])

    def test_distinct_topologies_counts_and_models_are_explicit_and_keep_shared_cap(self):
        self.providers()
        c,raw,p,changed=draft_team(self.root,'beta',count=4,topology='ring',communication='intermediate')
        self.assertTrue(changed)
        self.assertEqual(len(next(t for t in p['teams'] if t['id']=='beta')['plan']['topology']['members']),4)
        self.assertEqual(next(t for t in p['teams'] if t['id']=='beta')['plan']['topology']['kind'],'ring')
        self.assertEqual({t['plan']['engine_configuration']['provider']['model'] for t in p['teams']},{'local-alpha','local-beta','local-gamma'})
        self.assertEqual(p['budget']['max_llm_calls'],24)
        self.assertEqual(compile_collection(self.root)['teams'][1]['plan']['topology']['kind'],'fully_connected')

    def test_duplicate_external_reference_means_two_distinct_reference_only_teams(self):
        c=self.cfg()
        for i,url in enumerate(['https://github.com/unclebob/ub-mode','https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md?plain=1','https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md?plain=1']):
            c['teams'][i]['style']['references']=[{'label':'User-selected reference','url':url,'revision':None}]
        before=self.files()
        with patch('urllib.request.urlopen',side_effect=AssertionError('No remote skill fetching')),patch('teamknitt.runtime.api_key',side_effect=AssertionError('No keys')):
            p=compile_collection(self.root,c)
        self.assertEqual(len(p['teams']),3)
        self.assertTrue(all(t['style']['status']=='reference_only' for t in p['teams']))
        self.assertTrue(all(not t['style']['remote_content_loaded'] and not t['style']['external_runtime_used'] for t in p['teams']))
        self.assertEqual(before,self.files())

    def test_local_authored_context_is_bounded_bound_and_not_a_foreign_runtime(self):
        (self.root/'styles').mkdir();(self.root/'styles/alpha.md').write_text('LOCAL_STYLE_ALPHA: preserve unresolved assumptions.')
        c,raw,p,_=draft_team(self.root,'alpha',style_file='styles/alpha.md')
        a=next(t for t in p['teams'] if t['id']=='alpha')
        self.assertIn('team-style',a['plan']['source_bindings'])
        self.assertEqual(a['style']['status'],'user_authored_context')
        self.assertTrue(all('team-style' not in t['plan']['source_bindings'] for t in p['teams'] if t['id']!='alpha'))
        self.assertEqual(a['plan']['engine_plan']['budget']['max_llm_calls'],24)
        (self.root/'styles/alpha.md').write_text('changed by user')
        self.assertNotEqual(p['configuration_sha256'],compile_collection(self.root,c)['configuration_sha256'])

    def test_invalid_goals_links_ids_and_external_payloads_fail_before_execution(self):
        originals=self.cfg()
        cases=[]
        c=deepcopy(originals);c['teams'][1]['id']='alpha';cases.append(c)
        c=deepcopy(originals);c['teams'][0]['exporter']='member.99';cases.append(c)
        c=deepcopy(originals);c['communication']['links']=[{'source':'alpha','target':'beta'}];cases.append(c)
        c=deepcopy(originals);c['communication'].update(profile='summaries',links=[{'source':'alpha','target':'alpha'}]);cases.append(c)
        c=deepcopy(originals);c['teams'][0]['style']['references']=[{'label':'bad','url':'https://secret@github.com/project','revision':None}];cases.append(c)
        c=deepcopy(originals);c['teams'][0]['style'].update(file='https://github.com/project/SKILL.md',authorship='user_authored');cases.append(c)
        c=deepcopy(originals);c['teams'][0]['style']['authorship']='external_skill';cases.append(c)
        c=deepcopy(originals);c['teams'][1]['study_file']=c['teams'][0]['study_file'];cases.append(c)
        before=self.files()
        for c in cases:
            with self.subTest(config=c),self.assertRaises((ConfigurationError,ValueError,OSError)):
                compile_collection(self.root,c)
        self.assertEqual(before,self.files())
        p=self.root/'teams/beta/team.yaml';c=parse_yaml(p.read_text());c['mission']['brief_file']='mission/context.md';p.write_text(json.dumps(c))
        with self.assertRaisesRegex(ConfigurationError,'same shared brief'):compile_collection(self.root)

    def test_unsupported_delegation_and_statistics_never_silently_convert(self):
        path=self.root/'teams/alpha/study.yaml';original=parse_yaml(path.read_text())
        for key,value in [('statistics',{'approach':'bayesian'}),('teams',{'max_depth':1})]:
            c=deepcopy(original);c['base_overrides'][key]=value;path.write_text(json.dumps(c))
            with patch('teamknitt.runtime.api_key',side_effect=AssertionError('No credentials')):
                with self.assertRaises((ConfigurationError,ValueError)):compile_collection(self.root)


class EditingTests(Case):
    def test_cli_team_and_connection_previews_do_not_write(self):
        before=self.files()
        for args in [['teams','configure','--team','beta','--members','4','--topology','grid'],['teams','connect','--profile','summaries','--source','alpha','--target','beta']]:
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args+['--workspace',str(self.root)]),0)
                self.assertEqual(json.loads(output.getvalue())['api_calls'],0)
        self.assertEqual(before,self.files())

    def test_apply_keeps_models_budgets_goal_and_other_teams_with_private_backup(self):
        original=self.files()
        args=['teams','configure','--workspace',str(self.root),'--team','beta','--members','4','--topology','grid','--apply']
        with redirect_stderr(io.StringIO()):self.assertEqual(main(args),2)
        with redirect_stdout(io.StringIO()) as stream:self.assertEqual(main(args+['--reset-bindings']),0)
        result=json.loads(stream.getvalue());self.assertTrue(Path(result['backup']).is_file())
        for name in ['teams/alpha/team.yaml','teams/gamma/team.yaml','teams/alpha/study.yaml','teams/beta/study.yaml','teams/gamma/study.yaml','mission/task.md']:
            self.assertEqual((self.root/name).read_bytes(),original[Path(name)])
        self.assertEqual(compile_collection(self.root)['budget']['max_llm_calls'],24)
        if __import__('os').name=='posix':self.assertEqual(Path(result['backup']).stat().st_mode&0o777,0o600)

    def test_routes_are_directed_disable_clears_and_apply_uses_shared_lock(self):
        c,p=connection_draft(self.root,profile='summaries',source='alpha',target='beta')
        self.assertEqual(c['communication']['links'],[{'source':'alpha','target':'beta'}])
        persist(self.root,{'teams.yaml':c},baseline=baseline(self.root,['teams.yaml']))
        c,p=connection_draft(self.root,source='beta',target='gamma',reciprocal=True)
        self.assertEqual(len(c['communication']['links']),3)
        c,p=connection_draft(self.root,profile='none');self.assertFalse(c['communication']['links'])
        import fcntl
        with (self.root/'.run.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            connection_draft(self.root,profile='summaries',all_links=True)
            with self.assertRaisesRegex(ValueError,'owns this workspace'):
                persist(self.root,{'teams.yaml':c},baseline=baseline(self.root,['teams.yaml']))

    def test_style_attachment_requires_user_authorship_and_reference_is_draft_only(self):
        (self.root/'style.md').write_text('Own task instructions.')
        before=self.files()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(['teams','configure','--workspace',str(self.root),'--team','alpha','--style-file','style.md']),2)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['teams','configure','--workspace',str(self.root),'--team','alpha','--style-file','style.md','--user-authored']),0)
        self.assertEqual(before,self.files())

    def test_concurrent_reconfiguration_is_detected_without_overwrite(self):
        c,p=connection_draft(self.root,profile='summaries',source='alpha',target='beta')
        stamp=baseline(self.root,['teams.yaml'])
        changed=self.cfg();changed['name']='User edited';self.write(changed)
        with self.assertRaisesRegex(ConfigurationError,'changed during review'):persist(self.root,{'teams.yaml':c},baseline=stamp)
        self.assertEqual(self.cfg()['name'],'User edited')


class ExecutionTests(Case):
    def test_offline_three_team_run_has_no_calls_or_inter_team_exposures_by_default(self):
        r=asyncio.run(run(self.root));m=report(Path(r['run_directory']))
        self.assertEqual(r['status'],'completed_team_collection')
        self.assertEqual(r['provider_requests'],0)
        self.assertEqual(len(m['teams']),3)
        self.assertFalse(m['exchange'])
        self.assertIsNone(m['automatic_winner']);self.assertIsNone(m['goal_achieved'])
        self.assertTrue(all(t['status']=='completed_text_workflow' for t in m['teams']))

    def test_models_task_and_disconnected_context_are_separate(self):
        self.providers();frames={};bodies={}
        def check(tid,body):bodies.setdefault(tid,[]).append(body)
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,check)))
        self.assertEqual(r['provider_requests'],12)
        for tid in ('alpha','beta','gamma'):
            self.assertTrue(all('team_exchange' not in f['peer_views'] for f in frames[tid]))
            self.assertTrue(all(b['model']=='local-'+tid for b in bodies[tid]))
            self.assertTrue(all('PRIVATE_COMMON_GOAL' in json.dumps(b) for b in bodies[tid]))
        meta=report(Path(r['run_directory']))
        self.assertNotIn('PRIVATE_COMMON_GOAL',json.dumps(meta))
        self.assertNotIn('PRIVATE_CANDIDATE',json.dumps(meta))
        self.assertNotIn('RESULT_SENTINEL',json.dumps(meta))

    def test_only_permitted_prior_wave_exporter_contributions_reach_target_team(self):
        self.providers();self.connect(profile='summaries',source='alpha',target='beta');frames={}
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames)))
        self.assertEqual(r['provider_requests'],12)
        self.assertTrue(all('team_exchange' not in f['peer_views'] for f in frames['alpha']+frames['gamma']))
        received=[f for f in frames['beta'] if f['peer_views'].get('team_exchange',{}).get('contributions')]
        self.assertTrue(received)
        for frame in received:
            for source in frame['peer_views']['team_exchange']['contributions']:
                self.assertEqual(source['source_team'],'alpha')
                self.assertLess(source['from_wave'],frame['peer_views']['cognition']['wave'])
                self.assertEqual(source['text'],'ALPHA_RESULT_SENTINEL')
        self.assertFalse(frames['beta'][0]['peer_views']['team_exchange']['contributions'])
        meta=report(Path(r['run_directory']))
        self.assertEqual({e['target_team'] for e in meta['exchange'] if e['kind']=='team_exchange_exposed'},{'beta'})
        self.assertNotIn('RESULT_SENTINEL',json.dumps(meta))

    def test_export_word_cap_and_disabled_exporter_are_enforced(self):
        self.providers();self.connect(profile='summaries',source='alpha',target='beta',words=5);frames={}
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,long=True)))
        for f in frames['beta']:
            values=f['peer_views']['team_exchange']['contributions']
            self.assertLessEqual(sum(len(v['text'].split()) for v in values),5)
            self.assertTrue(all(v['truncated'] for v in values))
        c=self.cfg();c['teams'][0]['exporter']=None;self.write(c);frames={}
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames)))
        self.assertTrue(all(not f['peer_views']['team_exchange']['contributions'] for f in frames['beta']))

    def test_user_authored_style_context_does_not_enter_other_teams_or_metadata(self):
        self.providers();(self.root/'own.md').write_text('OWN_STYLE_ALPHA_ONLY Keep unresolved assumptions visible.')
        c,raw,p,_=draft_team(self.root,'alpha',style_file='own.md');self.write(c);frames={}
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames)))
        self.assertTrue(any('OWN_STYLE_ALPHA_ONLY' in json.dumps(f) for f in frames['alpha']))
        self.assertTrue(all('OWN_STYLE_ALPHA_ONLY' not in json.dumps(f) for f in frames['beta']+frames['gamma']))
        self.assertNotIn('OWN_STYLE_ALPHA_ONLY',json.dumps(report(Path(r['run_directory']))))

    def test_total_request_cap_never_multiplies_by_team_count_or_resume(self):
        self.providers(cap=3);frames={};once=[]
        def callback(tid,body):
            if tid=='alpha' and not once:
                once.append(True);child=self.current()/'teams/alpha'
                submit(child,action='pause',apply=True);submit(child,action='resume',apply=True)
        r=asyncio.run(run(self.root,live=True,approve_requests=3,transports=self.transports(frames,callback)))
        self.assertEqual(r['status'],'failed_or_incomplete')
        self.assertEqual(r['provider_requests'],3)
        self.assertLessEqual(sum(len(v) for v in frames.values()),6) # Frames can be assembled before a reservation fails.
        self.assertEqual(report(Path(r['run_directory']))['budget']['max_llm_calls'],3)

    def test_feedback_uses_verified_collection_workspace_and_only_selected_team(self):
        self.providers();(self.root/'mission/feedback.md').write_text('PRIVATE_TEAM_FEEDBACK Only alpha receives this guidance.')
        frames={};once=[]
        def callback(tid,body):
            if tid=='alpha' and not once:
                once.append(True);child=self.current()/'teams/alpha'
                submit(child,action='feedback',message_file='mission/feedback.md',apply=True)
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)))
        self.assertTrue(any('PRIVATE_TEAM_FEEDBACK' in json.dumps(f) for f in frames['alpha']))
        self.assertTrue(all('PRIVATE_TEAM_FEEDBACK' not in json.dumps(f) for f in frames['beta']+frames['gamma']))
        self.assertNotIn('PRIVATE_TEAM_FEEDBACK',json.dumps(report(Path(r['run_directory']))))
        with self.assertRaisesRegex(ConfigurationError,'terminal'):submit(Path(r['run_directory'])/'teams/alpha',action='resume',apply=True)

    def test_stop_one_team_preserves_other_disconnected_teams_and_partial_review(self):
        self.providers();frames={};once=[]
        def callback(tid,body):
            if tid=='alpha' and not once:
                once.append(True);submit(self.current()/'teams/alpha',action='stop',apply=True)
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)))
        self.assertEqual(r['status'],'stopped_or_incomplete')
        self.assertEqual(r['teams']['alpha']['status'],'stopped')
        self.assertEqual(r['teams']['beta']['status'],'completed_text_workflow')
        self.assertEqual(r['provider_requests'],9)
        self.assertTrue((Path(r['run_directory'])/'teams/alpha/outputs.partial.json').is_file())

    def test_authorization_and_tampered_saved_bindings_fail_closed(self):
        with self.assertRaises(ConfigurationError):asyncio.run(run(self.root,live=True,approve_requests=72))
        self.assertFalse((self.root/'trials').exists())
        r=asyncio.run(run(self.root));directory=Path(r['run_directory'])
        p=json.loads((directory/'teams-plan.json').read_text());p['configuration']['communication']['profile']='contributions'
        (directory/'teams-plan.json').write_text(json.dumps(p))
        with self.assertRaisesRegex(ConfigurationError,'binding'):report(directory)


class ViewerTests(Case):
    def test_collection_and_child_previews_are_nonmutating_and_never_load_arbitrary_paths(self):
        service=Service(self.root);before=self.files()
        state=service.state();self.assertEqual(state['kind'],'team_collection')
        self.assertEqual(service.team_state('alpha')['viewer']['multi_team']['team_id'],'alpha')
        r=service.team_draft({'team':['beta'],'members':['4'],'topology':['ring']})
        self.assertEqual(next(t for t in r['teams'] if t['id']=='beta')['members'],4)
        self.assertEqual(r['budget']['max_llm_calls'],24)
        child=service.team_draft({'members':['2']},'alpha')
        self.assertEqual(len(child['cognition']['roles']),2)
        for q in ({'team':['alpha'],'style_file':['.env']},{'team':['alpha'],'budget':['999']},{'team':['alpha'],'members':['2','3']}):
            with self.assertRaises(ConfigurationError):service.team_draft(q)
        self.assertEqual(before,self.files())

    def test_http_routes_only_metadata_and_drafts_not_execution_or_files(self):
        service=Service(self.root);server=ThreadingHTTPServer(('127.0.0.1',0),handler(service))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(thread.join,3);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_address[1]}'
        for path in ('/api/state','/team/alpha/api/state','/api/team-draft?team=alpha&members=2','/api/connection-draft?profile=summaries&source=alpha&target=beta'):
            with urllib.request.urlopen(base+path,timeout=10) as r:self.assertEqual(r.status,200)
        for path in ('/.env','/api/run','/teams/alpha/study.yaml','/team/../.env','/api/team-draft?team=alpha&style_file=.env'):
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+path,timeout=10)
            self.assertIn(caught.exception.code,(400,404));caught.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(urllib.request.Request(base+'/api/run',data=b'{}',method='POST'),timeout=5)
        self.assertEqual(caught.exception.code,405);caught.exception.close()
        self.assertFalse((self.root/'trials').exists())

    def test_offline_snapshots_are_new_private_files_and_keep_child_command_scope(self):
        output=Path(self.temp.name)/'collection.html';snapshot(output,workspace=self.root)
        text=output.read_text();self.assertIn('"live": false',text);self.assertNotIn('PRIVATE_COMMON_GOAL',text)
        child=Path(self.temp.name)/'alpha.html';snapshot(child,workspace=self.root,team_id='alpha')
        self.assertIn('"multi_team": {',child.read_text());self.assertIn('"team_id": "alpha"',child.read_text())
        with self.assertRaises(FileExistsError):snapshot(output,workspace=self.root)
        if __import__('os').name=='posix':self.assertEqual(output.stat().st_mode&0o777,0o600)


class AdditionalSafetyTests(Case):
    def test_explicit_native_clone_and_removal_are_drafts_then_preserve_caps_and_history(self):
        before=self.files()
        args=['teams','add','--workspace',str(self.root),'--id','delta','--from','beta']
        with redirect_stdout(io.StringIO()):self.assertEqual(main(args),0)
        self.assertEqual(before,self.files())
        with redirect_stdout(io.StringIO()):self.assertEqual(main(args+['--apply']),0)
        p=compile_collection(self.root)
        self.assertEqual(len(p['teams']),4)
        self.assertEqual(p['budget']['max_llm_calls'],24)
        self.assertFalse(p['communication']['links'])
        self.assertEqual((self.root/'teams/delta/study.yaml').read_text().strip(),json.dumps(parse_yaml(before[Path('teams/beta/study.yaml')].decode()),indent=2).strip())
        raw=json.loads((self.root/'teams/delta/team.yaml').read_text());raw['name']='Independent delta';(self.root/'teams/delta/team.yaml').write_text(json.dumps(raw))
        self.assertNotEqual(parse_yaml((self.root/'teams/beta/team.yaml').read_text())['name'],'Independent delta')
        with redirect_stdout(io.StringIO()):self.assertEqual(main(['teams','remove','--workspace',str(self.root),'--team','delta','--apply']),0)
        self.assertEqual(len(compile_collection(self.root)['teams']),3)
        self.assertTrue((self.root/'teams/delta/team.yaml').is_file())

    def test_clone_plan_matches_applied_configuration_and_rejects_duplicates(self):
        from teamknitt.teams.config import clone_draft
        from teamknitt.teams.editing import persist_clone
        c,raw,study,p,source=clone_draft(self.root,'delta','beta')
        stamp=baseline(self.root,['teams.yaml',source['configuration_file'],source['study_file']])
        persist_clone(self.root,'delta',c,raw,study,baseline=stamp)
        self.assertEqual(compile_collection(self.root)['configuration_sha256'],p['configuration_sha256'])
        with self.assertRaises(ConfigurationError):clone_draft(self.root,'delta','beta')

    def test_inter_team_components_do_not_wait_for_unrelated_components(self):
        from teamknitt.teams.runtime import Exchange
        from teamknitt.engine.multi_lab import GroupLimits
        p={'teams':[{'id':t,'exporter':'member.1'} for t in ['a','b','c','d']],
           'communication':{'profile':'summaries','max_read_words':10,'links':[{'source':'a','target':'b'},{'source':'c','target':'d'}]},
           'resources':{'max_active_agents':2}}
        limits=GroupLimits({'budget':{'max_llm_calls':10,'max_wall_seconds':2},'resources':{'max_llm_requests':1,'max_experiments':1},'generation_provider':{'max_parallel_requests':1}})
        exchange=Exchange(p,limits,lambda e:None)
        async def check():
            waiting=asyncio.create_task(exchange.before_wave('c',1))
            await asyncio.gather(exchange.before_wave('a',1),exchange.before_wave('b',1))
            self.assertFalse(waiting.done())
            await exchange.before_wave('d',1)
            await waiting
        asyncio.run(check())

    def test_pause_of_unconnected_team_does_not_block_connected_pair(self):
        self.providers();self.connect(profile='summaries',source='alpha',target='beta');frames={};once=[]
        def callback(tid,body):
            if tid=='gamma' and not once:
                once.append(True);submit(self.current()/'teams/gamma',action='pause',apply=True)
        async def check():
            running=asyncio.create_task(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)))
            for _ in range(600):
                if (self.root/'trials').exists() and list((self.root/'trials').iterdir()):
                    directory=self.current();child=directory/'teams/gamma'
                    if (child/'operator/state.json').exists() and metadata(child,'running')['mode']=='paused':
                        states=[json.loads((directory/'teams'/t/'summary.json').read_text())['status'] for t in ('alpha','beta')]
                        if states==['completed_text_workflow']*2:break
                await asyncio.sleep(.01)
            else:self.fail('Unrelated pause blocked the connected pair.')
            submit(child,action='resume',apply=True)
            return await asyncio.wait_for(running,10)
        result=asyncio.run(check())
        self.assertEqual(result['provider_requests'],12)
        self.assertEqual(result['status'],'completed_team_collection')

    def test_shared_wall_deadline_keeps_elapsing_while_team_is_paused(self):
        self.providers();c=self.cfg();c['budget']['max_wall_seconds']=1;self.write(c);once=[];frames={}
        def callback(tid,body):
            if tid=='alpha' and not once:
                once.append(True);submit(self.current()/'teams/alpha',action='pause',apply=True)
        started=time.monotonic()
        result=asyncio.run(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)))
        self.assertLess(time.monotonic()-started,10)
        child=Path(result['run_directory'])/'teams/alpha'
        native=json.loads((child/'summary.json').read_text())
        self.assertEqual(native['status'],'stopped')
        self.assertEqual(native['stop_reason'],'wall_time_limit')
        self.assertEqual(result['status'],'stopped_or_incomplete')

    def test_aggregate_provider_concurrency_does_not_exceed_configured_cap(self):
        self.providers();c=self.cfg();c['resources']['max_llm_requests']=1;self.write(c)
        lock=threading.Lock();counter={'active':0,'peak':0}
        def transport(method,path,body):
            with lock:
                counter['active']+=1;counter['peak']=max(counter['peak'],counter['active'])
            time.sleep(.01)
            with lock:counter['active']-=1
            return self.response('local')
        r=asyncio.run(run(self.root,live=True,approve_requests=24,transports={t:transport for t in ('alpha','beta','gamma')}))
        self.assertEqual(r['provider_requests'],12)
        self.assertEqual(counter['peak'],1)

    def test_style_credential_paths_symlinks_and_overflow_are_rejected(self):
        (self.root/'.env').write_text('PRIVATE_KEY_DATA')
        (self.root/'own.md').symlink_to(self.root/'.env')
        for path in ('.env','own.md','trials/private.md','../outside.md'):
            with self.assertRaises((ConfigurationError,OSError)):draft_team(self.root,'alpha',style_file=path)
        (self.root/'too-large.md').write_text('x'*12001)
        with self.assertRaises(ConfigurationError):draft_team(self.root,'alpha',style_file='too-large.md')

    def test_corrupt_style_metadata_and_wrong_child_binding_are_not_displayed(self):
        r=asyncio.run(run(self.root));directory=Path(r['run_directory']);path=directory/'teams-plan.json'
        p=json.loads(path.read_text());p['teams'][0]['style']['remote_content_loaded']=True;path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ConfigurationError,'style metadata'):report(directory)
        p['teams'][0]['style']['remote_content_loaded']=False;path.write_text(json.dumps(p))
        child=directory/'teams/alpha/team-run.json';identity=json.loads(child.read_text());identity['collection']['team_id']='beta';child.write_text(json.dumps(identity))
        with self.assertRaisesRegex(ConfigurationError,'does not belong'):report(directory)

    def test_schedule_changes_only_selected_team_and_respects_lock(self):
        before=self.files();args=['teams','schedule','--workspace',str(self.root),'--team','alpha','--id','chosen-gap','--kind','actor_unavailable','--target','member.1','--at-wave','4','--duration','1']
        with redirect_stdout(io.StringIO()):self.assertEqual(main(args),0)
        self.assertEqual(before,self.files())
        with redirect_stdout(io.StringIO()):self.assertEqual(main(args+['--apply']),0)
        for name in ['teams/beta/team.yaml','teams/alpha/study.yaml','mission/task.md','teams.yaml']:
            self.assertEqual((self.root/name).read_bytes(),before[Path(name)])
        self.assertEqual(len(parse_yaml((self.root/'teams/alpha/team.yaml').read_text())['dynamics']['perturbations']),1)

    def test_canonical_exchange_profiles_and_group_geometry_remain_user_choices(self):
        from teamknitt.teams.config import PROFILES
        import importlib.util
        spec=importlib.util.spec_from_file_location('teamknitt_canonical_specs',Path(__file__).resolve().parents[1]/'diagrams/specs.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(PROFILES,module.TEAM_EXCHANGE_PROFILES)
        self.assertEqual(compile_collection(self.root)['communication']['profile'],'none')
        state=Service(self.root).state()
        self.assertEqual([p['id'] for p in state['positions']],['alpha','beta','gamma'])
        self.assertEqual([p['x'] for p in state['positions']],[p['x'] for p in module.team_topology_layout('fully_connected',3)])


class FinalizationTests(Case):
    def test_stopping_a_connected_team_releases_its_peers_without_fabricating_exports(self):
        self.providers();self.connect(profile='summaries',source='alpha',target='beta');frames={};once=[]
        def callback(tid,body):
            if tid=='alpha' and not once:
                once.append(True);submit(self.current()/'teams/alpha',action='stop',apply=True)
        async def check():
            return await asyncio.wait_for(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)),10)
        result=asyncio.run(check());r=report(Path(result['run_directory']))
        self.assertEqual(result['status'],'stopped_or_incomplete')
        self.assertEqual(result['teams']['beta']['status'],'completed_text_workflow')
        self.assertEqual(result['teams']['gamma']['status'],'completed_text_workflow')
        exports=[e for e in r['exchange'] if e['kind']=='team_export_available']
        self.assertEqual(len(exports),1)
        self.assertEqual(exports[0]['source_team'],'alpha')

    def test_unexpected_failure_before_native_start_is_terminal_and_releases_peers(self):
        from teamknitt.teams.runtime import CollectionTeam
        original=CollectionTeam.run
        self.connect(profile='summaries',source='alpha',target='beta')
        async def fail_one(runner):
            if runner.team_id=='alpha':raise RuntimeError('PRIVATE_EXCEPTION_CONTENT')
            return await original(runner)
        async def check():
            with patch.object(CollectionTeam,'run',fail_one):
                return await asyncio.wait_for(run(self.root),10)
        result=asyncio.run(check());directory=Path(result['run_directory'])
        self.assertEqual(result['status'],'failed_or_incomplete')
        self.assertEqual(result['teams']['alpha']['status'],'failed_or_incomplete')
        self.assertEqual(result['teams']['beta']['status'],'completed_text_workflow')
        self.assertEqual(metadata(directory/'teams/alpha','failed_or_incomplete')['mode'],'finished')
        self.assertTrue((directory/'teams/alpha/outputs.partial.json').is_file())
        self.assertNotIn('PRIVATE_EXCEPTION_CONTENT',json.dumps(report(directory)))

    def test_aggregate_active_episodes_respect_cap_not_team_count(self):
        from teamknitt.runtime import CognitiveStudy
        c=self.cfg();c['resources']['max_active_agents']=1;self.write(c)
        original=CognitiveStudy.run_node_episode;counts={'active':0,'peak':0}
        async def counted(runner,node,actor):
            counts['active']+=1;counts['peak']=max(counts['peak'],counts['active'])
            try:
                await asyncio.sleep(.002)
                return await original(runner,node,actor)
            finally:counts['active']-=1
        with patch.object(CognitiveStudy,'run_node_episode',counted):result=asyncio.run(run(self.root))
        self.assertEqual(result['status'],'completed_team_collection')
        self.assertEqual(counts['peak'],1)

    def test_saved_collection_cannot_relabel_limits_or_shared_task(self):
        result=asyncio.run(run(self.root));directory=Path(result['run_directory']);path=directory/'teams-plan.json'
        original=json.loads(path.read_text())
        for key,value in [('budget',{'max_llm_calls':999,'max_wall_seconds':600}),('communication',{'profile':'contributions','max_read_words':400,'links':[]}),('task_binding',{'path':'mission/other.md','sha256':'0'*64})]:
            p=deepcopy(original);p[key]=value;path.write_text(json.dumps(p))
            with self.assertRaises(ConfigurationError):report(directory)
        path.write_text(json.dumps(original))
        self.assertEqual(report(directory)['status'],'completed_team_collection')

    def test_viewer_rejects_unknown_initial_team_and_symlinked_run(self):
        with self.assertRaises(ConfigurationError):Service(self.root,initial_team='missing').state()
        result=asyncio.run(run(self.root));alias=self.root/'aliased';alias.symlink_to(Path(result['run_directory']),target_is_directory=True)
        with self.assertRaises(ConfigurationError):Service(run_directory=alias)
        child=Service(self.root).team_state('alpha')
        self.assertEqual(child['viewer']['multi_team']['study_file'],'teams/alpha/study.yaml')


    def test_shared_utf8_task_with_crlf_keeps_one_byte_binding(self):
        goal='PRIVATE_COMMON_GOAL: café CSV proposal.\r\nUse explicit acceptance criteria.\r\n'
        (self.root/'mission/task.md').write_bytes(goal.encode('utf-8'))
        compiled=compile_collection(self.root)
        result=asyncio.run(run(self.root))
        self.assertEqual(result['status'],'completed_team_collection')
        r=report(Path(result['run_directory']))
        self.assertEqual(r['task_binding'],compiled['task_binding'])
        for tid in ('alpha','beta','gamma'):
            self.assertEqual((Path(result['run_directory'])/'teams'/tid/'problem.md').read_bytes(),goal.encode('utf-8'))


    def test_local_wall_deadline_also_bounds_connected_boundary_waits(self):
        self.providers();self.connect(profile='summaries',source='alpha',target='beta')
        path=self.root/'teams/alpha/study.yaml';c=parse_yaml(path.read_text());c['base_overrides']['budget']['max_wall_seconds']=1;path.write_text(json.dumps(c))
        once=[];frames={}
        def callback(tid,body):
            if tid=='beta' and not once:
                once.append(True);submit(self.current()/'teams/beta',action='pause',apply=True)
        async def check():
            running=asyncio.create_task(run(self.root,live=True,approve_requests=24,transports=self.transports(frames,callback)))
            try:
                for _ in range(500):
                    if (self.root/'trials').exists() and list((self.root/'trials').iterdir()):
                        directory=self.current();summary=directory/'teams/alpha/summary.json'
                        if summary.exists() and json.loads(summary.read_text())['status']=='failed_or_incomplete':break
                    await asyncio.sleep(.01)
                else:self.fail('Local deadline did not end the connected boundary wait.')
                self.assertEqual(metadata(directory/'teams/beta','running')['mode'],'paused')
                submit(directory/'teams/beta',action='resume',apply=True)
                return await asyncio.wait_for(running,10)
            finally:
                if not running.done():running.cancel();await asyncio.gather(running,return_exceptions=True)
        result=asyncio.run(check())
        self.assertEqual(result['status'],'failed_or_incomplete')
        self.assertEqual(result['teams']['beta']['status'],'completed_text_workflow')
        self.assertEqual(result['teams']['alpha']['provider_requests'],1)

    def test_local_wall_deadline_also_bounds_aggregate_agent_slot_wait(self):
        from teamknitt.runtime import CognitiveStudy
        path=self.root/'teams/alpha/study.yaml';c=parse_yaml(path.read_text());c['base_overrides']['budget']['max_wall_seconds']=1;path.write_text(json.dumps(c))
        c=self.cfg();c['teams']=[c['teams'][1],c['teams'][0],c['teams'][2]];c['resources']['max_active_agents']=1;self.write(c)
        original=CognitiveStudy.run_node_episode
        async def check():
            release=asyncio.Event();started=asyncio.Event()
            async def hold_beta(runner,node,actor):
                if runner.team_id=='beta':started.set();await release.wait()
                return await original(runner,node,actor)
            with patch.object(CognitiveStudy,'run_node_episode',hold_beta):
                running=asyncio.create_task(run(self.root))
                try:
                    await asyncio.wait_for(started.wait(),5)
                    for _ in range(500):
                        path=self.current()/'teams/alpha/summary.json'
                        if path.exists() and json.loads(path.read_text())['status']=='failed_or_incomplete':break
                        await asyncio.sleep(.01)
                    else:self.fail('Local deadline did not end the aggregate slot wait.')
                    self.assertFalse(running.done())
                    release.set();return await asyncio.wait_for(running,10)
                finally:
                    if not running.done():running.cancel();await asyncio.gather(running,return_exceptions=True)
        result=asyncio.run(check())
        self.assertEqual(result['teams']['alpha']['status'],'failed_or_incomplete')
        self.assertEqual(result['teams']['beta']['status'],'completed_text_workflow')


if __name__=='__main__':unittest.main()
