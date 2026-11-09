"""Generic connection boundaries and an independently configured chat judge, offline."""
import asyncio
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from teamknitt.engine.cli import main
from teamknitt.engine.scaffold import init_workspace
from teamknitt.engine.providers.chat import ChatCompletionsClient
from teamknitt.engine.providers.http import ProviderError
from teamknitt.engine.study import TextStudy, doctor, plans, load_study, compare
import test_providers as fixtures


class GenericConnectionTests(unittest.TestCase):
    setUp = fixtures.StudyTests.setUp
    tearDown = fixtures.StudyTests.tearDown

    def test_comparison_tolerates_extra_metrics_in_existing_private_trial_receipts(self):
        trial = self.root / "trials/older-fixture"
        trial.mkdir(parents=True)
        (trial / "summary.json").write_text(json.dumps({
            "trial_id": "older-fixture", "variant": "a-none", "status": "completed_text_workflow",
            "usage": {"chat_input_tokens": 3, "decision_input_tokens": 8, "unused_backend_detail": 8}}))
        result = compare(self.root)
        self.assertEqual(result["trials"], 1)
        data = json.loads((self.root / "comparisons/summary.json").read_text())["trials"][0]
        self.assertEqual(data["decision_input_tokens"], 8)
        self.assertNotIn("unused_backend_detail", data)

    def test_generation_endpoint_and_options_enter_the_configuration_identity(self):
        a = load_study(self.root)
        b = deepcopy(a)
        b["provider"]["base_url"] = "https://different.example.test/api"
        b["provider"]["endpoint"] = "/generate"
        pa, pb = plans(fixtures.PROJECT, a)["a-none"], plans(fixtures.PROJECT, b)["a-none"]
        self.assertNotEqual(pa["configuration_snapshot"]["id"], pb["configuration_snapshot"]["id"])
        self.assertEqual(pb["generation_provider"]["endpoint"], "/generate")

    def test_model_listing_is_not_assumed_for_a_compatible_endpoint(self):
        config = fixtures.fixture_config()
        config["provider"]["models_endpoint"] = None
        (self.root / "study.yaml").write_text(json.dumps(config))
        calls = []
        def transport(client, method, path, body):
            calls.append((method, path))
            return {"choices": [{"message": {"content": "OK"}}], "usage": {}}
        with patch.dict("os.environ", {"TEAMKNITT_API_KEY": fixtures.FAKE_KEY}), patch.object(ChatCompletionsClient, "_http", transport):
            result = asyncio.run(doctor(fixtures.PROJECT, self.root, live=True))
        self.assertEqual(result["status"], "connected")
        self.assertEqual(calls, [("POST", "/chat/completions")])

    def test_explicit_unauthenticated_loopback_sends_no_bearer_header(self):
        seen = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, count): return b'{"choices":[{"message":{"content":"OK"}}]}'
        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                return Response()
        client = ChatCompletionsClient(None, model="local-model", base_url="http://127.0.0.1:8000/v1")
        with patch("teamknitt.engine.providers.http.urllib.request.build_opener", return_value=Opener()):
            asyncio.run(client.generate([], budget_ref="fixture"))
        self.assertIsNone(seen[0].get_header("Authorization"))

    def test_starter_placeholders_block_run_before_credentials_or_trial_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "lab"
            init_workspace(workspace)
            (workspace / "mission/problem.md").write_text("Offline fixture mission.")
            with patch("teamknitt.engine.study.api_key", side_effect=AssertionError("No credential read")), \
                    patch("teamknitt.engine.providers.http.JSONClient._http", side_effect=AssertionError("No provider call")), \
                    redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["--project", str(workspace), "study", "run", "--workspace", str(workspace), "--variant", "single"]), 2)
            self.assertFalse((workspace / "trials").exists())

    def test_chat_specialist_uses_separate_key_and_resumes_generation(self):
        config = fixtures.fixture_config()
        config["provider"]["models_endpoint"] = None
        config["base_overrides"]["decisions"].update(mode="selected_active", specialist="judge")
        config["decision_providers"] = {"judge": {**fixtures.DECISION_FIXTURE, "adapter": "chat_completions", "endpoint": "/judge"}}
        plan = plans(fixtures.PROJECT, config)["a-none"]
        with patch("teamknitt.engine.study.api_key", return_value="offline-separate-key"):
            study = TextStudy(fixtures.PROJECT, self.root, config, plan, "a-none", fixtures.FAKE_KEY)
        self.assertNotEqual(study.client._key, study.specialist_client._key)
        calls = []
        def generation(method, path, body):
            calls.append((path, body["model"]))
            if len(calls) == 1:
                value = {"action": "decision.assess", "spec_id": "semantic_choice.v1", "question": {"type": "noul", "instructions": "Supported?"}}
            else:
                self.assertIn("decision/judge", json.dumps(body))
                value = {"action": "final", "summary": "fixture", "findings": [], "wisdom": [], "candidate_output": "unverified"}
            return {"choices": [{"message": {"content": json.dumps(value)}}], "usage": {"prompt_tokens": 2, "completion_tokens": 1}}
        def judge(method, path, body):
            calls.append((path, body["model"]))
            return {"model": "resolved-judge", "choices": [{"message": {"content": '{"answers":{"semantic_choice.v1":{"noul":0.8}}}'}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 2}}
        study.client._transport, study.specialist_client._transport = generation, judge
        actor = plan["personas"][0]["instance_id"]
        result = asyncio.run(study.episode(actor, actor, study.roles[actor], "fixture"))
        self.assertIn("output", result)
        self.assertEqual([path for path, model in calls], ["/chat/completions", "/judge", "/chat/completions"])
        self.assertEqual(study.calls, 3)
        self.assertEqual(study.usage["decision_input_tokens"], 7)
        self.assertEqual(study.decision_usage["decision/judge"]["requests"], 1)


if __name__ == "__main__":
    unittest.main()
