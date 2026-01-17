"""
Unit tests for VM deployment validation script

Tests the validation logic without requiring actual Azure resources.
Uses mocking to simulate Azure CLI responses.
"""

import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validate_vm_deployment import (
    ValidationResult,
    ValidationStatus,
    VMDeploymentValidator,
)


@pytest.fixture
def validator():
    """Create validator instance for testing"""
    return VMDeploymentValidator(resource_group="test-rg", vm_name_pattern="test-vm")


@pytest.fixture
def mock_vm_list_response():
    """Mock Azure CLI response for VM list"""
    return json.dumps([{"name": "test-vm", "location": "westus2"}])


@pytest.fixture
def mock_vm_size_response():
    """Mock Azure CLI response for VM size"""
    return json.dumps([{"name": "test-vm", "hardwareProfile": {"vmSize": "Standard_E16s_v3"}}])


@pytest.fixture
def mock_vm_running_response():
    """Mock Azure CLI response for VM running state"""
    return json.dumps(
        [
            {
                "name": "test-vm",
                "instanceView": {
                    "statuses": [
                        {
                            "code": "PowerState/running",
                            "displayStatus": "VM running",
                        }
                    ]
                },
            }
        ]
    )


class TestVMDeploymentValidator:
    """Test suite for VMDeploymentValidator"""

    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert validator.resource_group == "test-rg"
        assert validator.vm_name_pattern == "test-vm"
        assert validator.results == []

    def test_run_az_command_success(self, validator):
        """Test successful Azure CLI command execution"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

            returncode, stdout, stderr = validator.run_az_command(["az", "version"])

            assert returncode == 0
            assert stdout == "success"
            assert stderr == ""

    def test_run_az_command_failure(self, validator):
        """Test failed Azure CLI command execution"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

            returncode, stdout, stderr = validator.run_az_command(["az", "invalid"])

            assert returncode == 1
            assert stdout == ""
            assert stderr == "error"

    def test_run_az_command_timeout(self, validator):
        """Test Azure CLI command timeout"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["az"], timeout=30)

            returncode, stdout, stderr = validator.run_az_command(["az", "slow"])

            assert returncode == 1
            assert stdout == ""
            assert "timeout" in stderr.lower()

    def test_validate_vm_exists_success(self, validator, mock_vm_list_response):
        """Test VM exists validation - success case"""
        with patch.object(validator, "run_az_command", return_value=(0, mock_vm_list_response, "")):
            result = validator.validate_vm_exists()

            assert result.status == ValidationStatus.PASS
            assert "test-vm" in result.message
            assert result.check_name == "VM Exists"

    def test_validate_vm_exists_not_found(self, validator):
        """Test VM exists validation - VM not found"""
        with patch.object(validator, "run_az_command", return_value=(0, "[]", "")):
            result = validator.validate_vm_exists()

            assert result.status == ValidationStatus.FAIL
            assert "no vm found" in result.message.lower()

    def test_validate_vm_exists_cli_error(self, validator):
        """Test VM exists validation - Azure CLI error"""
        with patch.object(validator, "run_az_command", return_value=(1, "", "CLI error")):
            result = validator.validate_vm_exists()

            assert result.status == ValidationStatus.FAIL
            assert "failed to query" in result.message.lower()

    def test_validate_vm_size_correct(self, validator, mock_vm_size_response):
        """Test VM size validation - correct size"""
        with patch.object(validator, "run_az_command", return_value=(0, mock_vm_size_response, "")):
            result = validator.validate_vm_size()

            assert result.status == ValidationStatus.PASS
            assert "Standard_E16s_v3" in result.message
            assert "128GB" in result.message

    def test_validate_vm_size_incorrect(self, validator):
        """Test VM size validation - incorrect size"""
        wrong_size_response = json.dumps(
            [{"name": "test-vm", "hardwareProfile": {"vmSize": "Standard_D2s_v3"}}]
        )

        with patch.object(validator, "run_az_command", return_value=(0, wrong_size_response, "")):
            result = validator.validate_vm_size()

            assert result.status == ValidationStatus.FAIL
            assert "incorrect" in result.message.lower()

    def test_validate_vm_running_success(self, validator, mock_vm_running_response):
        """Test VM running validation - VM is running"""
        with patch.object(
            validator, "run_az_command", return_value=(0, mock_vm_running_response, "")
        ):
            result = validator.validate_vm_running()

            assert result.status == ValidationStatus.PASS
            assert "running" in result.message.lower()

    def test_validate_vm_running_stopped(self, validator):
        """Test VM running validation - VM is stopped"""
        stopped_response = json.dumps(
            [
                {
                    "name": "test-vm",
                    "instanceView": {
                        "statuses": [
                            {
                                "code": "PowerState/stopped",
                                "displayStatus": "VM stopped",
                            }
                        ]
                    },
                }
            ]
        )

        with patch.object(validator, "run_az_command", return_value=(0, stopped_response, "")):
            result = validator.validate_vm_running()

            assert result.status == ValidationStatus.FAIL
            assert "not running" in result.message.lower()

    def test_validate_managed_identity_success(self, validator):
        """Test managed identity validation - identity configured"""
        identity_response = json.dumps(
            [
                {
                    "name": "test-vm",
                    "identity": {
                        "type": "SystemAssigned",
                        "principalId": "test-principal-id",
                    },
                }
            ]
        )

        with patch.object(validator, "run_az_command", return_value=(0, identity_response, "")):
            result = validator.validate_managed_identity()

            assert result.status == ValidationStatus.PASS
            assert "test-principal-id" in result.message

    def test_validate_managed_identity_missing(self, validator):
        """Test managed identity validation - identity not configured"""
        no_identity_response = json.dumps([{"name": "test-vm", "identity": {"type": None}}])

        with patch.object(validator, "run_az_command", return_value=(0, no_identity_response, "")):
            result = validator.validate_managed_identity()

            assert result.status == ValidationStatus.FAIL
            assert "missing" in result.message.lower()

    def test_validate_key_vault_access_success(self, validator):
        """Test Key Vault access validation - roles assigned"""
        principal_response = "test-principal-id"
        roles_response = json.dumps(["Key Vault Secrets User"])

        with patch.object(validator, "run_az_command") as mock_cmd:
            mock_cmd.side_effect = [
                (0, principal_response, ""),
                (0, roles_response, ""),
            ]

            result = validator.validate_key_vault_access()

            assert result.status == ValidationStatus.PASS
            assert "Key Vault" in result.message

    def test_validate_key_vault_access_no_roles(self, validator):
        """Test Key Vault access validation - no roles assigned"""
        principal_response = "test-principal-id"
        no_roles_response = json.dumps([])

        with patch.object(validator, "run_az_command") as mock_cmd:
            mock_cmd.side_effect = [
                (0, principal_response, ""),
                (0, no_roles_response, ""),
            ]

            result = validator.validate_key_vault_access()

            assert result.status == ValidationStatus.WARN
            assert "no key vault roles" in result.message.lower()

    def test_validate_network_security_success(self, validator):
        """Test network security validation - SSH and HTTPS allowed"""
        nsg_response = json.dumps(
            [
                {
                    "name": "test-vm-nsg",
                    "securityRules": [
                        {
                            "name": "AllowSSH",
                            "destinationPortRange": "22",
                            "access": "Allow",
                        },
                        {
                            "name": "AllowHTTPS",
                            "destinationPortRange": "443",
                            "access": "Allow",
                        },
                    ],
                }
            ]
        )

        with patch.object(validator, "run_az_command", return_value=(0, nsg_response, "")):
            result = validator.validate_network_security()

            assert result.status == ValidationStatus.PASS
            assert "SSH" in result.message
            assert "HTTPS" in result.message

    def test_validate_network_security_missing_https(self, validator):
        """Test network security validation - HTTPS not allowed"""
        nsg_response = json.dumps(
            [
                {
                    "name": "test-vm-nsg",
                    "securityRules": [
                        {
                            "name": "AllowSSH",
                            "destinationPortRange": "22",
                            "access": "Allow",
                        }
                    ],
                }
            ]
        )

        with patch.object(validator, "run_az_command", return_value=(0, nsg_response, "")):
            result = validator.validate_network_security()

            assert result.status == ValidationStatus.WARN
            assert "SSH but not HTTPS" in result.message

    def test_print_result(self, validator, capsys):
        """Test result printing"""
        result = ValidationResult(
            check_name="Test Check",
            status=ValidationStatus.PASS,
            message="Test passed",
            details="Additional info",
        )

        validator.print_result(result)
        captured = capsys.readouterr()

        assert "Test Check" in captured.out
        assert "Test passed" in captured.out
        assert "Additional info" in captured.out

    def test_print_summary_all_passed(self, validator, capsys):
        """Test summary printing - all checks passed"""
        validator.results = [
            ValidationResult(check_name="Check 1", status=ValidationStatus.PASS, message="OK"),
            ValidationResult(check_name="Check 2", status=ValidationStatus.PASS, message="OK"),
        ]

        success = validator.print_summary()
        captured = capsys.readouterr()

        assert success is True
        assert "VALIDATION PASSED" in captured.out
        assert "Passed:  2" in captured.out

    def test_print_summary_with_failures(self, validator, capsys):
        """Test summary printing - some checks failed"""
        validator.results = [
            ValidationResult(check_name="Check 1", status=ValidationStatus.PASS, message="OK"),
            ValidationResult(check_name="Check 2", status=ValidationStatus.FAIL, message="Failed"),
        ]

        success = validator.print_summary()
        captured = capsys.readouterr()

        assert success is False
        assert "VALIDATION FAILED" in captured.out
        assert "Failed:  1" in captured.out

    def test_print_summary_with_warnings(self, validator, capsys):
        """Test summary printing - some checks warned"""
        validator.results = [
            ValidationResult(check_name="Check 1", status=ValidationStatus.PASS, message="OK"),
            ValidationResult(check_name="Check 2", status=ValidationStatus.WARN, message="Warning"),
        ]

        success = validator.print_summary()
        captured = capsys.readouterr()

        assert success is True  # Warnings don't fail validation
        assert "PASSED WITH WARNINGS" in captured.out
        assert "Warnings: 1" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
