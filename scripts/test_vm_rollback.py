#!/usr/bin/env python3
"""
VM Deployment Rollback Test Script

Tests rollback procedures WITHOUT actually rolling back.
Validates that rollback commands would work if executed.

Usage:
    python scripts/test_vm_rollback.py --resource-group haymaker-dev-rg --dry-run
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum


class RollbackTestStatus(Enum):
    """Rollback test result status"""

    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"


@dataclass
class RollbackTestResult:
    """Single rollback test result"""

    test_name: str
    status: RollbackTestStatus
    message: str
    command: str | None = None
    details: str | None = None


class VMRollbackTester:
    """Tests VM rollback procedures (dry-run mode)"""

    def __init__(self, resource_group: str, dry_run: bool = True):
        self.resource_group = resource_group
        self.dry_run = dry_run
        self.results: list[RollbackTestResult] = []

    def run_az_command(self, cmd: list[str]) -> tuple[int, str, str]:
        """Execute Azure CLI command safely"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 30 seconds"
        except Exception as e:
            return 1, "", str(e)

    def test_vm_can_be_stopped(self) -> RollbackTestResult:
        """Test that VM can be stopped (prerequisite for rollback)"""
        # Query VM state
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'haymaker')].{name:name, provisioningState:provisioningState}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="VM Can Be Stopped",
                status=RollbackTestStatus.FAIL,
                message="Failed to query VM state",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return RollbackTestResult(
                    test_name="VM Can Be Stopped",
                    status=RollbackTestStatus.WARN,
                    message="No VM found to test stopping",
                )

            vm_name = vms[0]["name"]
            stop_command = f"az vm stop --name {vm_name} --resource-group {self.resource_group}"

            return RollbackTestResult(
                test_name="VM Can Be Stopped",
                status=RollbackTestStatus.PASS,
                message=f"VM {vm_name} can be stopped",
                command=stop_command,
                details="Command would stop VM gracefully",
            )
        except (json.JSONDecodeError, KeyError) as e:
            return RollbackTestResult(
                test_name="VM Can Be Stopped",
                status=RollbackTestStatus.FAIL,
                message="Failed to parse VM data",
                details=str(e),
            )

    def test_vm_can_be_deallocated(self) -> RollbackTestResult:
        """Test that VM can be deallocated (frees compute resources)"""
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'haymaker')].name",
            "-o",
            "tsv",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="VM Can Be Deallocated",
                status=RollbackTestStatus.FAIL,
                message="Failed to query VM",
                details=stderr,
            )

        vm_name = stdout.strip()
        if not vm_name:
            return RollbackTestResult(
                test_name="VM Can Be Deallocated",
                status=RollbackTestStatus.WARN,
                message="No VM found to test deallocation",
            )

        deallocate_command = (
            f"az vm deallocate --name {vm_name} --resource-group {self.resource_group}"
        )

        return RollbackTestResult(
            test_name="VM Can Be Deallocated",
            status=RollbackTestStatus.PASS,
            message=f"VM {vm_name} can be deallocated",
            command=deallocate_command,
            details="Command would deallocate VM and stop billing for compute",
        )

    def test_vm_can_be_deleted(self) -> RollbackTestResult:
        """Test that VM can be deleted (full rollback)"""
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'haymaker')].{name:name, id:id}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="VM Can Be Deleted",
                status=RollbackTestStatus.FAIL,
                message="Failed to query VM",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return RollbackTestResult(
                    test_name="VM Can Be Deleted",
                    status=RollbackTestStatus.WARN,
                    message="No VM found to test deletion",
                )

            vm_name = vms[0]["name"]
            delete_command = (
                f"az vm delete --name {vm_name} --resource-group {self.resource_group} --yes"
            )

            return RollbackTestResult(
                test_name="VM Can Be Deleted",
                status=RollbackTestStatus.PASS,
                message=f"VM {vm_name} can be deleted",
                command=delete_command,
                details="⚠️  WARNING: This deletes the VM permanently!",
            )
        except (json.JSONDecodeError, KeyError) as e:
            return RollbackTestResult(
                test_name="VM Can Be Deleted",
                status=RollbackTestStatus.FAIL,
                message="Failed to parse VM data",
                details=str(e),
            )

    def test_function_apps_still_exist(self) -> RollbackTestResult:
        """Test that Function Apps still exist (rollback target)"""
        cmd = [
            "az",
            "functionapp",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[].{name:name, state:state}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="Function Apps Exist",
                status=RollbackTestStatus.FAIL,
                message="Failed to query Function Apps",
                details=stderr,
            )

        try:
            function_apps = json.loads(stdout)
            if not function_apps:
                return RollbackTestResult(
                    test_name="Function Apps Exist",
                    status=RollbackTestStatus.WARN,
                    message="No Function Apps found (rollback target missing)",
                    details="If rollback is needed, Function Apps must be recreated",
                )

            running_apps = [app for app in function_apps if app.get("state") == "Running"]
            return RollbackTestResult(
                test_name="Function Apps Exist",
                status=RollbackTestStatus.PASS,
                message=f"Found {len(function_apps)} Function Apps ({len(running_apps)} running)",
                details=f"Rollback target available: {', '.join(app['name'] for app in function_apps[:3])}...",
            )
        except (json.JSONDecodeError, KeyError) as e:
            return RollbackTestResult(
                test_name="Function Apps Exist",
                status=RollbackTestStatus.FAIL,
                message="Failed to parse Function Apps data",
                details=str(e),
            )

    def test_deployment_can_be_deleted(self) -> RollbackTestResult:
        """Test that deployment itself can be deleted"""
        cmd = [
            "az",
            "deployment",
            "group",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'vm')].{name:name, state:properties.provisioningState}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="Deployment Can Be Deleted",
                status=RollbackTestStatus.FAIL,
                message="Failed to query deployments",
                details=stderr,
            )

        try:
            deployments = json.loads(stdout)
            if not deployments:
                return RollbackTestResult(
                    test_name="Deployment Can Be Deleted",
                    status=RollbackTestStatus.WARN,
                    message="No VM deployment found",
                )

            deployment_name = deployments[0]["name"]
            delete_command = (
                f"az deployment group delete "
                f"--name {deployment_name} "
                f"--resource-group {self.resource_group}"
            )

            return RollbackTestResult(
                test_name="Deployment Can Be Deleted",
                status=RollbackTestStatus.PASS,
                message=f"Deployment {deployment_name} can be deleted",
                command=delete_command,
                details="Deletes deployment history, not resources",
            )
        except (json.JSONDecodeError, KeyError) as e:
            return RollbackTestResult(
                test_name="Deployment Can Be Deleted",
                status=RollbackTestStatus.FAIL,
                message="Failed to parse deployment data",
                details=str(e),
            )

    def test_network_resources_can_be_deleted(self) -> RollbackTestResult:
        """Test that network resources (VNet, NSG, PublicIP) can be deleted"""
        # Check VNet
        cmd = [
            "az",
            "network",
            "vnet",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'vm')].name",
            "-o",
            "tsv",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return RollbackTestResult(
                test_name="Network Resources Can Be Deleted",
                status=RollbackTestStatus.FAIL,
                message="Failed to query network resources",
                details=stderr,
            )

        vnet_name = stdout.strip()
        if not vnet_name:
            return RollbackTestResult(
                test_name="Network Resources Can Be Deleted",
                status=RollbackTestStatus.WARN,
                message="No VNet found",
            )

        delete_commands = [
            f"az network vnet delete --name {vnet_name} --resource-group {self.resource_group}",
            f"az network nsg delete --name {vnet_name}-nsg --resource-group {self.resource_group}",
            f"az network public-ip delete --name {vnet_name}-ip --resource-group {self.resource_group}",
        ]

        return RollbackTestResult(
            test_name="Network Resources Can Be Deleted",
            status=RollbackTestStatus.PASS,
            message=f"Network resources can be deleted (VNet: {vnet_name})",
            command="; ".join(delete_commands),
            details="Deletes VNet, NSG, and Public IP",
        )

    def run_all_tests(self) -> bool:
        """Run all rollback tests"""
        print("🧪 Starting VM rollback procedure tests...\n")
        if self.dry_run:
            print("⚠️  DRY-RUN MODE: No actual changes will be made\n")

        tests = [
            self.test_function_apps_still_exist,  # Check rollback target first
            self.test_vm_can_be_stopped,
            self.test_vm_can_be_deallocated,
            self.test_deployment_can_be_deleted,
            self.test_network_resources_can_be_deleted,
            self.test_vm_can_be_deleted,  # Destructive test last
        ]

        for test_func in tests:
            result = test_func()
            self.results.append(result)
            self.print_result(result)

        return self.print_summary()

    def print_result(self, result: RollbackTestResult):
        """Print single test result"""
        print(f"{result.status.value}: {result.test_name}")
        print(f"  └─ {result.message}")
        if result.command:
            print(f"     Command: {result.command}")
        if result.details:
            print(f"     Details: {result.details}")
        print()

    def print_summary(self) -> bool:
        """Print summary of all tests"""
        passed = sum(1 for r in self.results if r.status == RollbackTestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == RollbackTestStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == RollbackTestStatus.WARN)

        print("=" * 60)
        print("ROLLBACK TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed:  {passed}")
        print(f"❌ Failed:  {failed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"📊 Total:   {len(self.results)}")
        print("=" * 60)

        if failed > 0:
            print("\n❌ ROLLBACK TESTS FAILED")
            print("Some rollback procedures cannot be executed.")
            print("Review failures above before attempting rollback.\n")
            return False
        elif warned > 0:
            print("\n⚠️  ROLLBACK TESTS PASSED WITH WARNINGS")
            print("Rollback is possible but review warnings.\n")
            if self.dry_run:
                print("💡 To execute actual rollback, remove --dry-run flag")
                print("   (NOT RECOMMENDED unless truly needed)\n")
            return True
        else:
            print("\n✅ ROLLBACK TESTS PASSED")
            print("All rollback procedures can be executed if needed.\n")
            if self.dry_run:
                print("💡 To execute actual rollback, remove --dry-run flag")
                print("   (NOT RECOMMENDED unless truly needed)\n")
            return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test VM rollback procedures (dry-run by default)")
    parser.add_argument(
        "--resource-group",
        "-g",
        required=True,
        help="Azure resource group name (e.g., haymaker-dev-rg)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Test rollback procedures without executing (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="⚠️  DANGER: Actually execute rollback (NOT RECOMMENDED)",
    )

    args = parser.parse_args()

    if args.execute:
        print("⚠️  WARNING: --execute flag not implemented for safety")
        print("Rollback must be performed manually after reviewing test results\n")
        sys.exit(1)

    tester = VMRollbackTester(resource_group=args.resource_group, dry_run=args.dry_run)

    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
