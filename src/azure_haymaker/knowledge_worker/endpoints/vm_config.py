"""VM configuration models, constants, and validation logic.

Provides configuration models and validation for Azure Windows VM management:
- Azure region validation
- Resource naming and validation
- VM configuration constants
- Computer name generation

This module contains NO Azure SDK dependencies - only validation logic
and configuration management.

Philosophy:
- Single responsibility: Configuration and validation only
- Standard library dependencies only
- Self-contained and regeneratable
"""

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

# VM Configuration Constants
DEFAULT_VM_SIZE = "Standard_D2s_v3"
DEFAULT_IMAGE_PUBLISHER = "MicrosoftWindowsServer"
DEFAULT_IMAGE_OFFER = "WindowsServer"
DEFAULT_IMAGE_SKU = "2022-datacenter-azure-edition"
DEFAULT_IMAGE_VERSION = "latest"
PROVISIONING_TIMEOUT_MINUTES = 15
PROVISIONING_CHECK_INTERVAL_SECONDS = 30
RDP_PORT = 3389

# Valid Azure regions (subset for validation)
VALID_AZURE_REGIONS = {
    "eastus",
    "eastus2",
    "westus",
    "westus2",
    "westus3",
    "centralus",
    "northcentralus",
    "southcentralus",
    "westcentralus",
    "canadacentral",
    "canadaeast",
    "brazilsouth",
    "northeurope",
    "westeurope",
    "uksouth",
    "ukwest",
    "francecentral",
    "germanywestcentral",
    "norwayeast",
    "switzerlandnorth",
    "swedencentral",
    "eastasia",
    "southeastasia",
    "australiaeast",
    "australiasoutheast",
    "japaneast",
    "japanwest",
    "koreacentral",
    "koreasouth",
    "southindia",
    "centralindia",
    "westindia",
    "uaenorth",
    "southafricanorth",
    "qatarcentral",
}


class AzureRegionValidator:
    """Validates Azure region names against known regions."""

    @staticmethod
    def validate(location: str) -> None:
        """Validate Azure region.

        Args:
            location: Azure region to validate

        Raises:
            ValueError: If location is invalid
        """
        if not location or not isinstance(location, str):
            raise ValueError("location must be a non-empty string")

        location_lower = location.lower()
        if location_lower not in VALID_AZURE_REGIONS:
            raise ValueError(
                f"Invalid Azure region: '{location}'. "
                f"Must be one of: {', '.join(sorted(VALID_AZURE_REGIONS))}"
            )


class ResourceValidator:
    """Validates Azure resource names and IDs."""

    @staticmethod
    def validate_resource_group(resource_group_name: str) -> None:
        """Validate resource group name.

        Azure resource group names must:
        - Be 1-90 characters
        - Contain only alphanumerics, underscores, hyphens, periods, parentheses
        - Not end with a period

        Args:
            resource_group_name: Resource group name to validate

        Raises:
            ValueError: If resource group name is invalid
        """
        if not resource_group_name or not isinstance(resource_group_name, str):
            raise ValueError("resource_group_name must be a non-empty string")

        if len(resource_group_name) > 90:
            raise ValueError(
                f"resource_group_name too long: {len(resource_group_name)} chars (max 90)"
            )

        if resource_group_name.endswith("."):
            raise ValueError("resource_group_name cannot end with a period")

        # Allow alphanumeric, underscore, hyphen, period, parentheses
        if not re.match(r"^[a-zA-Z0-9_\-\.\(\)]+$", resource_group_name):
            raise ValueError(
                f"Invalid resource_group_name: '{resource_group_name}'. "
                "Must contain only alphanumerics, underscores, hyphens, periods, and parentheses"
            )

    @staticmethod
    def validate_vnet_id(vnet_id: str) -> None:
        """Validate Virtual Network subnet ID.

        VNet subnet IDs must be full Azure Resource IDs in the format:
        /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}

        Args:
            vnet_id: Virtual Network subnet resource ID to validate

        Raises:
            ValueError: If vnet_id is invalid or missing
        """
        if not vnet_id or not isinstance(vnet_id, str):
            raise ValueError(
                "vnet_id is required and must be a non-empty string. "
                "Provide the full Azure Resource ID of the subnet: "
                "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/{subnet}"
            )

        # Validate format - must contain all required components
        required_parts = [
            "/subscriptions/",
            "/resourceGroups/",
            "/providers/Microsoft.Network/virtualNetworks/",
            "/subnets/",
        ]

        for part in required_parts:
            if part not in vnet_id:
                raise ValueError(
                    f"Invalid vnet_id format. Missing '{part}'. "
                    f"Expected format: /subscriptions/{{sub}}/resourceGroups/{{rg}}/providers/Microsoft.Network/virtualNetworks/{{vnet}}/subnets/{{subnet}}"
                )

    @staticmethod
    def validate_worker_id(worker_id: str) -> None:
        """Validate worker ID format.

        Worker IDs should be alphanumeric with hyphens and underscores only.

        Args:
            worker_id: Worker ID to validate

        Raises:
            ValueError: If worker ID is invalid
        """
        if not worker_id or not isinstance(worker_id, str):
            raise ValueError("worker_id must be a non-empty string")

        if len(worker_id) > 64:
            raise ValueError(f"worker_id too long: {len(worker_id)} chars (max 64)")

        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_\-]+$", worker_id):
            raise ValueError(
                f"Invalid worker_id: '{worker_id}'. "
                "Must contain only alphanumerics, hyphens, and underscores"
            )


@dataclass
class VMConfig:
    """Configuration for Azure Windows VM deployment.

    Attributes:
        location: Azure region for VM deployment
        resource_group_name: Resource group name
        vnet_id: Full Azure Resource ID of the Virtual Network subnet
        vm_size: Azure VM size (e.g., Standard_D2s_v3)
    """

    location: str
    resource_group_name: str
    vnet_id: str
    vm_size: str = DEFAULT_VM_SIZE

    @staticmethod
    def get_vm_name(worker: "WorkerIdentity", location: str) -> str:
        """Generate VM name following naming convention.

        Args:
            worker: Worker identity
            location: Azure region

        Returns:
            VM name: cua-win-{location}-{worker_id}

        Raises:
            ValueError: If worker_id is invalid
        """
        # Validate worker_id first
        ResourceValidator.validate_worker_id(worker.worker_id)

        # Sanitize worker_id to ensure valid VM name (alphanumeric and hyphens)
        worker_id_safe = worker.worker_id.replace("_", "-")
        return f"cua-win-{location}-{worker_id_safe}"

    @staticmethod
    def get_computer_name(vm_name: str) -> str:
        """Generate unique 15-char computer name using hash.

        Windows computer names are limited to 15 characters. To avoid
        collisions when truncating long VM names, we use a hash-based
        approach that guarantees uniqueness.

        Args:
            vm_name: Full VM name (can be longer than 15 chars)

        Returns:
            Unique computer name (15 chars max)
        """
        # If vm_name is already 15 chars or less, use it directly
        if len(vm_name) <= 15:
            return vm_name

        # Hash the full VM name to get a unique identifier
        # Use first 8 chars of hex digest for uniqueness
        vm_hash = hashlib.sha256(vm_name.encode()).hexdigest()[:8]

        # Take prefix from vm_name (max 6 chars to leave room for hash)
        # Format: {prefix}-{hash} where total is 15 chars (6 + 1 + 8 = 15)
        prefix = vm_name[:6]
        return f"{prefix}-{vm_hash}"


__all__ = [
    "VMConfig",
    "AzureRegionValidator",
    "ResourceValidator",
    "DEFAULT_VM_SIZE",
    "DEFAULT_IMAGE_PUBLISHER",
    "DEFAULT_IMAGE_OFFER",
    "DEFAULT_IMAGE_SKU",
    "DEFAULT_IMAGE_VERSION",
    "PROVISIONING_TIMEOUT_MINUTES",
    "PROVISIONING_CHECK_INTERVAL_SECONDS",
    "RDP_PORT",
    "VALID_AZURE_REGIONS",
]
