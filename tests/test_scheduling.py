"""Workflow dependency, concurrency and exposure barriers; no external services."""
import asyncio
import unittest

from teamknitt.engine.planning import compile_plan
from teamknitt.engine.study import StudyError, TextStudy
import test_providers as fixtures
PROJECT,FAKE_KEY=fixtures.PROJECT,fixtures.FAKE_KEY


class GraphTests(unittest.TestCase):
    setUp=fixtures.StudyTests.setUp
    tearDown=fixtures.StudyTests.tearDown

    def make_study(self,width):
        from teamknitt.engine.study import load_study
        config=load_study(self.root)
        plan=compile_plan(PROJECT,config_overrides=config["base_overrides"])
        plan["resources"]["max_active_agents"]=width
        first,second=[p["instance_id"] for p in plan["personas"][:2]]
        def node(name,actor,deps):
            return {"id":name,"kind":"research_episode","actors":[actor],
                    "depends_on":deps,"research_activity":"planned"}
        plan["work_graph"]=[node("left",first,[]),node("right",second,[]),
                            node("after",first,["left","right"])]
        return TextStudy(PROJECT,self.root,config,plan,"scheduler",FAKE_KEY)

    def exercise(self,width):
        study=self.make_study(width)
        active=peak=0
        observations={}
        async def episode(actor,team,role,task):
            nonlocal active,peak
            active+=1; peak=max(peak,active)
            observations[task]=len(study.outputs)
            await asyncio.sleep(0)
            active-=1
            return {"actor":actor,"team":team,"output":{"summary":task}}
        study.episode=episode
        asyncio.run(study.run_graph())
        self.assertEqual(observations,{"left":0,"right":0,"after":2})
        self.assertEqual(len(study.outputs),3)
        return peak

    def test_independent_tracks_overlap_and_publish_after_dependency_wave(self):
        self.assertEqual(self.exercise(2),2)

    def test_resource_cap_preserves_the_same_peer_snapshot(self):
        self.assertEqual(self.exercise(1),1)

    def test_cycle_is_rejected_before_any_episode(self):
        study=self.make_study(2)
        async def forbidden_episode(*args,**kwargs):
            self.fail("Invalid graphs must not start an episode.")
        study.episode=forbidden_episode
        study.plan["work_graph"][0]["depends_on"]=["after"]
        with self.assertRaises(StudyError):
            asyncio.run(study.run_graph())

class OutputLimitTests(unittest.TestCase):
    def test_reasoning_only_truncation_reports_the_output_limit(self):
        from teamknitt.engine.providers.chat import ChatCompletionsClient,ProviderError
        client=ChatCompletionsClient(FAKE_KEY,model="fixture-chat",base_url="https://generation.example.test/v1",transport=lambda *args: {
            "choices":[{"finish_reason":"length","message":{"content":"","reasoning_content":"fixture"}}]})
        with self.assertRaises(ProviderError) as failure:
            asyncio.run(client.generate([{"role":"user","content":"fixture"}],budget_ref="offline"))
        self.assertEqual(failure.exception.kind,"output_limit")

    def test_explicit_reasoning_controls_are_sent_only_to_chat(self):
        from teamknitt.engine.providers.chat import ChatCompletionsClient
        captured=[]
        def transport(method,path,body):
            captured.append(body)
            return {"choices":[{"finish_reason":"stop","message":{"content":"{}"}}]}
        client=ChatCompletionsClient(FAKE_KEY,model="fixture-chat",base_url="https://generation.example.test/v1",request_options={"reasoning_effort":"low","chat_template_kwargs":{"enable_thinking":False}},transport=transport)
        asyncio.run(client.generate([{"role":"user","content":"fixture"}],budget_ref="offline"))
        self.assertEqual(captured[0]["reasoning_effort"],"low")
        self.assertEqual(captured[0]["chat_template_kwargs"],{"enable_thinking":False})


class ActionFormatTests(unittest.TestCase):
    setUp=fixtures.StudyTests.setUp
    tearDown=fixtures.StudyTests.tearDown

    def study(self,replies):
        from teamknitt.engine.study import load_study
        config=load_study(self.root)
        plan=compile_plan(PROJECT,config_overrides=config["base_overrides"])
        study=TextStudy(PROJECT,self.root,config,plan,"format",FAKE_KEY)
        output=iter(replies)
        def transport(*args):
            return {"choices":[{"finish_reason":"stop","message":{"content":next(output)}}]}
        study.client._transport=transport
        actor=plan["personas"][0]["instance_id"]
        return study,actor

    def test_malformed_action_executes_nothing_and_correction_is_budgeted(self):
        import json
        final={"action":"final","summary":"fixture","findings":[],"wisdom":[],"candidate_output":"unverified"}
        study,actor=self.study(["{invalid",json.dumps(final)])
        result=asyncio.run(study.episode(actor,actor,study.roles[actor],"fixture"))
        self.assertEqual(result["output"]["summary"],"fixture")
        self.assertEqual(study.calls,2)
        events=(study.root/"events.jsonl").read_text()
        self.assertIn('"kind": "action_rejected"',events)
        self.assertFalse((study.root/"experiments").exists())

    def test_repeated_bad_json_stops_at_the_existing_episode_limit(self):
        study,actor=self.study(["invalid"]*3)
        with self.assertRaises(StudyError):
            asyncio.run(study.episode(actor,actor,study.roles[actor],"fixture"))
        self.assertEqual(study.calls,3)
        self.assertFalse((study.root/"experiments").exists())
