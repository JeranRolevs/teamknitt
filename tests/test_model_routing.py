"""Verify active decision routing and resumption, including delegated agents, offline."""
import asyncio
import json
import unittest
from unittest.mock import patch
import test_providers as fixtures

from teamknitt.engine.planning import compile_plan
from teamknitt.engine.study import TextStudy, load_study


class ActiveRoutingTests(unittest.TestCase):
    setUp=fixtures.StudyTests.setUp
    tearDown=fixtures.StudyTests.tearDown

    def exercise(self,child=False):
        config=load_study(self.root)
        overrides=dict(config["base_overrides"])
        overrides["decisions"]={"mode":"selected_active","specialist":"specialist",
                                "allowed_specs":["semantic_choice.v1"]}
        plan=compile_plan(fixtures.PROJECT,config_overrides=overrides)
        with patch("teamknitt.engine.study.api_key",return_value=fixtures.FAKE_KEY):
            study=TextStudy(fixtures.PROJECT,self.root,config,plan,"routing",fixtures.FAKE_KEY)
        paths=[]; chat_count=0
        question={"action":"decision.assess","spec_id":"semantic_choice.v1",
                  "question":{"type":"noul","instructions":"Does the visible fixture say the checks passed?"}}
        final={"action":"final","summary":"fixture","candidate_output":"unverified fixture",
               "findings":[],"wisdom":[]}
        def transport(method,path,body):
            nonlocal chat_count
            paths.append((path,body["model"]))
            if path=="/assess":
                return {"model":"fixture-decision","answers":{"semantic_choice.v1":{"noul":.9}},"usage":{"input_tokens":8}}
            chat_count+=1
            if child and chat_count==1:
                action={"action":"delegate","task":"Use decision.assess on the visible fixture, then summarize."}
            elif chat_count==(2 if child else 1):
                action=question
            else:
                if chat_count==(3 if child else 2):
                    self.assertIn("decision/specialist",json.dumps(body["messages"]))
                    self.assertIn('0.9',json.dumps(body["messages"]))
                action=final
            return {"choices":[{"message":{"content":json.dumps(action)},"finish_reason":"stop"}],
                    "usage":{"prompt_tokens":5,"completion_tokens":3}}
        study.client._transport=transport
        study.specialist_client._transport=transport
        actor=plan["personas"][0]["instance_id"]
        result=asyncio.run(study.episode(actor,actor,study.roles[actor],"fixture"))
        self.assertIn("output",result)
        expected=[("/chat/completions","fixture-chat")]
        if child: expected.append(("/chat/completions","fixture-chat"))
        expected.extend([("/assess","fixture-decision"),("/chat/completions","fixture-chat")])
        if child: expected.append(("/chat/completions","fixture-chat"))
        self.assertEqual(paths,expected)
        self.assertEqual(study.calls,len(expected))

    def test_generation_calls_specialist_and_resumes_with_the_actual_answer(self):
        self.exercise()

    def test_child_inherits_the_generation_and_specialist_routes(self):
        self.exercise(child=True)


    def test_nonobject_question_is_rejected_with_a_typed_error(self):
        from teamknitt.engine.providers.chat import ProviderError,validate_question
        for question in ("Which check?",None,["raw","causality"]):
            with self.subTest(question=question),self.assertRaises(ProviderError) as error:
                validate_question(question)
            self.assertEqual(error.exception.kind,"invalid_question")
