"""Verify that a saved plan only creates the reviewed emergency administrator role."""
import argparse
import json
from pathlib import Path


EXPECTED_MUTATIONS = {
    "aws_iam_role.terraform_bootstrap_admin": ["create"],
    "aws_iam_role_policy_attachment.terraform_bootstrap_admin": ["create"],
    "aws_iam_role_policy.terraform_bootstrap_admin_guardrail": ["create"],
    "aws_iam_user_policy.terraform_bootstrap_admin_assume": ["create"],
}

EXPECTED_GUARDRAIL_ACTIONS = {
    "DenyStateDeletion": {"s3:DeleteObject", "s3:DeleteObjectVersion"},
    "DenyStateBucketDeletion": {"s3:DeleteBucket"},
    "DenyTerraformRoleDeletion": {"iam:DeleteRole"},
    "DenyOperatorDeletion": {"iam:DeleteUser"},
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
        raise ValueError("Plan must create only the reviewed bootstrap administrator resources.")

    values = _values_by_address(plan)
    role = values["aws_iam_role.terraform_bootstrap_admin"]
    if role.get("max_session_duration") != 3600:
        raise ValueError("Bootstrap administrator session duration must be one hour.")
    trust = _statements(role["assume_role_policy"])
    if set(trust) != {"AllowOperatorWithMFA"}:
        raise ValueError("Bootstrap administrator trust policy has unexpected statements.")
    trust_statement = trust["AllowOperatorWithMFA"]
    principal = trust_statement.get("Principal", {}).get("AWS")
    if (
        trust_statement.get("Effect") != "Allow"
        or _actions(trust_statement) != {"sts:AssumeRole"}
        or not isinstance(principal, str)
        or ":user/" not in principal
        or trust_statement.get("Condition", {}).get("Bool", {}).get("aws:MultiFactorAuthPresent") != "true"
    ):
        raise ValueError("Bootstrap administrator trust must allow one IAM user only with MFA.")

    attachment = values["aws_iam_role_policy_attachment.terraform_bootstrap_admin"]
    if attachment.get("policy_arn") != "arn:aws:iam::aws:policy/AdministratorAccess":
        raise ValueError("Bootstrap administrator must attach only AWS AdministratorAccess.")

    guardrails = _statements(values["aws_iam_role_policy.terraform_bootstrap_admin_guardrail"]["policy"])
    if set(guardrails) != set(EXPECTED_GUARDRAIL_ACTIONS):
        raise ValueError("Bootstrap administrator guardrail has unexpected statements.")
    for sid, expected_actions in EXPECTED_GUARDRAIL_ACTIONS.items():
        statement = guardrails[sid]
        if statement.get("Effect") != "Deny" or _actions(statement) != expected_actions:
            raise ValueError(f"{sid} differs from the reviewed explicit deny.")
        if not _resources(statement) or "*" in _resources(statement):
            raise ValueError(f"{sid} must target explicit protected resources.")

    state_resources = _resources(guardrails["DenyStateDeletion"])
    if len(state_resources) != 2 or not all(resource.endswith("/terraform.tfstate") for resource in state_resources):
        raise ValueError("State deletion deny must protect exactly two state objects.")
    state_buckets = {resource.rsplit("/", 3)[0] for resource in state_resources}
    bucket_resources = _resources(guardrails["DenyStateBucketDeletion"])
    if len(state_buckets) != 1 or bucket_resources != state_buckets:
        raise ValueError("State object and bucket deletion denies must protect the same bucket.")

    protected_roles = _resources(guardrails["DenyTerraformRoleDeletion"])
    expected_role_names = {
        "4EVR0TerraformPlanRole",
        "4EVR0TerraformApplyRole",
        "4EVR0TerraformBootstrapAdminRole",
    }
    if {resource.rsplit("/", 1)[-1] for resource in protected_roles} != expected_role_names:
        raise ValueError("Guardrail must protect all three Terraform roles from deletion.")

    assume = _statements(values["aws_iam_user_policy.terraform_bootstrap_admin_assume"]["policy"])
    if set(assume) != {"AssumeTerraformBootstrapAdminRole"}:
        raise ValueError("Operator bootstrap administrator policy has unexpected statements.")
    assume_statement = assume["AssumeTerraformBootstrapAdminRole"]
    assume_resources = _resources(assume_statement)
    if (
        assume_statement.get("Effect") != "Allow"
        or _actions(assume_statement) != {"sts:AssumeRole"}
        or len(assume_resources) != 1
        or not next(iter(assume_resources)).endswith(":role/4EVR0TerraformBootstrapAdminRole")
    ):
        raise ValueError("Operator policy must only allow assuming the reviewed bootstrap administrator role.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: reviewed MFA-protected bootstrap administrator resources only.")
