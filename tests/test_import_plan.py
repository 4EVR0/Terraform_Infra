import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("check_import_plan", Path(__file__).resolve().parents[1] / "scripts/check_import_plan.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportPlanTests(unittest.TestCase):
    def setUp(self):
        self.target = "aws_instance.monitoring"
        self.plan = {"complete": True, "resource_changes": [{
            "mode": "managed", "address": self.target,
            "change": {"actions": ["no-op"], "importing": {"id": "example-instance"}},
        }]}

    def test_expected_import(self):
        module.verify(self.plan, self.target, "example-instance")

    def test_mutations_rejected(self):
        for action in (["create"], ["update"], ["delete"], ["delete", "create"]):
            with self.subTest(action=action):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][0]["change"]["actions"] = action
                with self.assertRaises(ValueError):
                    module.verify(plan, self.target, "example-instance")

    def test_wrong_target_or_id_rejected(self):
        for target, identifier in [("aws_instance.other", "example-instance"), (self.target, "other-instance")]:
            with self.subTest(target=target, identifier=identifier), self.assertRaises(ValueError):
                module.verify(self.plan, target, identifier)

    def test_additional_change_rejected(self):
        self.plan["resource_changes"].append({"mode": "managed", "address": "aws_s3_bucket.other", "change": {"actions": ["delete"]}})
        with self.assertRaises(ValueError):
            module.verify(self.plan, self.target, "example-instance")

    def test_incomplete_and_multiple_imports_rejected(self):
        for key, value in [("complete", False), ("errored", True), ("deferred_changes", [{}])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.verify(plan, self.target, "example-instance")
        self.plan["resource_changes"] *= 2
        with self.assertRaises(ValueError):
            module.verify(self.plan, self.target, "example-instance")
