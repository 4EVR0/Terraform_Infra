import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_security_group_detach_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_security_group_detach_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SecurityGroupDetachPlanTests(unittest.TestCase):
    def setUp(self):
        self.target = "aws_instance.graphdb"
        self.removed = "shared-ssh"
        self.required = "graphdb-service"
        self.plan = {
            "complete": True,
            "resource_changes": [
                {
                    "mode": "managed",
                    "address": self.target,
                    "change": {
                        "actions": ["update"],
                        "before": {"vpc_security_group_ids": [self.required, self.removed]},
                        "after": {"vpc_security_group_ids": [self.required]},
                        "after_unknown": {},
                    },
                },
                {
                    "mode": "managed",
                    "address": "aws_security_group.shared_ssh",
                    "change": {"actions": ["no-op"]},
                },
            ],
        }

    def test_exact_detach(self):
        module.verify(self.plan, self.target, self.removed, self.required)

    def test_extra_mutation_rejected(self):
        self.plan["resource_changes"][1]["change"]["actions"] = ["update"]
        with self.assertRaises(ValueError):
            module.verify(self.plan, self.target, self.removed, self.required)

    def test_wrong_membership_rejected(self):
        cases = [
            [self.required, self.removed],
            [],
            [self.required, "unexpected"],
        ]
        for after in cases:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][0]["change"]["after"]["vpc_security_group_ids"] = after
            with self.subTest(after=after), self.assertRaises(ValueError):
                module.verify(plan, self.target, self.removed, self.required)

    def test_incomplete_or_unknown_plan_rejected(self):
        for key, value in [("complete", False), ("errored", True), ("deferred_changes", [{}])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.verify(plan, self.target, self.removed, self.required)
        self.plan["resource_changes"][0]["change"]["after_unknown"] = {"vpc_security_group_ids": True}
        with self.assertRaises(ValueError):
            module.verify(self.plan, self.target, self.removed, self.required)

    def test_import_or_replacement_rejected(self):
        for change in [
            {"actions": ["update"], "importing": {"id": "example"}},
            {"actions": ["delete", "create"]},
        ]:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][0]["change"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.verify(plan, self.target, self.removed, self.required)
