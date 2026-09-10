"""Check saved Terraform plan JSON locally; never upload the input file."""
import argparse
import json
from pathlib import Path


def verify_many(plan, expected):
    if not isinstance(expected, dict) or not expected or not all(
        isinstance(address, str) and address and isinstance(identifier, str) and identifier
        for address, identifier in expected.items()
    ):
        raise ValueError("Expected imports must be a nonempty address-to-ID map.")
    resource_ids = set()
    for address, identifier in expected.items():
        parts = address.split(".")
        if len(parts) < 2:
            raise ValueError("Expected import addresses must include a resource type and name.")
        resource_id = (parts[-2], identifier)
        if resource_id in resource_ids:
            raise ValueError("An existing ID must not be owned by multiple addresses of the same resource type.")
        resource_ids.add(resource_id)
    if plan.get("errored") or plan.get("complete") is False or plan.get("deferred_changes"):
        raise ValueError("Plan is errored, incomplete, or deferred.")
    imports = {}
    for resource in plan.get("resource_changes", []):
        change = resource.get("change", {})
        if resource.get("mode") == "managed" and change.get("actions") != ["no-op"]:
            raise ValueError("Plan contains a managed resource mutation.")
        if change.get("importing") is not None:
            address = resource.get("address")
            if resource.get("mode") != "managed" or address in imports:
                raise ValueError("Invalid or duplicate import target.")
            imports[address] = change["importing"].get("id")
    if imports != expected:
        raise ValueError("Import targets or IDs do not match the reviewed set.")


def verify(plan, target, expected_id):
    verify_many(plan, {target: expected_id})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--expected-id")
    parser.add_argument("--expected-imports", type=Path)
    args = parser.parse_args()
    try:
        if args.expected_imports:
            if args.target or args.expected_id:
                parser.error("Use either --expected-imports or --target with --expected-id.")
            expected = json.loads(args.expected_imports.read_text())
        else:
            if not args.target or not args.expected_id:
                parser.error("Provide --expected-imports or both --target and --expected-id.")
            expected = {args.target: args.expected_id}
        verify_many(json.loads(args.plan_json.read_text()), expected)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: {len(expected)} expected import(s) and no managed resource mutations.")
