import copy
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_team_admin_role_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_team_admin_role_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def document(statements):
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


class TeamAdminRolePlanTests(unittest.TestCase):
    def setUp(self):
        account = "000000000000"
        users = ["example-a", "example-b"]
        role_arns = [
            f"arn:aws:iam::{account}:role/4EVR0TerraformPlanRole",
            f"arn:aws:iam::{account}:role/4EVR0TerraformApplyRole",
            f"arn:aws:iam::{account}:role/4EVR0TerraformBootstrapAdminRole",
            f"arn:aws:iam::{account}:role/4EVR0TeamAdminRole",
        ]
        guardrails = [
            {
                "Sid": sid,
                "Effect": "Deny",
                "Action": sorted(actions),
                "Resource": "arn:aws:example:::protected",
            }
            for sid, actions in module.EXPECTED_GUARDRAIL_ACTIONS.items()
        ]
        next(x for x in guardrails if x["Sid"] == "DenyStateDeletion")["Resource"] = [
            "arn:aws:s3:::example-state/4evr0/bootstrap/terraform.tfstate",
            "arn:aws:s3:::example-state/4evr0/project/terraform.tfstate",
        ]
        next(x for x in guardrails if x["Sid"] == "DenyStateBucketDeletion")["Resource"] = "arn:aws:s3:::example-state"
        next(x for x in guardrails if x["Sid"] == "DenyTerraformRoleMutation")["Resource"] = role_arns
        next(x for x in guardrails if x["Sid"] == "DenyTerraformOperatorMutation")["Resource"] = f"arn:aws:iam::{account}:user/operator"
        base = [
            {"Sid": "ReadOwnIdentitySettings", "Effect": "Allow", "Action": ["iam:GetAccountPasswordPolicy"], "Resource": "*"},
            {
                "Sid": "ManageOwnPasswordAndMFA",
                "Effect": "Allow",
                "Action": ["iam:ChangePassword"],
                "Resource": f"arn:aws:iam::{account}:user/${{aws:username}}",
            },
            {
                "Sid": "ManageOwnVirtualMFADevice",
                "Effect": "Allow",
                "Action": ["iam:CreateVirtualMFADevice"],
                "Resource": f"arn:aws:iam::{account}:mfa/${{aws:username}}",
            },
            {"Sid": "ListVirtualMFADevices", "Effect": "Allow", "Action": "iam:ListVirtualMFADevices", "Resource": "*"},
            {"Sid": "AssumeTeamAdminRole", "Effect": "Allow", "Action": "sts:AssumeRole", "Resource": role_arns[-1]},
        ]
        self.plan = {
            "complete": True,
            "resource_changes": [
                {"mode": "managed", "address": address, "change": {"actions": actions}}
                for address, actions in module.EXPECTED_MUTATIONS.items()
            ],
            "planned_values": {"root_module": {"resources": [
                {
                    "address": "aws_iam_role.team_admin",
                    "values": {
                        "max_session_duration": 7200,
                        "assume_role_policy": document([{
                            "Sid": "AllowNamedTeamUsersWithMFA",
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {"AWS": [f"arn:aws:iam::{account}:user/{user}" for user in users]},
                            "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                        }]),
                    },
                },
                {"address": "aws_iam_role_policy_attachment.team_admin", "values": {"policy_arn": "arn:aws:iam::aws:policy/AdministratorAccess"}},
                {"address": "aws_iam_role_policy.team_admin_guardrail", "values": {"policy": document(guardrails)}},
                {"address": "aws_iam_group.team_users", "values": {"name": "4EVR0TeamUsers"}},
                {"address": "aws_iam_group_policy.team_users", "values": {"policy": document(base)}},
                {"address": "aws_iam_group_membership.team_users", "values": {"group": "4EVR0TeamUsers", "users": users}},
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

    def test_group_member_not_in_trust_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["planned_values"]["root_module"]["resources"][5]["values"]["users"].append("example-c")
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unscoped_self_management_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][4]["values"]
        policy = json.loads(values["policy"])
        next(x for x in policy["Statement"] if x["Sid"] == "ManageOwnPasswordAndMFA")["Resource"] = "*"
        values["policy"] = document(policy["Statement"])
        with self.assertRaises(ValueError):
            module.verify(plan)


if __name__ == "__main__":
    unittest.main()
