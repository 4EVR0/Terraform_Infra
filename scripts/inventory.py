#!/usr/bin/env python3
"""Read-only AWS inventory. Raw responses remain local and gitignored.

Uses only explicit describe/list/get operations. Never fetches credentials,
secret values, EC2 user data, or S3 object contents. Not an exhaustive AWS scan.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", nargs="+", default=["ap-northeast-2"])
    parser.add_argument("--profile", default="default")
    parser.add_argument("--expected-account-id", required=True,
                        help="Expected 12-digit AWS account ID; stops on mismatch.")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{12}", args.expected_account_id):
        parser.error("--expected-account-id must contain exactly 12 digits")
    os.umask(0o077)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = Path(__file__).resolve().parents[1] / "inventory/raw" / stamp
    destination.mkdir(parents=True)
    env = dict(os.environ, AWS_PAGER="", AWS_MAX_ATTEMPTS="2")

    def query(label, service, operation, region="ap-northeast-2", extra=()):
        assert operation.startswith(("describe-", "list-", "get-"))
        command = ["aws", "--profile", args.profile, "--region", region,
                   "--cli-connect-timeout", "10", "--cli-read-timeout", "20",
                   service, operation, *extra, "--output", "json"]
        result = {"label": label, "region": region, "operation": f"{service}:{operation}"}
        try:
            process = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90)
            result["ok"] = process.returncode == 0
            if result["ok"]:
                result["data"] = json.loads(process.stdout or "{}")
            else:
                result["error"] = process.stderr.strip()
                match = re.search(r"An error occurred \(([^)]+)\)", process.stderr)
                result["error_code"] = match.group(1) if match else None
                result["absent"] = result["error_code"] in {
                    "NoSuchTagSet", "NoSuchBucketPolicy", "NoSuchLifecycleConfiguration",
                    "NoSuchPublicAccessBlockConfiguration",
                    "ServerSideEncryptionConfigurationNotFoundError",
                }
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            result.update(ok=False, error=str(exc))
        (destination / f"{label}.json").write_text(json.dumps(result, indent=2) + "\n")
        return result

    identity = query("identity", "sts", "get-caller-identity")
    if not identity["ok"] or identity["data"].get("Account") != args.expected_account_id:
        raise SystemExit("Expected project account could not be verified; stopped. See local identity.json.")

    jobs = [
        ("regions", "ec2", "describe-regions"),
        ("buckets", "s3api", "list-buckets"),
        ("hosted-zones", "route53", "list-hosted-zones"),
        ("cloudfront", "cloudfront", "list-distributions"),
    ]
    operations = [
        ("instances", "ec2", "describe-instances"),
        ("volumes", "ec2", "describe-volumes"),
        ("security-groups", "ec2", "describe-security-groups"),
        ("vpcs", "ec2", "describe-vpcs"),
        ("subnets", "ec2", "describe-subnets"),
        ("route-tables", "ec2", "describe-route-tables"),
        ("internet-gateways", "ec2", "describe-internet-gateways"),
        ("nat-gateways", "ec2", "describe-nat-gateways"),
        ("addresses", "ec2", "describe-addresses"),
        ("rds", "rds", "describe-db-instances"),
        ("queues", "sqs", "list-queues"),
        ("ecr", "ecr", "describe-repositories"),
        ("glue", "glue", "get-databases"),
        ("load-balancers", "elbv2", "describe-load-balancers"),
        ("autoscaling", "autoscaling", "describe-auto-scaling-groups"),
    ]
    for region in args.regions:
        jobs.extend((f"{region}-{label}", service, operation, region)
                    for label, service, operation in operations)
        # Omit Lambda environment variables from the captured output.
        jobs.append((f"{region}-lambda", "lambda", "list-functions", region,
                     ("--query", "Functions[].{Name:FunctionName,Arn:FunctionArn,Role:Role,Runtime:Runtime,PackageType:PackageType}")))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda job: query(*job), jobs))

    details = []
    for result in results:
        if not result["ok"]:
            continue
        if result["label"] == "buckets":
            for bucket in result["data"].get("Buckets", []):
                name = bucket["Name"]
                location = query(f"s3-{name}-location", "s3api", "get-bucket-location", extra=("--bucket", name))
                results_location = location.get("data", {}).get("LocationConstraint")
                bucket_region = "eu-west-1" if results_location == "EU" else (results_location or "us-east-1")
                # A failed location request is unknown, not us-east-1.
                details.append(location)
                if location["ok"]:
                    for operation in ("get-bucket-versioning", "get-bucket-encryption",
                                      "get-public-access-block", "get-bucket-tagging",
                                      "get-bucket-policy", "get-bucket-lifecycle-configuration"):
                        details.append(query(f"s3-{name}-{operation}", "s3api", operation,
                                             bucket_region, ("--bucket", name)))
    profiles = set()
    for result in results:
        if result["ok"] and result["label"].endswith("-instances"):
            for reservation in result["data"].get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    arn = instance.get("IamInstanceProfile", {}).get("Arn")
                    if arn:
                        profiles.add(arn.rsplit("/", 1)[-1])
    for profile in sorted(profiles):
        result = query(f"iam-profile-{profile}", "iam", "get-instance-profile",
                       extra=("--instance-profile-name", profile))
        details.append(result)
        if not result["ok"]:
            continue
        for role in result["data"]["InstanceProfile"]["Roles"]:
            name = role["RoleName"]
            for operation in ("list-attached-role-policies", "list-role-policies"):
                details.append(query(f"iam-{name}-{operation}", "iam", operation,
                                     extra=("--role-name", name)))
    all_results = [identity, *results, *details]
    manifest = {
        "recorded_at_utc": stamp, "regions": args.regions,
        "scope": "Selected services in requested regions; global buckets, DNS, CloudFront and attached instance profiles. Not exhaustive.",
        "results": [{key: value for key, value in item.items() if key != "data"} for item in all_results],
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Saved {len(all_results)} read results to {destination}")
    for result in all_results:
        if not result["ok"]:
            status = "ABSENT" if result.get("absent") else "UNRESOLVED"
            print(f"{status} {result['label']}: {result.get('error', '')[:240]}")
    if any(not result["ok"] and not result.get("absent") for result in all_results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
