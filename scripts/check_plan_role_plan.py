"""Verify that a saved plan only creates the reviewed MFA-protected plan role resources."""
import argparse
import json
from pathlib import Path


EXPECTED_MUTATIONS = {
    "aws_iam_role.terraform_plan": ["create"],
    "aws_iam_role_policy.terraform_plan": ["create"],
    "aws_iam_user_policy.terraform_plan_assume": ["create"],
}

EXPECTED_IAM_READ_ACTIONS = {
    "iam:GetInstanceProfile",
    "iam:GetPolicy",
    "iam:GetPolicyVersion",
    "iam:GetRole",
    "iam:GetRolePolicy",
    "iam:ListAttachedRolePolicies",
    "iam:ListEntitiesForPolicy",
    "iam:ListInstanceProfilesForRole",
    "iam:ListInstanceProfileTags",
    "iam:ListPolicyTags",
    "iam:ListPolicyVersions",
    "iam:ListRolePolicies",
    "iam:ListRoleTags",
}

EXPECTED_S3_CONFIGURATION_ACTIONS = {
    "s3:GetAccelerateConfiguration",
    "s3:GetBucketAcl",
    "s3:GetBucketCORS",
    "s3:GetBucketLocation",
    "s3:GetBucketLogging",
    "s3:GetBucketNotification",
    "s3:GetBucketObjectLockConfiguration",
    "s3:GetBucketOwnershipControls",
    "s3:GetBucketPolicy",
    "s3:GetBucketPolicyStatus",
    "s3:GetBucketPublicAccessBlock",
    "s3:GetBucketRequestPayment",
    "s3:GetBucketTagging",
    "s3:GetBucketVersioning",
    "s3:GetBucketWebsite",
    "s3:GetEncryptionConfiguration",
    "s3:GetLifecycleConfiguration",
    "s3:GetReplicationConfiguration",
    "s3:ListBucket",
}


def _values_by_address(plan):
    resources = plan.get("planned_values", {}).get("root_module", {}).get("resources", [])
    return {resource.get("address"): resource.get("values", {}) for resource in resources}


def _actions(statement):
    value = statement.get("Action", [])
    return {value} if isinstance(value, str) else set(value)


def _resources(statement):
    value = statement.get("Resource", [])
    return {value} if isinstance(value, str) else set(value)


def _statements(policy):
    document = json.loads(policy)
    statements = document.get("Statement", [])
    return {statement.get("Sid"): statement for statement in statements}


def verify(plan):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")

    mutations = {}
    for resource in plan.get("resource_changes", []):
        if resource.get("mode") != "managed":
            continue
        change = resource.get("change", {})
        if change.get("importing") is not None:
            raise ValueError("Plan contains an unexpected import.")
        if change.get("actions") != ["no-op"]:
            mutations[resource.get("address")] = change.get("actions")
    if mutations != EXPECTED_MUTATIONS:
        raise ValueError("Plan must create only the reviewed plan role and its two inline policies.")

    values = _values_by_address(plan)
    role = values["aws_iam_role.terraform_plan"]
    if role.get("max_session_duration") != 3600:
        raise ValueError("Plan role session duration must be one hour.")

    trust = _statements(role["assume_role_policy"])
    if set(trust) != {"AllowOperatorWithMFA"}:
        raise ValueError("Plan role trust policy has unexpected statements.")
    trust_statement = trust["AllowOperatorWithMFA"]
    principal = trust_statement.get("Principal", {}).get("AWS")
    if (
        trust_statement.get("Effect") != "Allow"
        or _actions(trust_statement) != {"sts:AssumeRole"}
        or not isinstance(principal, str)
        or ":user/" not in principal
        or trust_statement.get("Condition", {}).get("Bool", {}).get("aws:MultiFactorAuthPresent") != "true"
    ):
        raise ValueError("Plan role trust must allow one IAM user only when MFA is present.")

    role_policy = _statements(values["aws_iam_role_policy.terraform_plan"]["policy"])
    expected_sids = {
        "ListProjectStateBucket",
        "ReadProjectState",
        "ManageProjectStateLock",
        "ReadCallerIdentity",
        "ReadProjectEC2",
        "ReadProjectIAM",
        "ReadProjectS3Configuration",
    }
    if set(role_policy) != expected_sids:
        raise ValueError("Plan role permission policy has unexpected statements.")

    state_read = role_policy["ReadProjectState"]
    state_resources = _resources(state_read)
    if _actions(state_read) != {"s3:GetObject"} or len(state_resources) != 1:
        raise ValueError("Project state permission must be read-only and target one object.")
    state_resource = next(iter(state_resources))
    if state_resource.endswith(".tflock"):
        raise ValueError("Project state read statement points to the lock instead of the state object.")

    lock = role_policy["ManageProjectStateLock"]
    lock_resources = _resources(lock)
    if _actions(lock) != {"s3:GetObject", "s3:PutObject", "s3:DeleteObject"} or len(lock_resources) != 1:
        raise ValueError("Lock permission must contain only get, put, and delete for one object.")
    if next(iter(lock_resources)) != f"{state_resource}.tflock":
        raise ValueError("Lock permission must target the project state lock object.")

    bucket_list = role_policy["ListProjectStateBucket"]
    prefixes = bucket_list.get("Condition", {}).get("StringEquals", {}).get("s3:prefix", [])
    prefixes = {prefixes} if isinstance(prefixes, str) else set(prefixes)
    if _actions(bucket_list) != {"s3:ListBucket"} or len(prefixes) != 2:
        raise ValueError("State bucket listing must be limited to the state and lock prefixes.")

    if _actions(role_policy["ReadCallerIdentity"]) != {"sts:GetCallerIdentity"}:
        raise ValueError("Caller identity statement contains unexpected actions.")
    if _actions(role_policy["ReadProjectEC2"]) != {"ec2:Describe*"}:
        raise ValueError("EC2 statement must be describe-only.")
    if _actions(role_policy["ReadProjectIAM"]) != EXPECTED_IAM_READ_ACTIONS:
        raise ValueError("IAM read statement differs from the reviewed action set.")

    s3_configuration = role_policy["ReadProjectS3Configuration"]
    if _actions(s3_configuration) != EXPECTED_S3_CONFIGURATION_ACTIONS:
        raise ValueError("S3 configuration statement differs from the reviewed action set.")
    if not _resources(s3_configuration) or "*" in _resources(s3_configuration):
        raise ValueError("S3 configuration reads must target explicit project bucket ARNs.")
    if "s3:GetObject" in _actions(s3_configuration):
        raise ValueError("Project data object reads are not allowed.")

    assume = _statements(values["aws_iam_user_policy.terraform_plan_assume"]["policy"])
    if set(assume) != {"AssumeTerraformPlanRole"}:
        raise ValueError("Operator policy has unexpected statements.")
    assume_statement = assume["AssumeTerraformPlanRole"]
    assume_resources = _resources(assume_statement)
    if (
        assume_statement.get("Effect") != "Allow"
        or _actions(assume_statement) != {"sts:AssumeRole"}
        or len(assume_resources) != 1
        or not next(iter(assume_resources)).endswith(":role/4EVR0TerraformPlanRole")
    ):
        raise ValueError("Operator policy must only allow assuming the reviewed plan role.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: reviewed MFA-protected Terraform plan role resources only.")
