import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_ingress_cleanup_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_ingress_cleanup_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rule(address, actions):
    return {"mode": "managed", "address": address, "change": {"actions": actions}}


class IngressCleanupPlanTests(unittest.TestCase):
    def setUp(self):
        self.rule = 'aws_vpc_security_group_ingress_rule.monitoring["public_web"]'
        self.target = "aws_instance.airflow"
        self.removed = "team-test"
        self.required = "airflow-service"
        self.plan = {
            "complete": True,
            "resource_changes": [
                rule(self.rule, ["delete"]),
                {
                    "mode": "managed",
                    "address": self.target,
                    "change": {
                        "actions": ["update"],
                        "before": {"instance_type": "t4g.large", "vpc_security_group_ids": [self.required, self.removed]},
                        "after": {"instance_type": "t4g.large", "vpc_security_group_ids": [self.required]},
                        "after_unknown": {},
                    },
                },
                rule('aws_vpc_security_group_ingress_rule.monitoring["kept"]', ["no-op"]),
            ],
        }
        self.detach = [(self.target, self.removed, self.required)]

    def verify(self, plan=None, rules=None, detaches=None):
        module.verify(plan or self.plan, [self.rule] if rules is None else rules,
                      self.detach if detaches is None else detaches)

    def test_accepts_reviewed_deletes_and_detach(self):
        self.verify()

    def test_accepts_rule_deletes_only(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].pop(1)
        self.verify(plan, detaches=[])

    def test_rejects_unreviewed_rule_delete(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].append(rule('aws_vpc_security_group_ingress_rule.monitoring["other"]', ["delete"]))
        with self.assertRaisesRegex(ValueError, "Unexpected managed mutation"):
            self.verify(plan)

    def test_rejects_rule_replacement(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][0]["change"]["actions"] = ["delete", "create"]
        with self.assertRaisesRegex(ValueError, "without replacement"):
            self.verify(plan)

    def test_rejects_missing_reviewed_change(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].pop(0)
        with self.assertRaisesRegex(ValueError, "missing"):
            self.verify(plan)

    def test_rejects_instance_attribute_change_beyond_groups(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][1]["change"]["after"]["instance_type"] = "t4g.xlarge"
        with self.assertRaisesRegex(ValueError, "other than security groups"):
            self.verify(plan)

    def test_rejects_instance_replacement(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][1]["change"]["actions"] = ["delete", "create"]
        with self.assertRaisesRegex(ValueError, "in-place update"):
            self.verify(plan)

    def test_rejects_dropping_required_group(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][1]["change"]["after"]["vpc_security_group_ids"] = []
        with self.assertRaisesRegex(ValueError, "required service group"):
            self.verify(plan)

    def test_rejects_unknown_groups(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][1]["change"]["after_unknown"] = {"vpc_security_group_ids": True}
        with self.assertRaisesRegex(ValueError, "not fully known"):
            self.verify(plan)

    def test_rejects_other_resource_mutation(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].append(rule("aws_security_group.monitoring", ["delete"]))
        with self.assertRaisesRegex(ValueError, "Unexpected managed mutation"):
            self.verify(plan)

    def test_rejects_non_rule_delete_address(self):
        with self.assertRaisesRegex(ValueError, "Only ingress rule addresses"):
            self.verify(rules=["aws_security_group.monitoring"])

    def test_rejects_import_and_incomplete_plan(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][0]["change"]["importing"] = {"id": "x"}
        with self.assertRaisesRegex(ValueError, "import"):
            self.verify(plan)
        with self.assertRaisesRegex(ValueError, "errored"):
            self.verify({"complete": False, "resource_changes": []})


if __name__ == "__main__":
    unittest.main()
