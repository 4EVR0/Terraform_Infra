import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inventory.py"
spec = importlib.util.spec_from_file_location("inventory", SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def run_inventory(self, mismatch=False, denied=False, absent=False):
        calls = []
        expected = "0" * 12

        def fake_run(command, **kwargs):
            calls.append(command)
            operation = next(word for word in command if word.startswith(("get-", "list-", "describe-")))
            response = {}
            error = None
            if operation == "get-caller-identity":
                response = {"Account": "1" * 12 if mismatch else expected}
            elif operation == "describe-regions":
                response = {"Regions": [{"RegionName": "region-a"}, {"RegionName": "region-b"}]}
            elif denied and operation == "describe-instances":
                error = "An error occurred (AccessDenied) when calling the DescribeInstances operation"
            elif absent and operation == "describe-repositories":
                response = {"repositories": [{"repositoryName": "example/test"}]}
            elif absent and operation in ("get-repository-policy", "get-lifecycle-policy"):
                error = "An error occurred (RepositoryPolicyNotFoundException) when calling the operation"
            return subprocess.CompletedProcess(command, 1 if error else 0, json.dumps(response), error or "")

        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "scripts/inventory.py"
            arguments = [str(script), "--all-regions", "--expected-account-id", expected]
            exit_code = 0
            with patch.object(inventory, "__file__", str(script)), patch("sys.argv", arguments), \
                    patch.object(inventory.subprocess, "run", side_effect=fake_run), \
                    contextlib.redirect_stdout(io.StringIO()):
                try:
                    inventory.main()
                except SystemExit as error:
                    exit_code = error.code
            manifests = list(Path(temporary).glob("inventory/raw/*/manifest.json"))
            manifest = json.loads(manifests[0].read_text()) if manifests else None
        return calls, exit_code, manifest

    def test_wrong_account_stops_before_resource_reads(self):
        calls, code, manifest = self.run_inventory(mismatch=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("get-caller-identity", calls[0])
        self.assertIsNone(manifest)

    def test_all_enabled_regions_are_scanned(self):
        calls, code, manifest = self.run_inventory()
        self.assertEqual(code, 0)
        self.assertEqual(manifest["regions"], ["region-a", "region-b"])
        reads = [command for command in calls if "describe-instances" in command]
        self.assertEqual({command[command.index("--region") + 1] for command in reads},
                         {"region-a", "region-b"})

    def test_access_denied_is_reported_and_fails_run(self):
        _, code, manifest = self.run_inventory(denied=True)
        self.assertEqual(code, 1)
        failures = [result for result in manifest["results"] if not result["ok"]]
        self.assertEqual(len(failures), 2)
        self.assertTrue(all(result["error_code"] == "AccessDenied" and not result["absent"]
                            for result in failures))

    def test_missing_optional_policy_is_known_absence(self):
        _, code, manifest = self.run_inventory(absent=True)
        self.assertEqual(code, 0)
        failures = [result for result in manifest["results"] if not result["ok"]]
        self.assertTrue(failures)
        self.assertTrue(all(result["absent"] for result in failures))


if __name__ == "__main__":
    unittest.main()
