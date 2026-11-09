"""Offline provider and text-runner checks. No real key or network request."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.contracts import CallerContext, DecisionRequest, DecisionStatus
from teamknitt.engine.providers.chat import ChatCompletionsClient, ChatDecisionClient
from teamknitt.engine.providers.typed import TypedDecisionClient, TypedDecisionBackend
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.providers.questions import validate_question
from teamknitt.engine.study import StudyError, TextStudy, api_key, compare, doctor, load_study, plans, run_variant
from teamknitt.engine.planning import compile_plan

PROJECT = Path(__file__).resolve().parents[1]
FAKE_KEY = "offline-test-key-not-a-credential"


DECISION_FIXTURE = {"adapter": "typed", "base_url": "https://decisions.example.test/v1",
    "model": "fixture-decision", "endpoint": "/assess", "api_key_env": "TEAMKNITT_DECISION_API_KEY",
    "env_file": ".env", "timeout_seconds": 10, "max_parallel_requests": 2}


def fixture_config():
    return {
        "schema_version": 1, "name": "offline-fixture", "problem_file": "mission/problem.md",
        "provider": {"base_url": "https://generation.example.test/v1", "model": "fixture-chat",
                     "endpoint": "/chat/completions", "models_endpoint": "/models",
                     "api_key_env": "TEAMKNITT_API_KEY", "env_file": ".env", "timeout_seconds": 10,
                     "max_output_tokens": 500, "max_parallel_requests": 2, "request_options": {}},
        "decision_providers": {"specialist": dict(DECISION_FIXTURE)},
        "runtime": {"mode": "text_only", "max_actions_per_episode": 3,
                    "max_findings": 3, "comparison_metrics": ["quality"]},
        "base_overrides": {"communication": {"profile": "none", "wisdom": False},
                           "decisions": {"allowed_specs": ["semantic_choice.v1"]}},
        "variants": [{"id": "a-none", "overrides": {}}],
    }


class ProviderTests(unittest.TestCase):
    def chat(self, **kwargs):
        options = {"model": "fixture-chat", "base_url": "https://generation.example.test/v1", **kwargs}
        return ChatCompletionsClient(FAKE_KEY, **options)

    def test_chat_endpoint_options_output_field_and_receipts_are_configurable(self):
        requests, events = [], []
        def transport(method, path, body):
            requests.append((method, path, body))
            return {"model": "resolved-fixture", "choices": [{"message": {"content": "OK"}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1}}
        client = self.chat(endpoint="/custom/generate", max_tokens=77, max_output_field="max_completion_tokens",
            request_options={"temperature": .2, "generation_options": {"think": False}},
            transport=transport, on_event=events.append)
        reply=asyncio.run(client.generate([{"role":"user","content":"fixture"}],budget_ref="fixture"))
        self.assertEqual(requests[0][1],"/custom/generate")
        self.assertEqual(requests[0][2]["max_completion_tokens"],77)
        self.assertNotIn("max_tokens",requests[0][2])
        self.assertFalse(requests[0][2]["stream"])
        self.assertEqual(requests[0][2]["generation_options"],{"think":False})
        self.assertEqual(reply["model"],"resolved-fixture")
        self.assertEqual(events[0]["request_id"],events[1]["request_id"])
        self.assertNotIn(FAKE_KEY,json.dumps(events))

    def test_options_cannot_override_bounds_identity_or_credentials(self):
        for options in ({"model":"other"},{"stream":True},{"max_tokens":999},{"nested":{"api_key":FAKE_KEY}},{"temperature":float('nan')}):
            with self.subTest(options=options),self.assertRaises(ProviderError):
                self.chat(request_options=options)

    def test_invalid_urls_fail_without_a_request_and_loopback_is_supported(self):
        for url in ("http://remote.example.test/v1","https://user:pass@example.test/v1","https://example.test/v1?key=x",
                    "https://[broken", "https://example.test:invalid/v1", "https://example.test/with space"):
            with self.subTest(url=url),self.assertRaises(ProviderError):
                self.chat(base_url=url)
        self.assertEqual(self.chat(base_url="http://127.0.0.1:8000/v1").base_url,"http://127.0.0.1:8000/v1")

    def test_chat_decision_adapter_validates_answers_and_preserves_usage(self):
        client=ChatDecisionClient(FAKE_KEY,model="judge",base_url="https://judge.example.test/v1",transport=lambda *args:{
            "model":"judge-resolved","choices":[{"message":{"content":json.dumps({"answers":{"q":{"noul":.8}}})}}],
            "usage":{"prompt_tokens":7,"completion_tokens":2}})
        result=asyncio.run(client.assess_text("visible",{"q":{"type":"noul","instructions":"Question?"}}))
        self.assertEqual(result["answers"]["q"]["noul"],.8)
        self.assertEqual(result["usage"]["prompt_tokens"],7)
        self.assertEqual(result["model"],"judge-resolved")

    def test_scope_is_checked_before_chat_decision_dispatch(self):
        client=ChatDecisionClient(FAKE_KEY,model="judge",base_url="https://judge.example.test/v1",
            transport=lambda *args:self.fail("No out-of-scope request"))
        caller=CallerContext("a","a","m","e","c","k",("allowed",),"b")
        request=DecisionRequest("r","semantic_choice.v1","fixture",("hidden",),caller,{"type":"noul","instructions":"Question?"})
        result=asyncio.run(TypedDecisionBackend(client,lambda req:self.fail("No hidden context")).assess(request))
        self.assertEqual(result.status,DecisionStatus.INVALID)

    def test_missing_chat_output_and_invalid_questions_are_typed_errors(self):
        for reply in ({},{"choices":[]},{"choices":[{"message":{"content":""}}]},{"choices":[{"finish_reason":"length"}]}):
            client=self.chat(transport=lambda *args:reply)
            with self.subTest(reply=reply),self.assertRaises(ProviderError):
                asyncio.run(client.generate([],budget_ref="fixture"))
        with self.assertRaises(ProviderError):
            validate_question({"type":"noul","instruction":"typo"})


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "mission").mkdir()
        (self.root / "mission/problem.md").write_text("AWAITING_USER_PROBLEM")
        (self.root / "study.yaml").write_text(json.dumps(fixture_config()))

    def tearDown(self):
        self.temp.cleanup()

    def test_private_dotenv_is_read_without_putting_key_in_public_settings(self):
        (self.root / ".env").write_text("TEAMKNITT_API_KEY='" + FAKE_KEY + "'\n")
        config = load_study(self.root)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(api_key(self.root, config["provider"]), FAKE_KEY)
            result = asyncio.run(doctor(PROJECT, self.root))
        self.assertTrue(result["key_present"])
        self.assertNotIn(FAKE_KEY, json.dumps(result))
        self.assertFalse(result["live_checks_run"])

    def test_problem_placeholder_blocks_before_provider_or_trial_creation(self):
        with self.assertRaises(StudyError):
            asyncio.run(run_variant(PROJECT, self.root, "a-none"))
        self.assertFalse((self.root / "trials").exists())

    def test_live_doctor_probes_preview_directly_instead_of_requiring_it_in_models(self):
        config = fixture_config()
        config["base_overrides"]["decisions"].update(mode="selected_active", specialist="specialist")
        (self.root / "study.yaml").write_text(json.dumps(config))
        calls = []
        def transport(client, method, path, body):
            calls.append(path)
            if path == "/models":
                return {"data": [{"id": "fixture-chat"}]}
            if path == "/chat/completions":
                return {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}], "usage": {}}
            return {"model":"fixture-decision", "answers": {"connection": {"noul": .95}}, "usage": {"input_tokens": 8}}
        with patch.dict(os.environ, {"TEAMKNITT_API_KEY": FAKE_KEY, "TEAMKNITT_DECISION_API_KEY": FAKE_KEY}), patch.object(ChatCompletionsClient, "_http", transport), patch.object(TypedDecisionClient, "_http", transport):
            result = asyncio.run(doctor(PROJECT, self.root, live=True))
        self.assertEqual(result["status"], "connected")
        self.assertEqual(calls, ["/models", "/chat/completions", "/assess"])
        self.assertFalse(result["research_started"])

    def test_real_workflow_structure_runs_with_fake_responses_and_never_verifies_proposals(self):
        (self.root / "mission/problem.md").write_text("Offline fixture: propose a reversible improvement.")
        def transport(client, method, path, body):
            output = {"action": "final", "summary": "Unverified proposal", "findings": [],
                      "wisdom": [], "candidate_output": "Proposed experiment, not executed."}
            return {"choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20}}
        with patch.dict(os.environ, {"TEAMKNITT_API_KEY": FAKE_KEY}), patch.object(ChatCompletionsClient, "_http", transport):
            result = asyncio.run(run_variant(PROJECT, self.root, "a-none"))
        self.assertEqual(result["status"], "completed_text_workflow")
        self.assertEqual(result["verification_status"], "not_evaluated")
        self.assertEqual(result["provider_post_requests"], 6)
        self.assertEqual(result["usage"]["chat_input_tokens"], 60)
        self.assertEqual(result["usage"]["chat_output_tokens"], 120)
        self.assertNotIn(FAKE_KEY, (self.root / "trials" / result["trial_id"] / "events.jsonl").read_text())
        self.assertFalse((self.root / "trials" / result["trial_id"] / "communication").exists())
        report = compare(self.root)
        self.assertEqual(report["trials"], 1)
        self.assertIsNone(report["automatic_winner"])

    def test_shadow_result_is_retained_but_not_returned_to_acting_agent(self):
        config = load_study(self.root)
        overrides = deepcopy(config["base_overrides"])
        overrides["decisions"].update(mode="shadow", specialist="specialist")
        plan = compile_plan(PROJECT, config_overrides=overrides)
        with patch("teamknitt.engine.study.api_key",return_value=FAKE_KEY):
            study = TextStudy(PROJECT, self.root, config, plan, "shadow", FAKE_KEY)
        def transport(method, path, body):
            if path == "/assess":
                return {"model":"fixture-decision", "answers": {"semantic_choice.v1": {"noul": .9}}, "usage": {"input_tokens": 4}}
            return {"choices": [{"message": {"content": '{"noul":0.1}'}, "finish_reason": "stop"}], "usage": {}}
        study.client._transport = transport
        study.specialist_client._transport = transport
        answer = asyncio.run(study.decision("a", "a", "e",
            {"spec_id": "semantic_choice.v1", "question": {"type": "noul", "instructions": "Fixture?"}},
            [{"role": "user", "content": "Visible fixture only."}]))
        self.assertEqual(answer["answer"]["noul"], .1)
        events = (study.root / "events.jsonl").read_text()
        self.assertIn('"visible_to_agent": false', events)
        self.assertIn('0.9', events)

    def test_external_overrides_still_obey_global_budget_validation(self):
        with self.assertRaises(ValueError):
            compile_plan(PROJECT, config_overrides={"budget": {"max_evaluations": 1, "confirmation_evaluations_reserved": 2}})


if __name__ == "__main__":
    unittest.main()
