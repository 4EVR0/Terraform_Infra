import copy
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "check_plan_role_plan",
    Path(__file__).resolve().parents[1] / "scripts/check_plan_role_plan.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def policy(statements):
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


class PlanRolePlanTests(unittest.TestCase):
    def setUp(self):
        state = "arn:aws:s3:::example-state/4evr0/project/terraform.tfstate"
        role_arn = "arn:aws:iam::000000000000:role/4EVR0TerraformPlanRole"
        role_policy = [
            {
                "Sid": "ListProjectStateBucket",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::example-state",
                "Condition": {"StringEquals": {"s3:prefix": ["4evr0/project/terraform.tfstate", "4evr0/project/terraform.tfstate.tflock"]}},
            },
            {"Sid": "ReadProjectState", "Effect": "Allow", "Action": "s3:GetObject", "Resource": state},
            {
                "Sid": "ManageProjectStateLock",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": f"{state}.tflock",
            },
            {"Sid": "ReadCallerIdentity", "Effect": "Allow", "Action": "sts:GetCallerIdentity", "Resource": "*"},
            {"Sid": "ReadProjectEC2", "Effect": "Allow", "Action": "ec2:Describe*", "Resource": "*"},
            {"Sid": "ReadProjectIAM", "Effect": "Allow", "Action": sorted(module.EXPECTED_IAM_READ_ACTIONS), "Resource": "*"},
            {
                "Sid": "ReadProjectS3Configuration",
                "Effect": "Allow",
                "Action": sorted(module.EXPECTED_S3_CONFIGURATION_ACTIONS),
                "Resource": "arn:aws:s3:::example-project",
            },
        ]
        resources = [
            {
                "address": "aws_iam_role.terraform_plan",
                "values": {
                    "max_session_duration": 3600,
                    "assume_role_policy": policy([{
                        "Sid": "AllowOperatorWithMFA",
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Principal": {"AWS": "arn:aws:iam::000000000000:user/example"},
                        "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                    }]),
                },
            },
            {"address": "aws_iam_role_policy.terraform_plan", "values": {"policy": policy(role_policy)}},
            {
                "address": "aws_iam_user_policy.terraform_plan_assume",
                "values": {"policy": policy([{
                    "Sid": "AssumeTerraformPlanRole",
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": role_arn,
                }])},
            },
        ]
        self.plan = {
            "complete": True,
            "resource_changes": [
                {"mode": "managed", "address": address, "change": {"actions": actions}}
                for address, actions in module.EXPECTED_MUTATIONS.items()
            ],
            "planned_values": {"root_module": {"resources": resources}},
        }

    def test_reviewed_plan_passes(self):
        module.verify(self.plan)

    def test_extra_mutation_or_import_rejected(self):
        extra = copy.deepcopy(self.plan)
        extra["resource_changes"].append({"mode": "managed", "address": "aws_s3_bucket.other", "change": {"actions": ["update"]}})
        with self.assertRaises(ValueError):
            module.verify(extra)

        imported = copy.deepcopy(self.plan)
        imported["resource_changes"][0]["change"]["importing"] = {"id": "existing"}
        with self.assertRaises(ValueError):
            module.verify(imported)

    def test_missing_mfa_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][0]["values"]
        trust = json.loads(values["assume_role_policy"])
        del trust["Statement"][0]["Condition"]
        values["assume_role_policy"] = json.dumps(trust)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_state_write_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        document = json.loads(values["policy"])
        next(s for s in document["Statement"] if s["Sid"] == "ReadProjectState")["Action"] = ["s3:GetObject", "s3:PutObject"]
        values["policy"] = json.dumps(document)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_project_object_read_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        document = json.loads(values["policy"])
        next(s for s in document["Statement"] if s["Sid"] == "ReadProjectS3Configuration")["Action"].append("s3:GetObject")
        values["policy"] = json.dumps(document)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unrestricted_bucket_resource_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        document = json.loads(values["policy"])
        next(s for s in document["Statement"] if s["Sid"] == "ReadProjectS3Configuration")["Resource"] = "*"
        values["policy"] = json.dumps(document)
        with self.assertRaises(ValueError):
            module.verify(plan)

    def test_unexpected_read_action_rejected(self):
        plan = copy.deepcopy(self.plan)
        values = plan["planned_values"]["root_module"]["resources"][1]["values"]
        document = json.loads(values["policy"])
        next(s for s in document["Statement"] if s["Sid"] == "ReadProjectIAM")["Action"].append("iam:CreateRole")
        values["policy"] = json.dumps(document)
        with self.assertRaises(ValueError):
            module.verify(plan)


if __name__ == "__main__":
    unittest.main()
