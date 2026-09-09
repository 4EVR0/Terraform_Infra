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
    region_args = parser.add_mutually_exclusive_group()
    region_args.add_argument("--regions", nargs="+", default=["ap-northeast-2"])
    region_args.add_argument("--all-regions", action="store_true",
                             help="Query selected services in every enabled AWS region.")
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
                    "OwnershipControlsNotFoundError",
                    "RepositoryPolicyNotFoundException", "LifecyclePolicyNotFoundException",
                }
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            result.update(ok=False, error=str(exc))
        (destination / f"{label}.json").write_text(json.dumps(result, indent=2) + "\n")
        return result

    identity = query("identity", "sts", "get-caller-identity")
    if not identity["ok"] or identity["data"].get("Account") != args.expected_account_id:
        raise SystemExit("Expected project account could not be verified; stopped. See local identity.json.")

    regions_result = query("regions", "ec2", "describe-regions")
    if args.all_regions:
        if not regions_result["ok"]:
            raise SystemExit("Enabled regions could not be verified; stopped.")
        args.regions = sorted(region["RegionName"] for region in regions_result["data"]["Regions"])
    print(f"Scanning {len(args.regions)} region(s); raw responses remain local.", flush=True)
    jobs = [
        ("iam-roles", "iam", "list-roles"),
        ("iam-users", "iam", "list-users"),
        ("iam-oidc", "iam", "list-open-id-connect-providers"),
        ("s3-account-public-access", "s3control", "get-public-access-block", "ap-northeast-2",
         ("--account-id", args.expected_account_id)),
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
        ("rds-clusters", "rds", "describe-db-clusters"),
        ("ecs", "ecs", "list-clusters"),
        ("eks", "eks", "list-clusters"),
        ("dynamodb", "dynamodb", "list-tables"),
        ("elasticache", "elasticache", "describe-cache-clusters"),
        ("classic-elb", "elb", "describe-load-balancers"),
        ("athena", "athena", "list-work-groups"),
        ("log-groups", "logs", "describe-log-groups"),
        ("eventbridge-rules", "events", "list-rules"),
        ("backup-vaults", "backup", "list-backup-vaults"),
        ("kms", "kms", "list-aliases"),
        ("queues", "sqs", "list-queues"),
        ("ecr", "ecr", "describe-repositories"),
        ("glue", "glue", "get-databases"),
        ("load-balancers", "elbv2", "describe-load-balancers"),
        ("autoscaling", "autoscaling", "describe-auto-scaling-groups"),
    ]
    for region in args.regions:
        jobs.extend((f"{region}-{label}", service, operation, region)
                    for label, service, operation in operations)
        jobs.append((f"{region}-snapshots", "ec2", "describe-snapshots", region,
                     ("--owner-ids", "self", "--query",
                      "Snapshots[].{Id:SnapshotId,Volume:VolumeId,Size:VolumeSize,State:State,Time:StartTime,Encrypted:Encrypted,Tags:Tags}")))
        jobs.append((f"{region}-alarms", "cloudwatch", "describe-alarms", region,
                     ("--query", "{Metric:MetricAlarms[].{Name:AlarmName,Namespace:Namespace,Metric:MetricName,State:StateValue},Composite:CompositeAlarms[].{Name:AlarmName,State:StateValue}}")))
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
                                      "get-bucket-policy", "get-bucket-lifecycle-configuration",
                                      "get-bucket-acl", "get-bucket-ownership-controls",
                                      "get-bucket-logging", "get-bucket-notification-configuration"):
                        details.append(query(f"s3-{name}-{operation}", "s3api", operation,
                                             bucket_region, ("--bucket", name)))
        if result["label"].endswith("-ecr"):
            for repository in result["data"].get("repositories", []):
                name = repository["repositoryName"]
                for operation in ("get-repository-policy", "get-lifecycle-policy"):
                    # Repository names may contain slashes; use a stable safe label.
                    label = name.encode().hex()
                    details.append(query(f"{result['region']}-ecr-{label}-{operation}", "ecr", operation,
                                         result["region"], ("--repository-name", name)))
        if result["label"].endswith("-glue"):
            for database in result["data"].get("DatabaseList", []):
                name = database["Name"]
                details.append(query(f"{result['region']}-glue-tables-{name.encode().hex()}", "glue", "get-tables",
                                     result["region"], ("--database-name", name, "--query",
                                     "TableList[].{Name:Name,Type:TableType,Location:StorageDescriptor.Location,Created:CreateTime,Updated:UpdateTime}")))
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
                policy_list = query(f"iam-{name}-{operation}", "iam", operation,
                                    extra=("--role-name", name))
                details.append(policy_list)
                if not policy_list["ok"]:
                    continue
                for policy_name in policy_list["data"].get("PolicyNames", []):
                    details.append(query(f"iam-{name}-inline-{policy_name}", "iam", "get-role-policy",
                                         extra=("--role-name", name, "--policy-name", policy_name)))
                for policy in policy_list["data"].get("AttachedPolicies", []):
                    arn = policy["PolicyArn"]
                    label = arn.encode().hex()
                    metadata = query(f"iam-policy-{label}", "iam", "get-policy",
                                     extra=("--policy-arn", arn))
                    details.append(metadata)
                    if metadata["ok"]:
                        version = metadata["data"]["Policy"]["DefaultVersionId"]
                        details.append(query(f"iam-policy-{label}-{version}", "iam", "get-policy-version",
                                             extra=("--policy-arn", arn, "--version-id", version)))
    all_results = [identity, regions_result, *results, *details]
    manifest = {
        "recorded_at_utc": stamp, "regions": args.regions,
        "scope": "Selected service APIs in requested/enabled regions; global S3, DNS, CloudFront, IAM identities and policies of EC2-attached roles. Not exhaustive; nested resources and additional services may remain.",
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
