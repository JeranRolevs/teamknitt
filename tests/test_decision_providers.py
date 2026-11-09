"""Offline specialist/custom routing, isolation, fallback and budget checks. No live account."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import test_providers as fixtures

from teamknitt.engine.config import ConfigurationError
from teamknitt.engine.contracts import CallerContext, DecisionRequest, DecisionStatus
from teamknitt.engine.decisions import resolve_specialist
DECISION_FIXTURE = fixtures.DECISION_FIXTURE
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.providers.typed import TypedDecisionClient, TypedDecisionBackend
from teamknitt.engine.study import StudyError, TextStudy, doctor, load_study, plans, prepare

DECISION_KEY = "offline-specialist-test-not-a-credential"
CUSTOM_KEY = "offline-custom-test-not-a-credential"
QUESTION = {"type": "noul", "instructions": "Does the visible fixture say the checks passed?"}


def answer(model="fixture-version", probability=.9):
    return {"model": model, "answers": {"semantic_choice.v1": {"type": "noul", "noul": probability}},
            "usage": {"input_tokens": 8, "output_tokens": 2}}


def decision_client(key, **kwargs):
    return TypedDecisionClient(key, **{"model":"fixture-decision", "base_url":"https://decisions.example.test/v1", **kwargs})


class TypedProviderTests(unittest.TestCase):
    def test_typed_shapes_preserve_all_types_model_and_usage(self):
        calls, events = [], []
        questions = {"a": QUESTION, "b": {"type": "choice", "instructions": "Choose a route",
                     "criteria": {"x": "Use X", "y": "Use Y"}},
                     "c": {"type": "score", "instructions": "Rate urgency",
                           "criteria": ["Routine", "Urgent"]}}
        def transport(method, path, body):
            calls.append((method, path, body))
            return {"model": "fixture-pinned", "answers": {
                "a": {"type": "noul", "noul": .9},
                "b": {"type": "choice", "choice": "x", "confidence": .8, "probabilities": {"x": .9, "y": .1}},
                "c": {"type": "score", "score": .3, "confidence": .4, "probabilities": {"0": .7, "1": .3}}},
                "usage": {"input_tokens": 24, "output_tokens": 5}}
        client = decision_client(DECISION_KEY, transport=transport, on_event=events.append)
        result = asyncio.run(client.assess_text("Visible fixture only", questions))
        self.assertEqual(calls, [("POST", "/assess", {"model": "fixture-decision", "state": "Visible fixture only", "questions": questions})])
        self.assertEqual(result["model"], "fixture-pinned")
        self.assertEqual(result["answers"]["c"]["probabilities"], {"0": .7, "1": .3})
        self.assertNotIn(DECISION_KEY, json.dumps(events))

    def test_scope_is_checked_before_context_resolution_or_http(self):
        def forbidden(*args):
            self.fail("No context resolution or HTTP for hidden input.")
        client = decision_client(DECISION_KEY, transport=forbidden)
        caller = CallerContext("a", "a", "m", "e", "c", "k", ("allowed",), "budget")
        request = DecisionRequest("r", "semantic_choice.v1", "fixture", ("hidden",), caller, QUESTION)
        result = asyncio.run(TypedDecisionBackend(client, forbidden).assess(request))
        self.assertEqual(result.status, DecisionStatus.INVALID)

    def test_malformed_answers_and_wrong_types_are_rejected(self):
        bad = [
            {"model": "v", "answers": {"other": {"noul": .9}}},
            {"model": "v", "answers": {"semantic_choice.v1": {"noul": 1.5}}},
            {"model": "v", "answers": {"semantic_choice.v1": {"type": "choice", "noul": .9}}},
            {"answers": {"semantic_choice.v1": {"noul": .9}}},
        ]
        for response in bad:
            with self.subTest(response=response):
                client = decision_client(DECISION_KEY, transport=lambda *args: response)
                with self.assertRaises(ProviderError):
                    asyncio.run(client.assess_text("fixture", {"semantic_choice.v1": QUESTION}))

    def test_limits_fail_before_reserving_a_request(self):
        calls = []
        client = decision_client(DECISION_KEY, reserve=lambda: calls.append("reserved"),
                                 transport=lambda *args: self.fail("No HTTP"))
        with self.assertRaises(ProviderError) as error:
            asyncio.run(client.assess_text("x" * (1024 * 1024), {"q": QUESTION}))
        self.assertEqual(error.exception.kind, "request_limit")
        self.assertEqual(calls, [])

    def test_configured_endpoint_uses_its_own_bearer_key_and_no_redirects(self):
        seen = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return json.dumps(answer()).encode()
        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                return Response()
        with patch("teamknitt.engine.providers.http.urllib.request.build_opener", return_value=Opener()):
            client = decision_client(CUSTOM_KEY, base_url="https://decision.example.invalid/api",
                                     endpoint="/judge", model="custom-model", provider_id="custom/test")
            asyncio.run(client.assess_text("fixture", {"semantic_choice.v1": QUESTION}))
        self.assertEqual(seen[0].full_url, "https://decision.example.invalid/api/judge")
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer " + CUSTOM_KEY)
        self.assertEqual(json.loads(seen[0].data)["model"], "custom-model")
        from teamknitt.engine.providers.http import _NoRedirect
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_http_failures_do_not_retry_or_expose_the_error_body(self):
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                raise urllib.error.HTTPError(request.full_url, 401, "Denied", {},
                                               io.BytesIO(DECISION_KEY.encode()))
        with patch("teamknitt.engine.providers.http.urllib.request.build_opener", return_value=Opener()):
            client = decision_client(DECISION_KEY)
            with self.assertRaises(ProviderError) as error:
                asyncio.run(client.assess_text("fixture", {"q": QUESTION}))
        self.assertEqual(len(calls), 1)
        self.assertEqual(error.exception.kind, "authentication")
        self.assertNotIn(DECISION_KEY, str(error.exception))


class RoutingTests(unittest.TestCase):
    setUp = fixtures.StudyTests.setUp
    tearDown = fixtures.StudyTests.tearDown

    def config(self, specialist="specialist", mode="selected_active"):
        config = load_study(self.root)
        config["base_overrides"]["decisions"] = {"mode": mode, "specialist": specialist,
                                                "allowed_specs": ["semantic_choice.v1"]}
        return config

    def make_study(self, config):
        plan = plans(fixtures.PROJECT, config)["a-none"]
        return TextStudy(fixtures.PROJECT, self.root, config, plan, "a-none", fixtures.FAKE_KEY)

    def exercise_episode(self, child=False, custom=False):
        config = self.config("other" if custom else "specialist")
        if custom:
            config["decision_providers"] = {"other": {**DECISION_FIXTURE,
                "base_url": "https://decision.example.invalid/v1", "model": "other-v1",
                "api_key_env": "OTHER_DECISION_KEY", "endpoint": "/judge"}}
        calls, count = [], 0
        final = {"action": "final", "summary": "fixture", "findings": [], "wisdom": [], "candidate_output": "unverified"}
        def specialist(client, method, path, body):
            calls.append((client.provider_id, path, body["model"]))
            self.assertNotIn(DECISION_KEY, json.dumps(body))
            self.assertNotIn(fixtures.FAKE_KEY, json.dumps(body))
            return answer("resolved-other" if custom else "resolved-specialist")
        def chat(method, path, body):
            nonlocal count
            count += 1
            calls.append(("generation", path, body["model"]))
            self.assertNotIn(DECISION_KEY, json.dumps(body))
            if child and count == 1:
                action = {"action": "delegate", "task": "Use the bounded decision tool, then summarize."}
            elif count == (2 if child else 1):
                action = {"action": "decision.assess", "spec_id": "semantic_choice.v1", "question": QUESTION}
            else:
                if count == (3 if child else 2):
                    self.assertIn("decision/other" if custom else "decision/specialist", json.dumps(body))
                    self.assertIn("resolved-other" if custom else "resolved-specialist", json.dumps(body))
                action = final
            return {"choices": [{"message": {"content": json.dumps(action)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY, "OTHER_DECISION_KEY": CUSTOM_KEY}), \
                patch.object(TypedDecisionClient, "_http", specialist):
            study = self.make_study(config)
            study.client._transport = chat
            actor = study.plan["personas"][0]["instance_id"]
            output = asyncio.run(study.episode(actor, actor, study.roles[actor], "visible fixture"))
        self.assertIn("output", output)
        specialist_calls = [row for row in calls if row[0] != "generation"]
        self.assertEqual(specialist_calls, [("decision/other", "/judge", "other-v1")] if custom else [
            ("decision/specialist", "/assess", "fixture-decision")])
        self.assertEqual(study.calls, len(calls))
        self.assertEqual(study.usage["decision_input_tokens"], 8)
        self.assertEqual(study.usage["decision_output_tokens"], 2)
        events = (study.root / "events.jsonl").read_text()
        self.assertNotIn(DECISION_KEY, events)
        self.assertNotIn(CUSTOM_KEY, events)
        return study

    def test_prime_calls_specialist_and_resumes_the_same_generation_model(self):
        self.exercise_episode()

    def test_delegated_agent_inherits_the_specialist_backend_and_budget(self):
        self.exercise_episode(child=True)

    def test_a_configured_compatible_model_routes_to_its_endpoint(self):
        self.exercise_episode(custom=True)

    def test_selected_credentials_are_redacted_before_requests_and_saved_publications(self):
        config = self.config()
        (self.root / "mission/problem.md").write_text("Fixture accidentally includes " + DECISION_KEY + fixtures.FAKE_KEY)
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY}):
            study = self.make_study(config)
        seen = []
        final = {"action": "final", "summary": DECISION_KEY, "findings": [], "wisdom": [],
                 "candidate_output": fixtures.FAKE_KEY}
        def transport(method, path, body):
            seen.append(body)
            return {"choices": [{"message": {"content": json.dumps(final)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
        study.client._transport = transport
        actor = study.plan["personas"][0]["instance_id"]
        output = asyncio.run(study.episode(actor, actor, study.roles[actor], "fixture"))
        study.plan["communication"].update(research_exchange=True, detail="high", wisdom=False)
        study.outputs = [output]
        study.peer_view("recipient", "different-team")
        for key in (DECISION_KEY, fixtures.FAKE_KEY):
            self.assertNotIn(key, json.dumps(seen))
            for path in study.root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(key, path.read_text())

    def test_shadow_specialist_is_not_supplied_to_the_acting_context(self):
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY}):
            study = self.make_study(self.config(mode="shadow"))
        study.client._transport = lambda *args: {
            "choices": [{"message": {"content": '{"noul":0.1}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
        study.specialist_client._transport = lambda *args: answer(probability=.93)
        result = asyncio.run(study.decision("a", "a", "e", {"spec_id": "semantic_choice.v1", "question": QUESTION},
                                           [{"role": "user", "content": "visible"}]))
        self.assertEqual(result["answer"]["noul"], .1)
        self.assertNotIn(".93", json.dumps(result))
        self.assertIn('"visible_to_agent": false', (study.root / "events.jsonl").read_text())

    def test_missing_specialist_key_is_explicit_and_fallback_is_budgeted(self):
        with patch.dict(os.environ, {}, clear=True):
            study = self.make_study(self.config())
        self.assertIsNone(study.specialist_client)
        study.client._transport = lambda *args: {
            "choices": [{"message": {"content": '{"noul":0.2}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
        result = asyncio.run(study.decision("a", "a", "e", {"spec_id": "semantic_choice.v1", "question": QUESTION}, []))
        self.assertEqual(result["backend"], "same_llm_fallback")
        self.assertEqual(result["specialist_status"], "unavailable")
        self.assertEqual(study.calls, 1)
        self.assertIn("missing_key", (study.root / "events.jsonl").read_text())

    def test_uncertain_specialist_transport_is_counted_and_falls_back_once(self):
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY}):
            study = self.make_study(self.config())
        attempts = []
        def failed(method, path, body):
            attempts.append(path)
            raise ProviderError("transport_uncertain", "No automatic retry")
        study.specialist_client._transport = failed
        study.client._transport = lambda *args: {
            "choices": [{"message": {"content": '{"noul":0.2}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
        result = asyncio.run(study.decision("a", "a", "e",
            {"spec_id": "semantic_choice.v1", "question": QUESTION}, []))
        self.assertEqual(result["backend"], "same_llm_fallback")
        self.assertEqual(attempts, ["/assess"])
        self.assertEqual(study.calls, 2)
        self.assertEqual(study.decision_usage["decision/specialist"]["requests"], 1)
        self.assertEqual(study.usage["missing_usage_receipts"], 1)
        self.assertIn("decision_fallback", (study.root / "events.jsonl").read_text())

    def test_shared_request_limit_covers_generation_and_specialist(self):
        config = self.config()
        config["base_overrides"]["resources"] = {"max_llm_requests": 1}
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY}):
            study = self.make_study(config)
        active = maximum = 0
        lock = threading.Lock()
        def transport(method, path, body):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.03)
            with lock:
                active -= 1
            if path == "/assess": return answer()
            return {"choices": [{"message": {"content": "fixture"}, "finish_reason": "stop"}], "usage": {}}
        study.client._transport = study.specialist_client._transport = transport
        async def work():
            await asyncio.gather(
                study.client.generate([{"role": "user", "content": "fixture"}], budget_ref="test"),
                study.specialist_client.assess_text("fixture", {"semantic_choice.v1": QUESTION}))
        asyncio.run(work())
        self.assertEqual(maximum, 1)
        self.assertEqual(study.calls, 2)

    def test_budget_exhaustion_does_not_dispatch_a_specialist_or_an_extra_fallback(self):
        config = self.config()
        config["base_overrides"]["budget"] = {"max_llm_calls": 1}
        with patch.dict(os.environ, {"TEAMKNITT_DECISION_API_KEY": DECISION_KEY}):
            study = self.make_study(config)
        study.calls = 1
        study.specialist_client._transport = lambda *args: self.fail("No specialist request remains")
        study.client._transport = lambda *args: self.fail("No fallback request remains")
        with self.assertRaises(StudyError):
            asyncio.run(study.decision("a", "a", "e", {"spec_id": "semantic_choice.v1", "question": QUESTION}, []))
        self.assertEqual(study.calls, 1)

    def test_public_binding_changes_when_the_decision_model_changes(self):
        a = self.config()
        a["decision_providers"] = {"specialist": dict(DECISION_FIXTURE)}
        b = deepcopy(a)
        b["decision_providers"]["specialist"]["model"] = "other-decision-version"
        pa, pb = plans(fixtures.PROJECT, a)["a-none"], plans(fixtures.PROJECT, b)["a-none"]
        self.assertNotEqual(pa["configuration_snapshot"]["id"], pb["configuration_snapshot"]["id"])
        self.assertNotIn(DECISION_KEY, json.dumps(pa))

    def test_unknown_providers_and_raw_key_fields_are_rejected_before_a_request(self):
        config = self.config("unknown")
        with self.assertRaises(ConfigurationError):
            plans(fixtures.PROJECT, config)
        config = self.config()
        config["decision_providers"] = {"specialist": {**DECISION_FIXTURE, "api_key": DECISION_KEY}}
        (self.root / "study.yaml").write_text(json.dumps(config))
        with self.assertRaises(ConfigurationError):
            prepare(fixtures.PROJECT, self.root)

    def test_doctor_llm_only_does_not_read_or_probe_a_specialist(self):
        config = self.config(mode="llm_only")
        (self.root / "study.yaml").write_text(json.dumps(config))
        paths = []
        def chat(client, method, path, body):
            paths.append(path)
            if path == "/models": return {"data": [{"id": "fixture-chat"}]}
            return {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}], "usage": {}}
        with patch.dict(os.environ, {"TEAMKNITT_API_KEY": fixtures.FAKE_KEY}), \
                patch.object(TypedDecisionClient, "_http", side_effect=AssertionError("No specialist probe")), \
                patch("teamknitt.engine.study.ChatCompletionsClient._http", chat):
            result = asyncio.run(doctor(fixtures.PROJECT, self.root, live=True))
        self.assertEqual(result["status"], "connected")
        self.assertEqual(paths, ["/models", "/chat/completions"])
        self.assertEqual(result["decision_providers"], {})

    def test_live_doctor_uses_the_selected_specialist_account_and_resolved_version(self):
        config = self.config()
        (self.root / "study.yaml").write_text(json.dumps(config))
        calls = []
        def chat(client, method, path, body):
            calls.append(("generation", path))
            if path == "/models": return {"data": [{"id": "fixture-chat"}]}
            return {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}], "usage": {}}
        def typed(client, method, path, body):
            calls.append((client.provider_id, path))
            self.assertEqual(client._key, DECISION_KEY)
            return {"model": "resolved-decision-test", "answers": {"connection": {"noul": .9}},
                    "usage": {"input_tokens": 3, "output_tokens": 1}}
        with patch.dict(os.environ, {"TEAMKNITT_API_KEY": fixtures.FAKE_KEY, "TEAMKNITT_DECISION_API_KEY": DECISION_KEY}), \
                patch("teamknitt.engine.study.ChatCompletionsClient._http", chat), patch.object(TypedDecisionClient, "_http", typed):
            result = asyncio.run(doctor(fixtures.PROJECT, self.root, live=True, variant="a-none"))
        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["decision_providers"]["decision/specialist"]["model"], "resolved-decision-test")
        self.assertEqual(calls, [("generation", "/models"), ("generation", "/chat/completions"), ("decision/specialist", "/assess")])
        self.assertNotIn(DECISION_KEY, (self.root / "setup/connection.json").read_text())


if __name__ == "__main__":
    unittest.main()
