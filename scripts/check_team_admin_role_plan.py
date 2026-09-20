"""Verify that a saved plan only creates the reviewed MFA-protected team administrator access."""
import argparse
import json
from pathlib import Path


EXPECTED_MUTATIONS = {
    "aws_iam_role.team_admin": ["create"],
    "aws_iam_role_policy_attachment.team_admin": ["create"],
    "aws_iam_role_policy.team_admin_guardrail": ["create"],
    "aws_iam_group.team_users": ["create"],
    "aws_iam_group_policy.team_users": ["create"],
    "aws_iam_group_membership.team_users": ["create"],
}

EXPECTED_GUARDRAIL_ACTIONS = {
    "DenyStateDeletion": {"s3:DeleteObject", "s3:DeleteObjectVersion"},
    "DenyStateBucketDeletion": {"s3:DeleteBucket"},
    "DenyTerraformRoleMutation": {
        "iam:AttachRolePolicy",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:UpdateRole",
        "iam:UpdateRoleDescription",
    },
    "DenyTerraformOperatorMutation": {
        "iam:AddUserToGroup",
        "iam:AttachUserPolicy",
        "iam:CreateAccessKey",
        "iam:CreateLoginProfile",
        "iam:DeactivateMFADevice",
        "iam:DeleteAccessKey",
        "iam:DeleteLoginProfile",
        "iam:DeleteUser",
        "iam:DeleteUserPolicy",
        "iam:DetachUserPolicy",
        "iam:EnableMFADevice",
        "iam:PutUserPolicy",
        "iam:RemoveUserFromGroup",
        "iam:ResyncMFADevice",
        "iam:TagUser",
        "iam:UntagUser",
        "iam:UpdateAccessKey",
        "iam:UpdateLoginProfile",
        "iam:UpdateUser",
    },
}

EXPECTED_BASE_SIDS = {
    "ReadOwnIdentitySettings",
    "ManageOwnPasswordAndMFA",
    "ManageOwnVirtualMFADevice",
    "ListVirtualMFADevices",
    "AssumeTeamAdminRole",
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
        raise ValueError("Plan must create only the reviewed team administrator access resources.")

    values = _values_by_address(plan)
    role = values["aws_iam_role.team_admin"]
    if role.get("max_session_duration") != 7200:
        raise ValueError("Team administrator session duration must be two hours.")
    trust = _statements(role["assume_role_policy"])
    if set(trust) != {"AllowNamedTeamUsersWithMFA"}:
        raise ValueError("Team administrator trust policy has unexpected statements.")
    trust_statement = trust["AllowNamedTeamUsersWithMFA"]
    principals = trust_statement.get("Principal", {}).get("AWS", [])
    if isinstance(principals, str):
        principals = [principals]
    if (
        trust_statement.get("Effect") != "Allow"
        or _actions(trust_statement) != {"sts:AssumeRole"}
        or not principals
        or any(":user/" not in principal for principal in principals)
        or trust_statement.get("Condition", {}).get("Bool", {}).get("aws:MultiFactorAuthPresent") != "true"
    ):
        raise ValueError("Team administrator trust must allow named IAM users only with MFA.")

    attachment = values["aws_iam_role_policy_attachment.team_admin"]
    if attachment.get("policy_arn") != "arn:aws:iam::aws:policy/AdministratorAccess":
        raise ValueError("Team administrator must attach only AWS AdministratorAccess.")

    guardrails = _statements(values["aws_iam_role_policy.team_admin_guardrail"]["policy"])
    if set(guardrails) != set(EXPECTED_GUARDRAIL_ACTIONS):
        raise ValueError("Team administrator guardrail has unexpected statements.")
    for sid, expected_actions in EXPECTED_GUARDRAIL_ACTIONS.items():
        statement = guardrails[sid]
        if statement.get("Effect") != "Deny" or _actions(statement) != expected_actions:
            raise ValueError(f"{sid} differs from the reviewed explicit deny.")
        if not _resources(statement) or "*" in _resources(statement):
            raise ValueError(f"{sid} must target explicit protected resources.")

    protected_roles = _resources(guardrails["DenyTerraformRoleMutation"])
    expected_role_names = {
        "4EVR0TerraformPlanRole",
        "4EVR0TerraformApplyRole",
        "4EVR0TerraformBootstrapAdminRole",
        "4EVR0TeamAdminRole",
    }
    if {resource.rsplit("/", 1)[-1] for resource in protected_roles} != expected_role_names:
        raise ValueError("Guardrail must protect all Terraform and team administrator roles.")

    operator_resources = _resources(guardrails["DenyTerraformOperatorMutation"])
    if len(operator_resources) != 1 or ":user/" not in next(iter(operator_resources)):
        raise ValueError("Guardrail must protect one explicit Terraform operator user.")

    base = _statements(values["aws_iam_group_policy.team_users"]["policy"])
    if set(base) != EXPECTED_BASE_SIDS:
        raise ValueError("Team user base policy has unexpected statements.")
    assume = base["AssumeTeamAdminRole"]
    if (
        assume.get("Effect") != "Allow"
        or _actions(assume) != {"sts:AssumeRole"}
        or _resources(assume) != {next(resource for resource in protected_roles if resource.endswith("/4EVR0TeamAdminRole"))}
    ):
        raise ValueError("Team users may assume only the reviewed team administrator role.")
    for sid in ("ManageOwnPasswordAndMFA", "ManageOwnVirtualMFADevice"):
        resources = _resources(base[sid])
        if len(resources) != 1 or "${aws:username}" not in next(iter(resources)):
            raise ValueError(f"{sid} must remain restricted to the current IAM user.")

    membership = values["aws_iam_group_membership.team_users"]
    members = set(membership.get("users", []))
    trusted_names = {principal.rsplit("/", 1)[-1] for principal in principals}
    if membership.get("group") != "4EVR0TeamUsers" or members != trusted_names:
        raise ValueError("Team group membership must exactly match trusted role principals.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()))
    except (ValueError, OSError, KeyError, StopIteration, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: reviewed MFA-protected team administrator access resources only.")
