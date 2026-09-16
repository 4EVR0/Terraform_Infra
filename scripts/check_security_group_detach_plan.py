"""Verify that a saved plan only detaches one reviewed security group."""
import argparse
import json
from pathlib import Path


def verify(plan, target, removed_group_id, required_group_id):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")

    target_change = None
    for resource in plan.get("resource_changes", []):
        if resource.get("mode") != "managed":
            continue
        change = resource.get("change", {})
        actions = change.get("actions")
        if resource.get("address") == target:
            if target_change is not None:
                raise ValueError("Target appears more than once.")
            target_change = change
            if actions != ["update"] or change.get("importing") is not None:
                raise ValueError("Target must be one in-place update without import.")
        elif actions != ["no-op"]:
            raise ValueError("Plan contains another managed resource mutation.")

    if target_change is None:
        raise ValueError("Expected target update is missing.")

    before = set(target_change.get("before", {}).get("vpc_security_group_ids") or [])
    after = set(target_change.get("after", {}).get("vpc_security_group_ids") or [])
    if target_change.get("after_unknown", {}).get("vpc_security_group_ids"):
        raise ValueError("Planned security group IDs are not fully known.")
    if removed_group_id not in before or removed_group_id in after:
        raise ValueError("Reviewed security group is not removed exactly as expected.")
    if required_group_id not in before or required_group_id not in after:
        raise ValueError("Required service security group is not preserved.")
    if after != before - {removed_group_id}:
        raise ValueError("Plan changes security group membership beyond the reviewed removal.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--removed-group-id", required=True)
    parser.add_argument("--required-group-id", required=True)
    args = parser.parse_args()
    try:
        verify(
            json.loads(args.plan_json.read_text()),
            args.target,
            args.removed_group_id,
            args.required_group_id,
        )
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: reviewed security group detached from one target with no other managed mutations.")
