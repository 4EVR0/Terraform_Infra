import copy
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_bootstrap_admin_role_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_bootstrap_admin_role_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def document(statements):
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


class BootstrapAdminRolePlanTests(unittest.TestCase):
    def setUp(self):
        account = "000000000000"
        bucket = "arn:aws:s3:::example-state"
        role_arns = [
            f"arn:aws:iam::{account}:role/4EVR0TerraformPlanRole",
            f"arn:aws:iam::{account}:role/4EVR0TerraformApplyRole",
            f"arn:aws:iam::{account}:role/4EVR0TerraformBootstrapAdminRole",
        ]
        guardrails = [
            {
                "Sid": "DenyStateDeletion",
                "Effect": "Deny",
                "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
                "Resource": [
                    f"{bucket}/4evr0/bootstrap/terraform.tfstate",
                    f"{bucket}/4evr0/project/terraform.tfstate",
                ],
            },
            {"Sid": "DenyStateBucketDeletion", "Effect": "Deny", "Action": "s3:DeleteBucket", "Resource": bucket},
            {"Sid": "DenyTerraformRoleDeletion", "Effect": "Deny", "Action": "iam:DeleteRole", "Resource": role_arns},
            {
                "Sid": "DenyOperatorDeletion",
                "Effect": "Deny",
                "Action": "iam:DeleteUser",
                "Resource": f"arn:aws:iam::{account}:user/example",
            },
        ]
        self.plan = {
            "complete": True,
            "resource_changes": [
                {"mode": "managed", "address": address, "change": {"actions": actions}}
                for address, actions in module.EXPECTED_MUTATIONS.items()
            ],
            "planned_values": {"root_module": {"resources": [
                {
                    "address": "aws_iam_role.terraform_bootstrap_admin",
                    "values": {
                        "max_session_duration": 3600,
                        "assume_role_policy": document([{
                            "Sid": "AllowOperatorWithMFA",
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {"AWS": f"arn:aws:iam::{account}:user/example"},
                            "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                        }]),
                    },
                },
                {
                    "address": "aws_iam_role_policy_attachment.terraform_bootstrap_admin",
                    "values": {"policy_arn": "arn:aws:iam::aws:policy/AdministratorAccess"},
                },
                {
                    "address": "aws_iam_role_policy.terraform_bootstrap_admin_guardrail",
                    "values": {"policy": document(guardrails)},
                },
                {
                    "address": "aws_iam_user_policy.terraform_bootstrap_admin_assume",
                    "values": {"policy": document([{
                        "Sid": "AssumeTerraformBootstrapAdminRole",
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Resource": role_arns[-1],
                    }])},
                },
            ]}},
        }

    def test_reviewed_plan_passes(self):
        module.verify(self.plan)

    def test_extra_mutation_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].append({"mode": "managed", "address": "aws_iam_user.other", "change": {"actions": ["create"]}})
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_missing_mfa_rejected(self):
        plan = copy.deepcopy(self.plan)
        role = plan["planned_values"]["root_module"]["resources"][0]["values"]
        trust = json.loads(role["assume_role_policy"])
        del trust["Statement"][0]["Condition"]
        role["assume_role_policy"] = document(trust["Statement"])
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_wrong_attached_policy_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["planned_values"]["root_module"]["resources"][1]["values"]["policy_arn"] = "arn:aws:iam::aws:policy/PowerUserAccess"
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_state_version_delete_must_be_denied(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][2]["values"]
        policy = json.loads(values["policy"])
        deny = next(statement for statement in policy["Statement"] if statement["Sid"] == "DenyStateDeletion")
        deny["Action"].remove("s3:DeleteObjectVersion")
        values["policy"] = document(policy["Statement"])
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unscoped_guardrail_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][2]["values"]
        policy = json.loads(values["policy"])
        next(statement for statement in policy["Statement"] if statement["Sid"] == "DenyOperatorDeletion")["Resource"] = "*"
        values["policy"] = document(policy["Statement"])
        with self.assertRaises(ValueError):
            module.verify(plan)


if __name__ == "__main__":
    unittest.main()
