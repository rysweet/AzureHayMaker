"""RBAC role assignment management for Service Principals.

This module handles role assignments and custom RBAC role definitions
for Azure HayMaker service principals.

Philosophy:
- Single responsibility: RBAC operations only
- Minimal permissions (avoid User Access Administrator)
- Self-contained role definitions
"""

import asyncio
import logging
import uuid

from azure.mgmt.authorization import AuthorizationManagementClient

from azure_haymaker.exceptions import ServicePrincipalError

logger = logging.getLogger(__name__)

# Built-in Azure role definition IDs (consistent across all subscriptions)
ROLE_DEFINITIONS = {
    "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
    "Reader": "acdd72a7-3385-48ef-bd42-f606fba81ae7",
    "Custom RBAC Agent": "CUSTOM_RBAC_AGENT_ROLE_ID",  # Custom role - must be created in subscription
}

# Custom RBAC role definition for HayMaker scenario agents
# This role provides minimal required permissions for scenario execution
# and avoids the over-privileged User Access Administrator role
CUSTOM_RBAC_ROLE_DEFINITION = {
    "roleName": "AzureHayMaker-Agent-Role",
    "description": "Custom role for Azure HayMaker scenario execution with minimal permissions",
    "permissions": [
        {
            "actions": [
                "Microsoft.Resources/subscriptions/resourceGroups/read",
                "Microsoft.Compute/virtualMachines/read",
                "Microsoft.Network/virtualNetworks/read",
                "Microsoft.Network/networkInterfaces/read",
                "Microsoft.Storage/storageAccounts/read",
                "Microsoft.KeyVault/vaults/read",
                "Microsoft.ContainerRegistry/registries/read",
                "Microsoft.ServiceBus/namespaces/read",
            ],
            "notActions": [],
            "dataActions": [
                "Microsoft.KeyVault/vaults/secrets/getSecret/action",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
            ],
            "notDataActions": [],
        }
    ],
    "assignableScopes": ["/subscriptions/{subscription_id}"],
}

# Role propagation wait time (seconds) - Azure RBAC eventual consistency
ROLE_PROPAGATION_WAIT = 60


async def assign_roles(
    principal_id: str,
    subscription_id: str,
    roles: list[str],
    credential,
) -> None:
    """Assign RBAC roles to a service principal.

    Args:
        principal_id: Object ID of the service principal
        subscription_id: Azure subscription ID for role assignments
        roles: List of role names to assign (e.g., ["Contributor", "Reader"])
        credential: Azure credential for authorization client

    Raises:
        ServicePrincipalError: If role assignment fails
    """
    try:
        auth_client = AuthorizationManagementClient(
            credential=credential,
            subscription_id=subscription_id,
        )

        for role_name in roles:
            role_definition_id = ROLE_DEFINITIONS.get(role_name)
            if not role_definition_id:
                raise ServicePrincipalError(f"Unknown role: {role_name}")

            # Create role assignment
            role_assignment_name = str(uuid.uuid4())
            scope = f"/subscriptions/{subscription_id}"
            role_definition_id_full = (
                f"{scope}/providers/Microsoft.Authorization/roleDefinitions/{role_definition_id}"
            )

            await asyncio.to_thread(
                auth_client.role_assignments.create,
                scope=scope,
                role_assignment_name=role_assignment_name,
                parameters={
                    "properties": {
                        "roleDefinitionId": role_definition_id_full,
                        "principalId": principal_id,
                        "principalType": "ServicePrincipal",
                    }
                },
            )

        # Wait for role propagation (Azure RBAC eventual consistency)
        await asyncio.sleep(ROLE_PROPAGATION_WAIT)

    except ServicePrincipalError:
        raise
    except Exception as e:
        raise ServicePrincipalError(f"Failed to assign roles: {e}") from e


__all__ = [
    "CUSTOM_RBAC_ROLE_DEFINITION",
    "ROLE_DEFINITIONS",
    "ROLE_PROPAGATION_WAIT",
    "assign_roles",
]
