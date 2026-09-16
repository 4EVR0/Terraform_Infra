"""Verify that a saved plan destroys exactly the reviewed managed resources."""
import argparse
import json
from pathlib import Path


def verify(plan, expected_addresses):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")

    expected = set(expected_addresses)
    if not expected or len(expected) != len(expected_addresses):
        raise ValueError("Expected destroy addresses must be unique and non-empty.")

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

    if set(mutations) != expected:
        raise ValueError("Managed mutations do not match the reviewed destroy set.")
    if any(actions != ["delete"] for actions in mutations.values()):
        raise ValueError("Every reviewed resource must be destroyed without replacement.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--expected-address", action="append", required=True)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()), args.expected_address)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: plan destroys exactly the reviewed managed resources.")
