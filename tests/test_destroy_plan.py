import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_destroy_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_destroy_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DestroyPlanTests(unittest.TestCase):
    def setUp(self):
        self.expected = [
            "aws_security_group.shared_ssh",
            'aws_vpc_security_group_ingress_rule.shared_ssh["ssh_ipv4"]',
            'aws_vpc_security_group_egress_rule.shared_ssh["all_ipv4"]',
        ]
        self.plan = {
            "complete": True,
            "resource_changes": [
                {
                    "mode": "managed",
                    "address": address,
                    "change": {"actions": ["delete"]},
                }
                for address in self.expected
            ]
            + [
                {
                    "mode": "managed",
                    "address": "aws_instance.monitoring",
                    "change": {"actions": ["no-op"]},
                }
            ],
        }

    def test_exact_destroy_set(self):
        module.verify(self.plan, self.expected)

    def test_missing_or_extra_mutation_rejected(self):
        for resources in [
            self.plan["resource_changes"][:-2],
            self.plan["resource_changes"]
            + [
                {
                    "mode": "managed",
                    "address": "aws_instance.other",
                    "change": {"actions": ["update"]},
                }
            ],
        ]:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"] = resources
            with self.assertRaises(ValueError):
                module.verify(plan, self.expected)

    def test_update_replacement_and_import_rejected(self):
        cases = [
            (["update"], None),
            (["delete", "create"], None),
            (["delete"], {"id": "existing"}),
        ]
        for actions, importing in cases:
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][0]["change"]["actions"] = actions
            if importing is not None:
                plan["resource_changes"][0]["change"]["importing"] = importing
            with self.subTest(actions=actions, importing=importing), self.assertRaises(ValueError):
                module.verify(plan, self.expected)

    def test_incomplete_or_deferred_plan_rejected(self):
        for key, value in [("complete", False), ("errored", True), ("deferred_changes", [{}])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.verify(plan, self.expected)

    def test_expected_addresses_must_be_unique_and_nonempty(self):
        for expected in [[], [self.expected[0], self.expected[0]]]:
            with self.assertRaises(ValueError):
                module.verify(self.plan, expected)
