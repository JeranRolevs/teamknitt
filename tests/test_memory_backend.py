"""Routing and experiment-scope regression checks; offline."""
import asyncio
from pathlib import Path
import json
import unittest
import test_providers as fixtures
from teamknitt.engine.memory import MemoryResearchBackend,ACTION_CONTRACT
from teamknitt.engine.planning import compile_plan
from teamknitt.engine.study import TextStudy,compare,load_study


class MemoryBridgeTests(unittest.TestCase):
    def test_visible_feedback_excludes_private_splits_and_run_id_panels(self):
        data={"status":"valid","metrics":{"fault_recall":.5},"results":[],
              "private_seed_file":"private","run_ids":{"confirmation":["hidden"]}}
        view=MemoryResearchBackend.visible_result(data)
        self.assertNotIn("private_seed_file",view)
        self.assertNotIn("run_ids",view)
        self.assertEqual(view["metrics"]["fault_recall"],.5)

    def test_authoring_contract_exposes_source_not_a_window_preset(self):
        self.assertIn("select(bank, ages, new, t, capacity, aux)",ACTION_CONTRACT)
        self.assertIn('"source"',ACTION_CONTRACT)
        self.assertNotIn("damp_raw",ACTION_CONTRACT)


class ComparisonScopeTests(unittest.TestCase):
    setUp=fixtures.StudyTests.setUp
    tearDown=fixtures.StudyTests.tearDown
    def test_different_missions_are_not_compared_as_one_task(self):
        config=load_study(self.root)
        plan=compile_plan(fixtures.PROJECT,config_overrides=config["base_overrides"])
        TextStudy(fixtures.PROJECT,self.root,config,plan,"one",fixtures.FAKE_KEY)
        other=dict(config,name="different-research-task")
        TextStudy(fixtures.PROJECT,self.root,other,plan,"two",fixtures.FAKE_KEY)
        self.assertEqual(compare(self.root)["trials"],1)
