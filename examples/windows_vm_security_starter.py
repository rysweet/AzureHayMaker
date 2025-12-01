# STARTER FILE - Template for implementation, not production code

"""Starter code template for Windows VM Security Hardening (Issue #125).

This file shows the BEFORE and AFTER for key security fixes.
See full spec: specs/WINDOWS_VM_SECURITY_HARDENING.md

CRITICAL FIXES NEEDED:
1. Store credentials in Key Vault (not plaintext)
2. Restrict NSG rules (not from ANY IP)
3. Remove public IPs (use Azure Bastion)
4. Enable disk encryption
5. Add JIT VM access

Usage:
    1. Review the BEFORE code (current implementation)
    2. Implement the AFTER code (security fixes)
    3. Write security tests to verify fixes
    4. Run: pytest tests/security/test_windows_vm_security.py -v
"""

import secrets
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient


# ============================================================================
# BEFORE (Current Implementation - INSECURE)
# ============================================================================


class WindowsVMManager_BEFORE:
    """INSECURE implementation (from PR #121).

    Issues:
    1. Returns plaintext password in dict
    2. NSG allows RDP from ANY IP
    3. Public IP assigned to all VMs
    4. No disk encryption
    5. No JIT access
    """

    async def provision_vm_INSECURE(self, worker_id: str) -> tuple[str, dict]:
        """INSECURE: Provisions VM with security issues."""

        # ISSUE #1: Plaintext password returned (may be logged)
        password = secrets.token_urlsafe(24)

        # ISSUE #2: NSG allows RDP from ANY IP
        nsg_rules = [
            {
                "name": "Allow-RDP",
                "protocol": "Tcp",
                "source_address_prefix": "*",  # ⚠️ INSECURE: ANY IP
                "destination_port_range": "3389",
                "access": "Allow",
            }
        ]

        # ISSUE #3: Public IP assigned
        public_ip_config = {
            "location": "eastus",
            "sku": {"name": "Standard"},
            # ⚠️ INSECURE: Public IP on VM
        }

        # ISSUE #4: No disk encryption specified
        vm_config = {
            "location": "eastus",
            "hardware_profile": {"vm_size": "Standard_D2s_v3"},
            "storage_profile": {
                "image_reference": {
                    "publisher": "MicrosoftWindowsServer",
                    "offer": "WindowsServer",
                    "sku": "2022-datacenter",
                    "version": "latest",
                }
                # ⚠️ INSECURE: No encryption configuration
            },
        }

        vm_id = f"vm-{worker_id}"

        # ISSUE #1: Password returned in plaintext
        return vm_id, {
            "vm_id": vm_id,
            "admin_username": "azureuser",
            "admin_password": password,  # ⚠️ INSECURE: Plaintext password
        }


# ============================================================================
# AFTER (Security-Hardened Implementation - SECURE)
# ============================================================================


class WindowsVMManager_SECURE:
    """SECURE implementation addressing all security issues."""

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        keyvault_name: str,
        bastion_subnet_id: str,
    ):
        """Initialize secure Windows VM manager.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            keyvault_name: Key Vault name for secrets
            bastion_subnet_id: Azure Bastion subnet ID (e.g., /subscriptions/.../subnets/AzureBastionSubnet)
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.keyvault_name = keyvault_name
        self.bastion_subnet_id = bastion_subnet_id

        # Initialize clients
        credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.network_client = NetworkManagementClient(credential, subscription_id)
        vault_url = f"https://{keyvault_name}.vault.azure.net"
        self.keyvault_client = SecretClient(vault_url, credential)

    async def provision_vm_SECURE(self, worker_id: str) -> tuple[str, dict]:
        """SECURE: Provisions VM with all security controls.

        Returns:
            Tuple of (vm_id, vm_info_dict)
            - vm_info_dict contains Key Vault reference (NOT plaintext password)
        """

        # FIX #1: Store password in Key Vault immediately
        password = secrets.token_urlsafe(32)  # Increased from 24 to 32 chars
        secret_name = f"vm-{worker_id}-admin-password"

        # Store in Key Vault (async in production, shown sync for clarity)
        self.keyvault_client.set_secret(secret_name, password)

        # FIX #2: Restrict NSG to Bastion subnet only
        nsg_rules = [
            {
                "name": "Allow-RDP-From-Bastion-Only",
                "protocol": "Tcp",
                "source_address_prefix": "10.0.1.0/24",  # ✅ SECURE: Bastion subnet only
                "destination_port_range": "3389",
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 100,
                "direction": "Inbound",
            },
            {
                "name": "Deny-RDP-From-Internet",
                "protocol": "Tcp",
                "source_address_prefix": "Internet",  # ✅ SECURE: Explicit deny
                "destination_port_range": "3389",
                "access": "Deny",
                "priority": 200,
                "direction": "Inbound",
            },
        ]

        # FIX #3: NO public IP (access via Azure Bastion only)
        # public_ip_config = None  # ✅ SECURE: No public IP

        # Network interface without public IP
        nic_config = {
            "location": "eastus",
            "ip_configurations": [
                {
                    "name": "ipconfig1",
                    "subnet": {"id": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Network/virtualNetworks/haymaker-vnet/subnets/vm-subnet"},
                    # No public_ip_address property ✅ SECURE
                }
            ],
        }

        # FIX #4: Enable disk encryption
        vm_config = {
            "location": "eastus",
            "hardware_profile": {"vm_size": "Standard_D2s_v3"},
            "storage_profile": {
                "image_reference": {
                    "publisher": "MicrosoftWindowsServer",
                    "offer": "WindowsServer",
                    "sku": "2022-datacenter",
                    "version": "latest",
                },
                "os_disk": {
                    "create_option": "FromImage",
                    "managed_disk": {
                        "storage_account_type": "Premium_LRS",
                        "security_profile": {  # ✅ SECURE: Encryption enabled
                            "security_encryption_type": "DiskWithVMGuestState",
                        },
                    },
                },
            },
            "os_profile": {
                "computer_name": f"vm-{worker_id[:8]}",
                "admin_username": "azureuser",
                "admin_password": password,  # Used for initial creation only
                "windows_configuration": {
                    "enable_automatic_updates": True,
                    "patch_settings": {"patch_mode": "AutomaticByPlatform"},
                },
            },
        }

        # FIX #5: Configure JIT VM access (separate API call after VM creation)
        jit_policy = {
            "kind": "Basic",
            "properties": {
                "virtual_machines": [
                    {
                        "id": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Compute/virtualMachines/vm-{worker_id}",
                        "ports": [
                            {
                                "number": 3389,
                                "protocol": "TCP",
                                "max_request_access_duration": "PT4H",  # 4 hours
                            }
                        ],
                    }
                ],
            },
        }

        # TODO: Create NSG with secure rules
        # TODO: Create NIC without public IP
        # TODO: Create VM with encryption
        # TODO: Enable JIT access policy

        vm_id = f"vm-{worker_id}"

        # FIX #1: Return Key Vault reference, NOT plaintext password
        return vm_id, {
            "vm_id": vm_id,
            "admin_username": "azureuser",
            "password_secret_uri": f"https://{self.keyvault_name}.vault.azure.net/secrets/{secret_name}",  # ✅ SECURE
            "access_method": "azure_bastion",  # ✅ SECURE: No RDP over internet
            "encryption_enabled": True,  # ✅ SECURE
            "jit_enabled": True,  # ✅ SECURE
        }


# ============================================================================
# Testing Examples
# ============================================================================


async def test_password_not_in_logs():
    """Security test: Verify password never appears in logs.

    TODO: Implement test that:
    1. Provisions VM
    2. Captures all log output
    3. Asserts password does NOT appear in logs
    4. Asserts only Key Vault URI returned
    """
    pass


async def test_nsg_rules_restricted():
    """Security test: Verify NSG blocks internet RDP.

    TODO: Implement test that:
    1. Provisions VM with secure NSG
    2. Queries NSG rules
    3. Asserts no rule allows source "*" or "Internet" for port 3389
    4. Asserts Bastion subnet rule exists
    """
    pass


async def test_no_public_ip_assigned():
    """Security test: Verify no public IP on VM.

    TODO: Implement test that:
    1. Provisions VM
    2. Queries NIC configuration
    3. Asserts ip_configurations[0].public_ip_address is None
    """
    pass


async def test_disk_encryption_enabled():
    """Security test: Verify disk encryption.

    TODO: Implement test that:
    1. Provisions VM
    2. Queries VM disk configuration
    3. Asserts encryption enabled on OS disk
    """
    pass


# ============================================================================
# Integration Example
# ============================================================================


async def provision_secure_vm_example():
    """Example: Provision secure VM with all fixes.

    This shows how the secure implementation integrates with
    existing Knowledge Worker framework.
    """

    manager = WindowsVMManager_SECURE(
        subscription_id="YOUR_SUBSCRIPTION_ID",
        resource_group="haymaker-dev-rg",
        keyvault_name="haymaker-kv",
        bastion_subnet_id="/subscriptions/.../subnets/AzureBastionSubnet",
    )

    worker_id = "worker-001"

    # Provision VM (all security controls applied)
    vm_id, vm_info = await manager.provision_vm_SECURE(worker_id)

    print(f"✅ Secure VM provisioned: {vm_id}")
    print(f"✅ Password stored in Key Vault: {vm_info['password_secret_uri']}")
    print(f"✅ Access via Azure Bastion: {vm_info['access_method']}")
    print(f"✅ Disk encryption enabled: {vm_info['encryption_enabled']}")
    print(f"✅ JIT access enabled: {vm_info['jit_enabled']}")

    # Password is NEVER in logs, only Key Vault reference
    # NSG blocks internet, allows Bastion only
    # No public IP means no attack surface from internet
    # Encrypted disks protect data at rest
    # JIT access limits attack window to 4-hour requests


if __name__ == "__main__":
    import asyncio

    # Run example
    # asyncio.run(provision_secure_vm_example())

    print("Starter template for Issue #125: Windows VM Security Hardening")
    print("See specs/WINDOWS_VM_SECURITY_HARDENING.md for full specification")
