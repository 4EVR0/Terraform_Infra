"""Check saved Terraform plan JSON locally; never upload the input file."""
import argparse
import json
from pathlib import Path


def verify(plan, target, expected_id):
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")
    imports = []
    for resource in plan.get("resource_changes", []):
        change = resource.get("change", {})
        if resource.get("mode") == "managed" and change.get("actions") != ["no-op"]:
            raise ValueError("Plan contains a managed resource mutation.")
        if change.get("importing") is not None:
            imports.append(resource)
    if len(imports) != 1:
        raise ValueError("Exactly one import is required.")
    resource = imports[0]
    if resource.get("mode") != "managed" or resource.get("address") != target:
        raise ValueError("Import target does not match.")
    if resource["change"]["importing"].get("id") != expected_id:
        raise ValueError("Import ID does not match the reviewed existing resource.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--expected-id", required=True)
    args = parser.parse_args()
    try:
        verify(json.loads(args.plan_json.read_text()), args.target, args.expected_id)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: exactly one expected import and no managed resource mutations.")
