#!/usr/bin/env python3
"""
VM Deployment Validation Script

Tests that VM deployment succeeded and all resources are configured correctly.
Run after deployment to verify infrastructure state.

Usage:
    python scripts/validate_vm_deployment.py --resource-group haymaker-dev-rg
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum


class ValidationStatus(Enum):
    """Validation result status"""

    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    SKIP = "⏭️  SKIP"


@dataclass
class ValidationResult:
    """Single validation check result"""

    check_name: str
    status: ValidationStatus
    message: str
    details: str | None = None


class VMDeploymentValidator:
    """Validates VM deployment success and configuration"""

    def __init__(self, resource_group: str, vm_name_pattern: str = "haymaker-*-vm"):
        self.resource_group = resource_group
        self.vm_name_pattern = vm_name_pattern
        self.results: list[ValidationResult] = []

    def run_az_command(self, cmd: list[str]) -> tuple[int, str, str]:
        """Execute Azure CLI command safely"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "command timeout after 30 seconds"
        except Exception as e:
            return 1, "", str(e)

    def validate_vm_exists(self) -> ValidationResult:
        """Verify VM resource exists"""
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            f"[?contains(name, '{self.vm_name_pattern.replace('*', '')}')].name",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="VM Exists",
                status=ValidationStatus.FAIL,
                message="Failed to query VM",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return ValidationResult(
                    check_name="VM Exists",
                    status=ValidationStatus.FAIL,
                    message=f"No VM found matching pattern: {self.vm_name_pattern}",
                )

            return ValidationResult(
                check_name="VM Exists",
                status=ValidationStatus.PASS,
                message=f"VM found: {vms[0]}",
            )
        except json.JSONDecodeError:
            return ValidationResult(
                check_name="VM Exists",
                status=ValidationStatus.FAIL,
                message="Invalid JSON response from Azure CLI",
                details=stdout,
            )

    def validate_vm_size(self) -> ValidationResult:
        """Verify VM is correct size (128GB - Standard_E16s_v3)"""
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[].{name:name, size:hardwareProfile.vmSize}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="VM Size",
                status=ValidationStatus.FAIL,
                message="Failed to query VM size",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return ValidationResult(
                    check_name="VM Size",
                    status=ValidationStatus.SKIP,
                    message="No VM to check",
                )

            # Handle both query formats
            vm_data = vms[0]
            if "size" in vm_data:
                vm_size = vm_data["size"]
            elif "hardwareProfile" in vm_data:
                vm_size = vm_data["hardwareProfile"]["vmSize"]
            else:
                raise KeyError("Neither 'size' nor 'hardwareProfile' found")

            expected_size = "Standard_E16s_v3"

            if vm_size == expected_size:
                return ValidationResult(
                    check_name="VM Size",
                    status=ValidationStatus.PASS,
                    message=f"VM size correct: {vm_size} (128GB RAM)",
                )
            else:
                return ValidationResult(
                    check_name="VM Size",
                    status=ValidationStatus.FAIL,
                    message=f"VM size incorrect: {vm_size} (expected {expected_size})",
                )
        except (json.JSONDecodeError, KeyError) as e:
            return ValidationResult(
                check_name="VM Size",
                status=ValidationStatus.FAIL,
                message="Failed to parse VM size",
                details=str(e),
            )

    def validate_vm_running(self) -> ValidationResult:
        """Verify VM is running"""
        cmd = [
            "az",
            "vm",
            "get-instance-view",
            "--resource-group",
            self.resource_group,
            "--query",
            "[].{name:name, powerState:instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="VM Running",
                status=ValidationStatus.FAIL,
                message="Failed to query VM power state",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return ValidationResult(
                    check_name="VM Running",
                    status=ValidationStatus.SKIP,
                    message="No VM to check",
                )

            vm_data = vms[0]

            # Try to get power state from instanceView.statuses
            if "instanceView" in vm_data:
                statuses = vm_data["instanceView"].get("statuses", [])
                power_state = None
                for status in statuses:
                    if status.get("code", "").startswith("PowerState/"):
                        power_state = status.get("displayStatus", "")
                        break

                if not power_state:
                    return ValidationResult(
                        check_name="VM Running",
                        status=ValidationStatus.WARN,
                        message="Could not determine VM power state",
                    )

                if "running" in power_state.lower():
                    return ValidationResult(
                        check_name="VM Running",
                        status=ValidationStatus.PASS,
                        message=f"VM is running: {power_state}",
                    )
                else:
                    return ValidationResult(
                        check_name="VM Running",
                        status=ValidationStatus.FAIL,
                        message=f"VM not running: {power_state}",
                    )

            # Fallback for query format that returns powerState directly
            power_states = vm_data.get("powerState", [])
            if not power_states:
                return ValidationResult(
                    check_name="VM Running",
                    status=ValidationStatus.WARN,
                    message="Could not determine VM power state",
                )

            power_state = power_states[0]
            if "running" in power_state.lower():
                return ValidationResult(
                    check_name="VM Running",
                    status=ValidationStatus.PASS,
                    message=f"VM is running: {power_state}",
                )
            else:
                return ValidationResult(
                    check_name="VM Running",
                    status=ValidationStatus.FAIL,
                    message=f"VM not running: {power_state}",
                )
        except (json.JSONDecodeError, KeyError) as e:
            return ValidationResult(
                check_name="VM Running",
                status=ValidationStatus.FAIL,
                message="Failed to parse VM power state",
                details=str(e),
            )

    def validate_managed_identity(self) -> ValidationResult:
        """Verify VM has system-assigned managed identity"""
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[].{name:name, identityType:identity.type, principalId:identity.principalId}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="Managed Identity",
                status=ValidationStatus.FAIL,
                message="Failed to query VM identity",
                details=stderr,
            )

        try:
            vms = json.loads(stdout)
            if not vms:
                return ValidationResult(
                    check_name="Managed Identity",
                    status=ValidationStatus.SKIP,
                    message="No VM to check",
                )

            vm_data = vms[0]

            # Handle both query formats
            if "identity" in vm_data:
                identity = vm_data["identity"]
                identity_type = identity.get("type")
                principal_id = identity.get("principalId")
            else:
                identity_type = vm_data.get("identityType")
                principal_id = vm_data.get("principalId")

            if identity_type == "SystemAssigned" and principal_id:
                return ValidationResult(
                    check_name="Managed Identity",
                    status=ValidationStatus.PASS,
                    message=f"System-assigned identity configured: {principal_id}",
                )
            else:
                return ValidationResult(
                    check_name="Managed Identity",
                    status=ValidationStatus.FAIL,
                    message=f"Managed identity missing or incorrect: {identity_type}",
                )
        except (json.JSONDecodeError, KeyError) as e:
            return ValidationResult(
                check_name="Managed Identity",
                status=ValidationStatus.FAIL,
                message="Failed to parse VM identity",
                details=str(e),
            )

    def validate_key_vault_access(self) -> ValidationResult:
        """Verify VM has access to Key Vault"""
        # First get VM principal ID
        cmd = [
            "az",
            "vm",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[0].identity.principalId",
            "-o",
            "tsv",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0 or not stdout.strip():
            return ValidationResult(
                check_name="Key Vault Access",
                status=ValidationStatus.SKIP,
                message="Could not get VM principal ID",
                details=stderr,
            )

        principal_id = stdout.strip()

        # Check role assignments
        cmd = [
            "az",
            "role",
            "assignment",
            "list",
            "--assignee",
            principal_id,
            "--query",
            "[?contains(roleDefinitionName, 'Key Vault')].roleDefinitionName",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="Key Vault Access",
                status=ValidationStatus.FAIL,
                message="Failed to query role assignments",
                details=stderr,
            )

        try:
            roles = json.loads(stdout)
            if roles:
                return ValidationResult(
                    check_name="Key Vault Access",
                    status=ValidationStatus.PASS,
                    message=f"Key Vault roles assigned: {', '.join(roles)}",
                )
            else:
                return ValidationResult(
                    check_name="Key Vault Access",
                    status=ValidationStatus.WARN,
                    message="No Key Vault roles found (may still be propagating)",
                )
        except json.JSONDecodeError:
            return ValidationResult(
                check_name="Key Vault Access",
                status=ValidationStatus.FAIL,
                message="Failed to parse role assignments",
                details=stdout,
            )

    def validate_network_security(self) -> ValidationResult:
        """Verify NSG allows SSH and HTTPS"""
        cmd = [
            "az",
            "network",
            "nsg",
            "list",
            "--resource-group",
            self.resource_group,
            "--query",
            "[?contains(name, 'vm')].{name:name, rules:securityRules[].{name:name, port:destinationPortRange, access:access}}",
            "-o",
            "json",
        ]

        returncode, stdout, stderr = self.run_az_command(cmd)

        if returncode != 0:
            return ValidationResult(
                check_name="Network Security",
                status=ValidationStatus.FAIL,
                message="Failed to query NSG rules",
                details=stderr,
            )

        try:
            nsgs = json.loads(stdout)
            if not nsgs:
                return ValidationResult(
                    check_name="Network Security",
                    status=ValidationStatus.WARN,
                    message="No NSG found for VM",
                )

            nsg = nsgs[0]

            # Handle both query formats
            if "rules" in nsg:
                rules = nsg["rules"]
            elif "securityRules" in nsg:
                rules = nsg["securityRules"]
            else:
                rules = []

            ssh_allowed = any(
                (r.get("port") == "22" or r.get("destinationPortRange") == "22")
                and r.get("access") == "Allow"
                for r in rules
            )
            https_allowed = any(
                (r.get("port") == "443" or r.get("destinationPortRange") == "443")
                and r.get("access") == "Allow"
                for r in rules
            )

            if ssh_allowed and https_allowed:
                return ValidationResult(
                    check_name="Network Security",
                    status=ValidationStatus.PASS,
                    message="NSG allows SSH (22) and HTTPS (443)",
                )
            elif ssh_allowed:
                return ValidationResult(
                    check_name="Network Security",
                    status=ValidationStatus.WARN,
                    message="NSG allows SSH but not HTTPS",
                )
            else:
                return ValidationResult(
                    check_name="Network Security",
                    status=ValidationStatus.FAIL,
                    message="NSG does not allow required ports",
                )
        except (json.JSONDecodeError, KeyError) as e:
            return ValidationResult(
                check_name="Network Security",
                status=ValidationStatus.FAIL,
                message="Failed to parse NSG rules",
                details=str(e),
            )

    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        print("🔍 Starting VM deployment validation...\n")

        validations = [
            self.validate_vm_exists,
            self.validate_vm_size,
            self.validate_vm_running,
            self.validate_managed_identity,
            self.validate_key_vault_access,
            self.validate_network_security,
        ]

        for validation_func in validations:
            result = validation_func()
            self.results.append(result)
            self.print_result(result)

        return self.print_summary()

    def print_result(self, result: ValidationResult):
        """Print single validation result"""
        print(f"{result.status.value}: {result.check_name}")
        print(f"  └─ {result.message}")
        if result.details:
            print(f"     Details: {result.details}")
        print()

    def print_summary(self) -> bool:
        """Print summary of all validations"""
        passed = sum(1 for r in self.results if r.status == ValidationStatus.PASS)
        failed = sum(1 for r in self.results if r.status == ValidationStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == ValidationStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == ValidationStatus.SKIP)

        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"✅ Passed:  {passed}")
        print(f"❌ Failed:  {failed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"📊 Total:   {len(self.results)}")
        print("=" * 60)

        if failed > 0:
            print("\n❌ VALIDATION FAILED")
            print("Some critical checks did not pass.")
            print("Review failures above and fix before proceeding.\n")
            return False
        elif warned > 0:
            print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
            print("Review warnings above - may indicate issues.\n")
            return True
        else:
            print("\n✅ VALIDATION PASSED")
            print("All checks passed successfully!\n")
            return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate VM deployment for Azure HayMaker orchestrator"
    )
    parser.add_argument(
        "--resource-group",
        "-g",
        required=True,
        help="Azure resource group name (e.g., haymaker-dev-rg)",
    )
    parser.add_argument(
        "--vm-pattern",
        default="haymaker-*-vm",
        help="VM name pattern to match (default: haymaker-*-vm)",
    )

    args = parser.parse_args()

    validator = VMDeploymentValidator(
        resource_group=args.resource_group, vm_name_pattern=args.vm_pattern
    )

    success = validator.run_all_validations()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
