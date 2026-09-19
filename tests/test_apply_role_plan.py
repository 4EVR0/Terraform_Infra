import copy
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_apply_role_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_apply_role_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def document(statements):
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


class ApplyRolePlanTests(unittest.TestCase):
    def setUp(self):
        state = "arn:aws:s3:::example-state/4evr0/project/terraform.tfstate"
        statements = []
        for sid in sorted(module.EXPECTED_SIDS):
            statement = {"Sid": sid, "Effect": "Allow", "Action": "example:Read", "Resource": "arn:aws:example:::reviewed"}
            statements.append(statement)
        by_sid = {statement["Sid"]: statement for statement in statements}
        by_sid["WriteProjectState"].update(Action="s3:PutObject", Resource=state)
        by_sid["ManageProjectStateLock"].update(Action=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource=f"{state}.tflock")
        by_sid["DenyProjectStateDeletion"].update(Effect="Deny", Action="s3:DeleteObject", Resource=[state, "arn:aws:s3:::example-state/4evr0/bootstrap/terraform.tfstate"])
        by_sid["DenyBootstrapStateAccess"].update(Effect="Deny", Action=["s3:GetObject", "s3:PutObject"], Resource="arn:aws:s3:::example-state/4evr0/bootstrap/terraform.tfstate")
        by_sid["DenyResourceReplacementAndDeletion"].update(Effect="Deny", Action=sorted(module.REQUIRED_EXPLICIT_DENIES), Resource="*")
        by_sid["ManageReviewedRolePolicyAttachments"]["Condition"] = {"ArnEquals": {"iam:PolicyARN": "arn:aws:iam::aws:policy/example"}}
        by_sid["PassReviewedRolesToEC2"]["Condition"] = {"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}}

        self.plan = {
            "complete": True,
            "resource_changes": [
                {"mode": "managed", "address": address, "change": {"actions": actions}}
                for address, actions in module.EXPECTED_MUTATIONS.items()
            ],
            "planned_values": {"root_module": {"resources": [
                {
                    "address": "aws_iam_role.terraform_apply",
                    "values": {
                        "max_session_duration": 3600,
                        "assume_role_policy": document([{
                            "Sid": "AllowOperatorWithMFA",
                            "Effect": "Allow",
                            "Action": "sts:AssumeRole",
                            "Principal": {"AWS": "arn:aws:iam::000000000000:user/example"},
                            "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                        }]),
                    },
                },
                {"address": "aws_iam_role_policy.terraform_apply", "values": {"policy": document(statements)}},
                {
                    "address": "aws_iam_user_policy.terraform_apply_assume",
                    "values": {"policy": document([{
                        "Sid": "AssumeTerraformApplyRole",
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Resource": "arn:aws:iam::000000000000:role/4EVR0TerraformApplyRole",
                    }])},
                },
            ]}},
        }

    def test_reviewed_plan_passes(self):
        module.verify(self.plan)

    def test_extra_mutation_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].append({"mode": "managed", "address": "aws_s3_bucket.other", "change": {"actions": ["update"]}})
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_missing_mfa_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][0]["values"]
        trust = json.loads(values["assume_role_policy"])
        del trust["Statement"][0]["Condition"]
        values["assume_role_policy"] = json.dumps(trust)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_state_delete_allow_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        policy = json.loads(values["policy"])
        next(x for x in policy["Statement"] if x["Sid"] == "WriteProjectState")["Action"] = ["s3:PutObject", "s3:DeleteObject"]
        values["policy"] = json.dumps(policy)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unscoped_write_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        policy = json.loads(values["policy"])
        next(x for x in policy["Statement"] if x["Sid"] == "ManageReviewedInstances")["Resource"] = "*"
        values["policy"] = json.dumps(policy)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_missing_explicit_deny_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        policy = json.loads(values["policy"])
        deny = next(x for x in policy["Statement"] if x["Sid"] == "DenyResourceReplacementAndDeletion")
        deny["Action"].remove("ec2:TerminateInstances")
        values["policy"] = json.dumps(policy)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unrestricted_pass_role_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        policy = json.loads(values["policy"])
        del next(x for x in policy["Statement"] if x["Sid"] == "PassReviewedRolesToEC2")["Condition"]
        values["policy"] = json.dumps(policy)
        with self.assertRaises(ValueError):
            module.verify(plan)


if __name__ == "__main__":
    unittest.main()
