"""User tasks/topologies, renamed packaging, safe drafts and optional observation tools.

No paid calls: execution tests use deterministic fixtures or injected loopback mocks.
"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from labtune.config import ConfigurationError, parse_yaml
from teamknitt import __version__
from teamknitt.builder import make_configuration, draft_configuration, apply_configuration
from teamknitt.cli import main
from teamknitt.config import compile_plan, load, resource
from teamknitt.observatory import ViewerService, handler, html
from teamknitt.reporting import build_report, plan_report
from teamknitt.runtime import run, CognitiveStudy
from teamknitt.scaffold import init
from teamknitt.topology import links, members

ROOT = Path(__file__).resolve().parents[1]


class TaskCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "team"
        init(self.root, goal="Brainstorm welcoming formats for a neighborhood workshop.")
        self.c = load(self.root)

    def plan(self, c=None):
        return compile_plan(self.root, self.c if c is None else c)

    def execute(self, c=None, **kw):
        info = asyncio.run(run(self.root, self.c if c is None else c, **kw))
        return info, build_report(Path(info["run_directory"]))

    def engine(self):
        return parse_yaml((self.root / "study.yaml").read_text())


class TaskAndTopologyTests(TaskCase):
    def test_product_package_cli_and_user_scope_are_renamed(self):
        import tomllib
        p = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        self.assertEqual(p["name"], "teamknitt")
        self.assertEqual(p["scripts"]["teamknitt"], "teamknitt.cli:main")
        self.assertNotIn("teamthill", p["scripts"])
        self.assertEqual(__version__, "0.3.0")
        self.assertTrue((self.root / "mission/task.md").is_file())
        self.assertNotIn("scientist", self.c["mission"]["deliverable"])

    def test_default_task_team_has_explicit_user_controls_not_a_fixed_research_lab(self):
        p = self.plan()
        self.assertEqual(p["schema_version"], 3)
        self.assertEqual(len(p["labtune_plan"]["personas"]), 3)
        self.assertEqual(p["labtune_plan"]["design"]["id"], "teamknitt_task_team")
        self.assertEqual(self.c["mission"]["purpose"], "brainstorm")
        self.assertEqual(p["provider_request_cap"], 24)
        self.assertEqual(p["api_calls"], 0)
        self.assertEqual(self.c["mission"]["review"], "user_review")

    def test_each_purpose_is_a_user_choice_not_forced_scientific_research(self):
        for purpose in ("task", "brainstorm", "goal", "research"):
            c = make_configuration(purpose=purpose)
            self.assertEqual(self.plan(c)["configuration"]["mission"]["purpose"], purpose)
            self.assertNotIn("scripted", json.dumps(c))

    def test_topology_counts_are_exact_and_layouts_are_canonical_for_every_size(self):
        geometry = json.loads(resource("topology-layouts.json").read_text())
        for n in range(1, 17):
            for kind, count in (("fully_connected", n*(n-1)), ("hub_and_spoke", 2*(n-1)), ("hierarchical", 2*(n-1)), ("ring", 0 if n==1 else 2 if n==2 else 2*n)):
                with self.subTest(n=n,kind=kind):
                    routes = links({"topology":kind,"members":n,"links":[]})
                    self.assertEqual(len(routes), count)
                    self.assertEqual(len(routes), len(set(routes)))
                    positions = geometry[kind][str(n)]
                    self.assertEqual([p["id"] for p in positions], members(n))
                    self.assertTrue(all(0<=p["x"]<=1 and 0<=p["y"]<=1 for p in positions))

    def test_custom_links_are_directed_and_no_reverse_is_inferred(self):
        team={"topology":"custom","members":3,"links":[{"source":"member.1","target":"member.3"}]}
        self.assertEqual(links(team),[("member.1","member.3")])
        for link in ({"source":"member.1","target":"member.1"},{"source":"member.1","target":"unknown"},team["links"][0]):
            bad=deepcopy(team);bad["links"].append(link)
            with self.assertRaises(ConfigurationError):links(bad)
        with self.assertRaises(ConfigurationError):links({"topology":"ring","members":3,"links":team["links"]})

    def test_member_count_bounds_and_count_cognition_mismatch_are_explicit(self):
        for n in (0,17,True,1.5):
            with self.assertRaises(ConfigurationError):members(n)
        c=deepcopy(self.c);c["team"]["members"]=4
        with self.assertRaisesRegex(ConfigurationError,"role bindings"):self.plan(c)

    def test_large_team_does_not_raise_engine_budget_or_concurrency(self):
        c=make_configuration(count=16,communication="intermediate")
        p=self.plan(c)
        self.assertEqual(p["provider_request_cap"],24)
        self.assertEqual(p["labtune_plan"]["resources"]["max_active_agents"],6)
        self.assertFalse(p["reference_request_case"]["cap_covers_that_case"])

    def test_all_sharing_profiles_translate_to_explicit_engine_controls(self):
        for profile in ("none","low","intermediate","high","wisdom_only"):
            c=make_configuration(communication=profile)
            p=self.plan(c)
            self.assertEqual(p["labtune_plan"]["communication"]["effective_profile"],profile)
            shared=[r for r in c["cognition"]["representations"] if r["kind"]=="workspace" and len(r["readers"])>1]
            self.assertEqual(bool(shared),profile=="high")

    def test_goal_text_binds_identity_and_is_not_changed_by_a_draft(self):
        p=self.plan();before=(self.root/"mission/task.md").read_text()
        draft=draft_configuration(self.c,count=4,topology="ring")
        self.plan(draft)
        self.assertEqual((self.root/"mission/task.md").read_text(),before)
        (self.root/"mission/task.md").write_text("Plan a different user-selected goal.")
        self.assertNotEqual(p["configuration_sha256"],self.plan()["configuration_sha256"])

    def test_task_handoff_cannot_bypass_a_selected_topology(self):
        c=make_configuration(count=4,topology="ring")
        c["cognition"]["handoffs"][0].update(producer="member.1",consumer="member.3",representation="notes-1")
        with self.assertRaisesRegex(ConfigurationError,"topology"):self.plan(c)


class DraftSafetyTests(TaskCase):
    def test_cli_draft_does_not_write_files_or_read_credentials(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch("teamknitt.runtime.api_key",side_effect=AssertionError("No credential read")),redirect_stdout(io.StringIO()) as out:
            status=main(["configure","--workspace",str(self.root),"--members","4","--topology","ring","--communication","intermediate"])
        self.assertEqual(status,0)
        self.assertEqual(json.loads(out.getvalue())["status"],"configuration_draft_only")
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_apply_requires_acknowledged_reset_and_keeps_private_backup(self):
        draft=draft_configuration(self.c,count=4,topology="hub_and_spoke")
        before=(self.root/"team.yaml").read_bytes();engine=(self.root/"study.yaml").read_bytes();goal=(self.root/"mission/task.md").read_bytes()
        with self.assertRaises(ConfigurationError):apply_configuration(self.root,draft)
        result=apply_configuration(self.root,draft,reset_cognition=True)
        self.assertEqual(Path(result["backup"]).read_bytes(),before)
        if os.name=='posix':self.assertEqual(Path(result['backup']).stat().st_mode&0o777,0o600)
        self.assertEqual((self.root/"study.yaml").read_bytes(),engine)
        self.assertEqual((self.root/"mission/task.md").read_bytes(),goal)
        self.assertEqual(load(self.root)["team"]["members"],4)

    def test_applying_waits_for_engine_lock_but_drafting_is_allowed(self):
        import fcntl
        with (self.root/".run.lock").open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            draft=draft_configuration(self.c,count=4)
            self.plan(draft)
            with self.assertRaisesRegex(ConfigurationError,"run owns"):apply_configuration(self.root,draft,reset_cognition=True)
        self.assertEqual(load(self.root)["team"]["members"],3)

    def test_viewer_preview_does_not_apply_or_change_model_budget(self):
        service=ViewerService(plan_report(self.plan()),workspace=self.root)
        before=(self.root/"team.yaml").read_bytes()
        report=service.draft({"members":["4"],"topology":["hub_and_spoke"],"communication":["intermediate"],"purpose":["goal"]})
        self.assertEqual(report["viewer"]["selection"],"draft_only")
        self.assertEqual(len(report["cognition"]["roles"]),4)
        self.assertEqual(report["budget"]["max_llm_calls"],24)
        self.assertEqual(report["generation_provider"]["model"],"YOUR_MODEL_ID")
        self.assertEqual((self.root/"team.yaml").read_bytes(),before)

    def test_builder_preserves_selected_engine_variant_and_its_budget(self):
        s=self.engine()
        s['variants'].append({'id':'user-selected','overrides':{'lab':{'design_file':'designs/task-team.md'},'budget':{'max_llm_calls':9}}})
        (self.root/'study.yaml').write_text(json.dumps(s))
        self.c['engine']['variant']='user-selected'
        self.c['communication']['wisdom']=True
        draft=draft_configuration(self.c,count=4,topology='ring')
        self.assertEqual(draft['engine']['variant'],'user-selected')
        self.assertTrue(draft['communication']['wisdom'])
        self.assertEqual(self.plan(draft)['provider_request_cap'],9)

    def test_saved_run_view_cannot_draft_and_bad_query_fields_are_rejected(self):
        service=ViewerService(plan_report(self.plan()))
        with self.assertRaises(ConfigurationError):service.draft({"members":["4"]})
        service=ViewerService(plan_report(self.plan()),workspace=self.root)
        for query in ({"path":["/etc/passwd"]},{"members":["0"]},{"members":["2","3"]}):
            with self.assertRaises((ConfigurationError,ValueError)):service.draft(query)


class TaskExecutionAndMonitoringTests(TaskCase):
    def test_task_fixture_produces_reviewable_contributions_not_automatic_goal_success(self):
        info,r=self.execute()
        self.assertEqual(info["provider_requests"],0)
        self.assertEqual(r["mission"]["purpose"],"brainstorm")
        self.assertIsNone(info["goal_achieved"])
        self.assertEqual(info["task_review"],"awaiting_user_review")
        self.assertIn('member.1',Path(info['deliverable']).read_text())
        self.assertEqual(r["usage"]["provider_requests"],0)
        self.assertIn('user', {v['author'] for v in r['versions']})

    def test_every_topology_filters_artifact_exposure_at_runtime(self):
        for kind in ("fully_connected","hub_and_spoke","ring","hierarchical"):
            c=make_configuration(count=4,topology=kind)
            _,r=self.execute(c)
            allowed=set(links(c['team']))
            exposed=[(e['author'],e['actor']) for e in r['events'] if e['kind']=='representation_exposed' and e['author'] not in {e['actor'],'user','researcher'}]
            self.assertTrue(exposed)
            self.assertTrue(set(exposed)<=allowed)
            if kind=='ring':self.assertNotIn(('member.1','member.3'),exposed)
            if kind=='hub_and_spoke':self.assertFalse(any(a!='member.1' and b!='member.1' for a,b in exposed))

    def test_fragmented_four_member_fixture_preserves_partial_agreement_not_a_binary_score(self):
        _,r=self.execute(make_configuration(count=4),policy='fragmented')
        self.assertEqual(r['snapshots'][-1]['reported_plan_pair_agreement'],.5)
        self.assertEqual(r['snapshots'][-1]['perceived_in_sync_reports'],4)
        self.assertIsNone(r['observations']['aggregate_score'])

    def test_no_sharing_has_no_peer_artifact_exposure_or_handoff_contract(self):
        _,r=self.execute(make_configuration(communication='none'))
        self.assertEqual(r['handoffs'],[])
        self.assertFalse(any(e['kind']=='representation_exposed' and e['author'] not in {e['actor'],'user','researcher'} for e in r['events']))

    def test_optional_observations_can_be_disabled_or_selected(self):
        c=deepcopy(self.c);c['observations']['enabled']=False
        _,r=self.execute(c)
        self.assertFalse(r['observations']['enabled']);self.assertEqual(r['observations']['dimensions'],[])
        self.assertNotIn('coordination_stability',r)
        c=deepcopy(self.c);c['observations']['dimensions']=['coupling']
        _,r=self.execute(c)
        self.assertEqual([d['id'] for d in r['observations']['dimensions']],['coupling'])
        self.assertIsNone(r['observations']['aggregate_score'])

    def test_dynamic_concepts_not_supported_by_short_traces_are_not_fabricated(self):
        _,r=self.execute()
        dims={d['id']:d for d in r['observations']['dimensions']}
        for key in ('attractors','synchronization','fractals'):
            self.assertEqual(dims[key]['status'],'not_estimated')
            self.assertNotIn('score',dims[key])
        self.assertEqual(dims['local_global']['status'],'descriptive_only')
        self.assertTrue(dims['local_global']['data']['actions_by_wave'])

    def test_monitor_selects_matching_records_not_an_old_different_goal(self):
        service=ViewerService(plan_report(self.plan()),workspace=self.root)
        self.assertEqual(service.state()['mode'],'configuration')
        info,_=self.execute()
        self.assertEqual(service.state()['run_id'],Path(info['run_directory']).name)
        (self.root/'mission/task.md').write_text('A different user-selected task.')
        self.assertEqual(service.state()['mode'],'configuration')
        self.assertEqual(service.state('setup')['mode'],'configuration')

    def mock_engine(self,profile='intermediate'):
        s=self.engine();s['provider'].update(model='local-fixture',base_url='http://127.0.0.1:1',api_key_env=None)
        (self.root/'study.yaml').write_text(json.dumps(s))
        return make_configuration(communication=profile)

    def test_live_metadata_is_available_while_provider_transport_is_in_flight(self):
        c=self.mock_engine();seen=[]
        def transport(method,path,body):
            dirs=list((self.root/'trials').iterdir())
            r=build_report(dirs[-1]);seen.append((r['status'],r['usage']['provider_requests'],r['last_telemetry'],len(r['current_operations'])))
            return {'choices':[{'message':{'content':json.dumps({'action':'final','summary':'Proposed workshop ideas','candidate_output':'Offer a low-pressure welcome circle and optional small-group activities.','findings':[],'wisdom':[]})}}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}
        info,r=self.execute(c,live=True,approve_requests=24,transport=transport)
        self.assertTrue(any(status=='running' and count>0 and stamp and active>0 for status,count,stamp,active in seen))
        self.assertEqual(info['provider_requests'],12)
        self.assertEqual(r['usage']['chat_input_tokens'],120)
        self.assertIsNone(r['goal_achieved'])
        self.assertIn('welcome circle',Path(info['deliverable']).read_text())
        self.assertNotIn('welcome circle',json.dumps(r))

    def test_low_sharing_in_generic_tasks_carries_unverified_blockers_not_fake_measured_failures(self):
        c=self.mock_engine('low');frames=[]
        def transport(method,path,body):
            for m in body['messages']:
                if m['role']=='user':
                    try:frame=json.loads(m['content'])
                    except ValueError:continue
                    if 'peer_views' in frame:frames.append(frame)
            return {'choices':[{'message':{'content':json.dumps({'action':'final','summary':'Contribution','candidate_output':'Idea','findings':[{'kind':'blocker','text':'A reported access constraint needs user review.'}],'wisdom':[]})}}]}
        _,r=self.execute(c,live=True,approve_requests=24,transport=transport)
        views=[f['peer_views']['labtune'].get('low.md','') for f in frames]
        self.assertTrue(any('member_report_not_independently_verified' in v for v in views))
        self.assertFalse(any('measured_development_evidence' in v for v in views))

    def test_live_authorization_and_nonempty_user_task_remain_required(self):
        with self.assertRaises(ConfigurationError):asyncio.run(run(self.root,self.c,live=True))
        c=self.mock_engine();(self.root/'mission/task.md').write_text('AWAITING_USER_TASK')
        with self.assertRaises(ConfigurationError):asyncio.run(run(self.root,c,live=True,approve_requests=24))
        self.assertFalse((self.root/'trials').exists())


class ObserverHTTPAndPackagingTests(TaskCase):
    def test_http_api_can_only_read_or_preview_not_start_or_apply(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(ViewerService(plan_report(self.plan()),workspace=self.root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(thread.join,3);self.addCleanup(server.shutdown)
        url=f'http://127.0.0.1:{server.server_address[1]}'
        def get(path):
            with urllib.request.urlopen(url+path,timeout=5) as r:return r.status,json.loads(r.read())
        self.assertEqual(get('/api/state')[1]['mode'],'configuration')
        self.assertEqual(len(get('/api/draft?members=4&topology=ring')[1]['cognition']['roles']),4)
        for path,code in (('/api/draft?members=0',400),('/api/draft?unknown=x',400),('/etc/passwd',404),('/api/run',404)):
            with self.assertRaises(urllib.error.HTTPError) as caught:get(path)
            self.assertEqual(caught.exception.code,code)
            caught.exception.close()
        request=urllib.request.Request(url+'/api/run',data=b'{}',method='POST')
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=5)
        self.assertEqual(caught.exception.code,405)
        caught.exception.close()
        self.assertEqual(load(self.root)['team']['members'],3)
        self.assertFalse((self.root/'trials').exists())

    def test_offline_html_embeds_renamed_app_and_javascript_is_valid(self):
        page=html(plan_report(self.plan()))
        self.assertIn('teamknitt',page);self.assertIn('#ffda00',page);self.assertIn('#302e29',page)
        self.assertNotIn('__TEAMKNITT_APP_JS__',page)
        node=shutil.which('node')
        if not node:self.skipTest('Node is optional')
        for script in re.findall(r'<script>([\s\S]*?)</script>',page):
            p=subprocess.run([node,'-e','new Function('+json.dumps(script)+');'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_license_terms_and_credits_remain_unchanged_despite_wider_task_scope(self):
        for name in ('LICENSE','LICENSING.md'):
            self.assertEqual((self.root/name).read_bytes(),(ROOT/name).read_bytes())
        text=(self.root/'README.md').read_text()
        self.assertIn('not',text);self.assertIn('permission for commercial use',text)
        self.assertIn('Goran Mitevski',text);self.assertIn('Pioneertown B.V.',text)


if __name__=='__main__':unittest.main()
