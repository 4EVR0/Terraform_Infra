"""Verify that a saved plan only closes reviewed public ingress.

Allowed managed mutations:
- delete of each reviewed aws_vpc_security_group_ingress_rule address (no replacement);
- in-place update of each reviewed EC2 instance that only detaches one reviewed
  security group, keeps the required service group, and changes nothing else.
Any other managed mutation, import, replacement, or unknown value fails.
"""
import argparse
import json
from pathlib import Path

RULE_TYPE = "aws_vpc_security_group_ingress_rule"
INSTANCE_TYPE = "aws_instance"


def _parse_detach(value):
    try:
        target, removed, required = value.split(",")
    except ValueError as error:
        raise ValueError("Detach must be TARGET,REMOVED_GROUP_ID,REQUIRED_GROUP_ID.") from error
    return target, removed, required


def _without_groups(state):
    return {key: value for key, value in (state or {}).items() if key != "vpc_security_group_ids"}


def verify(plan, rule_addresses, detaches):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")

    expected_rules = set(rule_addresses)
    if len(expected_rules) != len(rule_addresses):
        raise ValueError("Reviewed rule addresses must be unique.")
    detach_targets = {target: (removed, required) for target, removed, required in detaches}
    if len(detach_targets) != len(detaches):
        raise ValueError("Each detach target may appear once.")
    if not expected_rules and not detach_targets:
        raise ValueError("Nothing to verify.")
    for address in expected_rules:
        if not address.startswith(RULE_TYPE + "."):
            raise ValueError("Only ingress rule addresses may be deleted.")
    for target in detach_targets:
        if not target.startswith(INSTANCE_TYPE + "."):
            raise ValueError("Only EC2 instances may be detach targets.")

    seen = set()
    for resource in plan.get("resource_changes", []):
        if resource.get("mode") != "managed":
            continue
        address = resource.get("address")
        change = resource.get("change", {})
        actions = change.get("actions")
        if change.get("importing") is not None:
            raise ValueError("Plan contains an unexpected import.")
        if actions == ["no-op"]:
            continue
        if address in seen:
            raise ValueError("Address appears more than once.")
        seen.add(address)

        if address in expected_rules:
            if actions != ["delete"]:
                raise ValueError(f"{address} must be deleted without replacement.")
        elif address in detach_targets:
            removed, required = detach_targets[address]
            if actions != ["update"]:
                raise ValueError(f"{address} must be one in-place update.")
            if change.get("after_unknown", {}).get("vpc_security_group_ids"):
                raise ValueError(f"{address} security group IDs are not fully known.")
            before = set(change.get("before", {}).get("vpc_security_group_ids") or [])
            after = set(change.get("after", {}).get("vpc_security_group_ids") or [])
            if removed not in before or removed in after:
                raise ValueError(f"{address} does not detach the reviewed group.")
            if required not in before or required not in after:
                raise ValueError(f"{address} does not keep the required service group.")
            if after != before - {removed}:
                raise ValueError(f"{address} changes groups beyond the reviewed detach.")
            if _without_groups(change.get("before")) != _without_groups(change.get("after")):
                raise ValueError(f"{address} changes attributes other than security groups.")
            if any(value for key, value in (change.get("after_unknown") or {}).items()
                   if key != "vpc_security_group_ids"):
                raise ValueError(f"{address} has unknown values after the update.")
        else:
            raise ValueError(f"Unexpected managed mutation: {address} {actions}.")

    missing = (expected_rules | set(detach_targets)) - seen
    if missing:
        raise ValueError(f"Reviewed changes are missing from the plan: {sorted(missing)}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--delete-rule", action="append", default=[], help="Reviewed ingress rule address to delete.")
    parser.add_argument("--detach", action="append", default=[],
                        help="TARGET,REMOVED_GROUP_ID,REQUIRED_GROUP_ID for one reviewed instance.")
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()), args.delete_rule, [_parse_detach(v) for v in args.detach])
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: plan only deletes reviewed ingress rules and detaches reviewed security groups.")
