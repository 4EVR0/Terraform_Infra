"""Verify that a saved plan only creates the reviewed restricted Terraform apply role."""
import argparse
import json
from pathlib import Path


EXPECTED_MUTATIONS = {
    "aws_iam_role.terraform_apply": ["create"],
    "aws_iam_role_policy.terraform_apply": ["create"],
    "aws_iam_user_policy.terraform_apply_assume": ["create"],
}

EXPECTED_SIDS = {
    "ListProjectStateBucket",
    "ReadProjectState",
    "ManageProjectStateLock",
    "ReadCallerIdentity",
    "ReadProjectEC2",
    "ReadProjectIAM",
    "ReadProjectS3Configuration",
    "WriteProjectState",
    "ManageReviewedInstances",
    "ModifyReviewedInstanceAttributes",
    "ManageReviewedSecurityGroupRules",
    "TagReviewedEC2Resources",
    "ManageReviewedIAMRoles",
    "ManageReviewedRolePolicyAttachments",
    "ManageReviewedInstanceProfiles",
    "ManageReviewedCustomerPolicies",
    "PassReviewedRolesToEC2",
    "ManageReviewedS3Protection",
    "DenyProjectStateDeletion",
    "DenyBootstrapStateAccess",
    "DenyResourceReplacementAndDeletion",
}

FORBIDDEN_ALLOW_ACTIONS = {
    "ec2:CreateNetworkInterface",
    "ec2:CreateSecurityGroup",
    "ec2:CreateVolume",
    "ec2:DeleteNetworkInterface",
    "ec2:DeleteSecurityGroup",
    "ec2:DeleteVolume",
    "ec2:RunInstances",
    "ec2:TerminateInstances",
    "iam:CreateInstanceProfile",
    "iam:CreatePolicy",
    "iam:CreateRole",
    "iam:DeleteInstanceProfile",
    "iam:DeletePolicy",
    "iam:DeleteRole",
    "s3:CreateBucket",
    "s3:DeleteBucket",
    "s3:DeleteObject",
}

REQUIRED_EXPLICIT_DENIES = FORBIDDEN_ALLOW_ACTIONS - {"s3:DeleteObject"}

SCOPED_WRITE_SIDS = {
    "WriteProjectState",
    "ManageReviewedInstances",
    "ModifyReviewedInstanceAttributes",
    "ManageReviewedSecurityGroupRules",
    "TagReviewedEC2Resources",
    "ManageReviewedIAMRoles",
    "ManageReviewedRolePolicyAttachments",
    "ManageReviewedInstanceProfiles",
    "ManageReviewedCustomerPolicies",
    "PassReviewedRolesToEC2",
    "ManageReviewedS3Protection",
}


def _actions(statement):
    value = statement.get("Action", [])
    return {value} if isinstance(value, str) else set(value)


def _resources(statement):
    value = statement.get("Resource", [])
    return {value} if isinstance(value, str) else set(value)


def _statements(policy):
    document = json.loads(policy)
    return {statement.get("Sid"): statement for statement in document.get("Statement", [])}


def _values_by_address(plan):
    resources = plan.get("planned_values", {}).get("root_module", {}).get("resources", [])
    return {resource.get("address"): resource.get("values", {}) for resource in resources}


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
        raise ValueError("Plan must create only the reviewed apply role and its two inline policies.")

    values = _values_by_address(plan)
    role = values["aws_iam_role.terraform_apply"]
    if role.get("max_session_duration") != 3600:
        raise ValueError("Apply role session duration must be one hour.")
    trust = _statements(role["assume_role_policy"])
    if set(trust) != {"AllowOperatorWithMFA"}:
        raise ValueError("Apply role trust policy has unexpected statements.")
    trust_statement = trust["AllowOperatorWithMFA"]
    principal = trust_statement.get("Principal", {}).get("AWS")
    if (
        trust_statement.get("Effect") != "Allow"
        or _actions(trust_statement) != {"sts:AssumeRole"}
        or not isinstance(principal, str)
        or ":user/" not in principal
        or trust_statement.get("Condition", {}).get("Bool", {}).get("aws:MultiFactorAuthPresent") != "true"
    ):
        raise ValueError("Apply role trust must allow one IAM user only when MFA is present.")

    policy = _statements(values["aws_iam_role_policy.terraform_apply"]["policy"])
    if set(policy) != EXPECTED_SIDS:
        raise ValueError("Apply role permission policy has unexpected statements.")

    for sid, statement in policy.items():
        if statement.get("Effect") == "Allow":
            forbidden = _actions(statement) & FORBIDDEN_ALLOW_ACTIONS
            if forbidden - {"s3:DeleteObject"}:
                raise ValueError(f"{sid} allows a forbidden destructive action.")
            if "s3:DeleteObject" in forbidden and sid != "ManageProjectStateLock":
                raise ValueError(f"{sid} allows DeleteObject outside the state lock.")
    for sid in SCOPED_WRITE_SIDS:
        resources = _resources(policy[sid])
        if not resources or "*" in resources:
            raise ValueError(f"{sid} must target explicit reviewed resources.")

    state_write = policy["WriteProjectState"]
    if _actions(state_write) != {"s3:PutObject"} or len(_resources(state_write)) != 1:
        raise ValueError("Project state write must contain PutObject for one object only.")
    state_resource = next(iter(_resources(state_write)))
    if state_resource.endswith(".tflock") or not state_resource.endswith("terraform.tfstate"):
        raise ValueError("Project state write targets the wrong object.")

    lock = policy["ManageProjectStateLock"]
    if _actions(lock) != {"s3:GetObject", "s3:PutObject", "s3:DeleteObject"}:
        raise ValueError("Project state lock permissions differ from the reviewed set.")
    if _resources(lock) != {f"{state_resource}.tflock"}:
        raise ValueError("Project state lock permission targets the wrong object.")

    state_delete_deny = policy["DenyProjectStateDeletion"]
    if state_delete_deny.get("Effect") != "Deny" or _actions(state_delete_deny) != {"s3:DeleteObject"}:
        raise ValueError("State object deletion must be explicitly denied.")
    if state_resource not in _resources(state_delete_deny):
        raise ValueError("Project state object is missing from the deletion deny.")

    bootstrap_deny = policy["DenyBootstrapStateAccess"]
    if bootstrap_deny.get("Effect") != "Deny" or _actions(bootstrap_deny) != {"s3:GetObject", "s3:PutObject"}:
        raise ValueError("Bootstrap state reads and writes must be explicitly denied.")

    destructive_deny = policy["DenyResourceReplacementAndDeletion"]
    if destructive_deny.get("Effect") != "Deny" or not REQUIRED_EXPLICIT_DENIES.issubset(_actions(destructive_deny)):
        raise ValueError("Resource creation and deletion actions must be explicitly denied.")

    attachment = policy["ManageReviewedRolePolicyAttachments"]
    policy_arns = attachment.get("Condition", {}).get("ArnEquals", {}).get("iam:PolicyARN")
    if not policy_arns:
        raise ValueError("Role policy attachments must be limited by iam:PolicyARN.")

    pass_role = policy["PassReviewedRolesToEC2"]
    if pass_role.get("Condition", {}).get("StringEquals", {}).get("iam:PassedToService") != "ec2.amazonaws.com":
        raise ValueError("PassRole must be limited to EC2.")

    assume = _statements(values["aws_iam_user_policy.terraform_apply_assume"]["policy"])
    if set(assume) != {"AssumeTerraformApplyRole"}:
        raise ValueError("Operator apply policy has unexpected statements.")
    assume_statement = assume["AssumeTerraformApplyRole"]
    assume_resources = _resources(assume_statement)
    if (
        assume_statement.get("Effect") != "Allow"
        or _actions(assume_statement) != {"sts:AssumeRole"}
        or len(assume_resources) != 1
        or not next(iter(assume_resources)).endswith(":role/4EVR0TerraformApplyRole")
    ):
        raise ValueError("Operator policy must only allow assuming the reviewed apply role.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: reviewed MFA-protected restricted Terraform apply role resources only.")
