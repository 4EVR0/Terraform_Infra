import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_iam_attachment_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_iam_attachment_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IamAttachmentPlanTests(unittest.TestCase):
    def setUp(self):
        self.target = "aws_iam_role_policy_attachment.monitoring_ssm"
        self.role = "monitoring-role"
        self.policy = "arn:aws:iam::aws:policy/example"
        self.plan = {
            "complete": True,
            "resource_changes": [
                {
                    "mode": "managed",
                    "address": self.target,
                    "change": {"actions": ["create"]},
                },
                {
                    "mode": "managed",
                    "address": "aws_iam_role.monitoring",
                    "change": {"actions": ["no-op"]},
                },
            ],
            "planned_values": {
                "root_module": {
                    "resources": [
                        {
                            "address": self.target,
                            "values": {"role": self.role, "policy_arn": self.policy},
                        }
                    ]
                }
            },
        }

    def test_exact_attachment_create(self):
        module.verify(self.plan, self.target, self.role, self.policy)

    def test_extra_mutation_rejected(self):
        self.plan["resource_changes"][1]["change"]["actions"] = ["update"]
        with self.assertRaises(ValueError):
            module.verify(self.plan, self.target, self.role, self.policy)

    def test_wrong_target_action_or_import_rejected(self):
        cases = [
            ("aws_iam_role_policy_attachment.other", ["create"], None),
            (self.target, ["update"], None),
            (self.target, ["create"], {"id": "existing"}),
        ]
        for address, actions, importing in cases:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][0]["address"] = address
            plan["resource_changes"][0]["change"]["actions"] = actions
            if importing is not None:
                plan["resource_changes"][0]["change"]["importing"] = importing
            with self.subTest(address=address, actions=actions), self.assertRaises(ValueError):
                module.verify(plan, self.target, self.role, self.policy)

    def test_wrong_role_or_policy_rejected(self):
        for role, policy in [("other-role", self.policy), (self.role, "other-policy")]:
            with self.subTest(role=role, policy=policy), self.assertRaises(ValueError):
                module.verify(self.plan, self.target, role, policy)

    def test_incomplete_plan_rejected(self):
        for key, value in [("complete", False), ("errored", True), ("deferred_changes", [{}])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.verify(plan, self.target, self.role, self.policy)
