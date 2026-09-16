"""Verify that a saved plan only creates one reviewed IAM policy attachment."""
import argparse
import json
from pathlib import Path


def root_resource_values(plan):
    resources = plan.get("planned_values", {}).get("root_module", {}).get("resources", [])
    return {resource.get("address"): resource.get("values", {}) for resource in resources}


def verify(plan, target, expected_role, expected_policy_arn):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")

    mutations = {}
    for resource in plan.get("resource_changes", []):
        if resource.get("mode") != "managed":
            continue
        change = resource.get("change", {})
        if change.get("importing") is not None:
            raise ValueError("Plan contains an unexpected import.")
        actions = change.get("actions")
        if actions != ["no-op"]:
            mutations[resource.get("address")] = actions

    if mutations != {target: ["create"]}:
        raise ValueError("Plan must only create the reviewed IAM policy attachment.")

    values = root_resource_values(plan).get(target)
    if values is None:
        raise ValueError("Planned IAM policy attachment is missing.")
    if values.get("role") != expected_role or values.get("policy_arn") != expected_policy_arn:
        raise ValueError("Planned IAM role or policy ARN does not match the reviewed values.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--expected-role", required=True)
    parser.add_argument("--expected-policy-arn", required=True)
    args = parser.parse_args()
    try:
        verify(
            json.loads(args.plan_json.read_text()),
            args.target,
            args.expected_role,
            args.expected_policy_arn,
        )
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: one reviewed IAM policy attachment create and no other managed mutations.")
