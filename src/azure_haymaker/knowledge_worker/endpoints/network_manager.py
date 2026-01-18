"""Azure network resource management for Windows VMs.

Provides network infrastructure management:
- Public IP address creation
- Network Security Group (NSG) creation
- Network Interface (NIC) creation
- Network resource cleanup

This module manages Azure network resources required for Windows VM deployment.

Philosophy:
- Single responsibility: Network resource management only
- Dependency injection for Azure SDK clients
- Self-contained and regeneratable
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NetworkResourceManager:
    """Manages Azure network resources for Windows VMs.

    Handles creation and cleanup of Public IPs, NSGs, and NICs required
    for Windows VM deployment with RDP access.

    Attributes:
        network_client: Azure Network Management client
        subscription_id: Azure subscription ID for resource IDs
    """

    def __init__(self, network_client: Any, subscription_id: str):
        """Initialize NetworkResourceManager.

        Args:
            network_client: Azure Network Management client
            subscription_id: Azure subscription ID
        """
        self.network_client = network_client
        self.subscription_id = subscription_id

    async def create_public_ip(
        self,
        name: str,
        location: str,
        tags: dict[str, str],
        resource_group: str,
    ) -> str:
        """Create a public IP address.

        Args:
            name: Name for the public IP
            location: Azure region
            tags: Resource tags
            resource_group: Resource group name

        Returns:
            Public IP address string
        """
        logger.info(f"Creating public IP: {name}")

        public_ip_params = {
            "location": location,
            "public_ip_allocation_method": "Static",
            "tags": tags,
        }

        # Azure async SDK - await the poller directly
        poller = await self.network_client.public_ip_addresses.begin_create_or_update(
            resource_group_name=resource_group,
            public_ip_address_name=name,
            parameters=public_ip_params,
        )

        public_ip_result = await poller
        ip_address = public_ip_result.ip_address

        logger.info(f"Public IP created: {name} ({ip_address})")
        return ip_address

    async def create_nsg(
        self,
        name: str,
        location: str,
        tags: dict[str, str],
        resource_group: str,
        allowed_ips: list[str],
        rdp_port: int,
    ) -> None:
        """Create Network Security Group with RDP rules.

        Creates NSG rules with one rule per allowed source IP/range.
        All IPs must be explicitly specified (wildcards are rejected).

        Args:
            name: Name for the NSG
            location: Azure region
            tags: Resource tags
            resource_group: Resource group name
            allowed_ips: List of allowed source IP addresses/CIDR ranges
            rdp_port: RDP port number (usually 3389)

        Security Note:
            All source IPs are validated before this method is called.
            Wildcards like '*' or '0.0.0.0/0' are rejected by SecurityValidator.
        """
        logger.info(f"Creating NSG: {name}")

        # Build security rules - one per allowed source IP/range
        security_rules = []

        for idx, source_ip in enumerate(allowed_ips):
            rule = {
                "name": f"AllowRDP-{idx}",
                "protocol": "Tcp",
                "source_port_range": "*",
                "destination_port_range": str(rdp_port),
                "source_address_prefix": source_ip,
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 1000 + idx,  # Increment priority for each rule
                "direction": "Inbound",
            }
            security_rules.append(rule)
            logger.info(f"NSG rule {idx}: Allow RDP from {source_ip}")

        nsg_params = {
            "location": location,
            "security_rules": security_rules,
            "tags": tags,
        }

        try:
            poller = await self.network_client.network_security_groups.begin_create_or_update(
                resource_group_name=resource_group,
                network_security_group_name=name,
                parameters=nsg_params,
            )

            await poller
            logger.info(f"NSG created: {name} with {len(security_rules)} rule(s)")

        except Exception as e:
            logger.error(
                f"Failed to create NSG {name}: {type(e).__name__}",
                exc_info=True,  # Full details in debug logs only
            )
            raise

    async def create_nic(
        self,
        name: str,
        location: str,
        tags: dict[str, str],
        resource_group: str,
        subnet_id: str,
        public_ip_name: str,
        nsg_name: str,
    ) -> str:
        """Create Network Interface with Public IP and NSG.

        Args:
            name: Name for the NIC
            location: Azure region
            tags: Resource tags
            resource_group: Resource group name
            subnet_id: Full subnet resource ID
            public_ip_name: Name of the public IP to associate
            nsg_name: Name of the NSG to associate

        Returns:
            NIC resource ID
        """
        logger.info(f"Creating NIC: {name}")

        # Build resource IDs
        public_ip_id = (
            f"/subscriptions/{self.subscription_id}/"
            f"resourceGroups/{resource_group}/"
            f"providers/Microsoft.Network/publicIPAddresses/{public_ip_name}"
        )
        nsg_id = (
            f"/subscriptions/{self.subscription_id}/"
            f"resourceGroups/{resource_group}/"
            f"providers/Microsoft.Network/networkSecurityGroups/{nsg_name}"
        )

        nic_params = {
            "location": location,
            "ip_configurations": [
                {
                    "name": "ipconfig1",
                    "subnet": {"id": subnet_id},
                    "public_ip_address": {"id": public_ip_id},
                }
            ],
            "network_security_group": {"id": nsg_id},
            "tags": tags,
        }

        poller = await self.network_client.network_interfaces.begin_create_or_update(
            resource_group_name=resource_group,
            network_interface_name=name,
            parameters=nic_params,
        )

        nic_result = await poller
        logger.info(f"NIC created: {name}")
        return nic_result.id

    async def cleanup_network_resources(
        self,
        vm_name: str,
        resource_group: str,
    ) -> None:
        """Clean up network resources associated with a VM.

        Args:
            vm_name: VM name whose resources to clean up
            resource_group: Resource group name
        """
        nic_name = f"{vm_name}-nic"
        public_ip_name = f"{vm_name}-ip"
        nsg_name = f"{vm_name}-nsg"

        # Delete NIC
        await self._delete_nic(nic_name, resource_group)

        # Delete Public IP
        await self._delete_public_ip(public_ip_name, resource_group)

        # Delete NSG
        await self._delete_nsg(nsg_name, resource_group)

    async def _delete_nic(self, nic_name: str, resource_group: str) -> None:
        """Delete Network Interface.

        Args:
            nic_name: NIC name to delete
            resource_group: Resource group name
        """
        try:
            poller = await self.network_client.network_interfaces.begin_delete(
                resource_group_name=resource_group,
                network_interface_name=nic_name,
            )
            await poller
            logger.info(f"NIC deleted: {nic_name}")
        except Exception as e:
            logger.info(f"NIC cleanup skipped ({nic_name}): {e}")

    async def _delete_public_ip(self, public_ip_name: str, resource_group: str) -> None:
        """Delete Public IP address.

        Args:
            public_ip_name: Public IP name to delete
            resource_group: Resource group name
        """
        try:
            poller = await self.network_client.public_ip_addresses.begin_delete(
                resource_group_name=resource_group,
                public_ip_address_name=public_ip_name,
            )
            await poller
            logger.info(f"Public IP deleted: {public_ip_name}")
        except Exception as e:
            logger.info(f"Public IP cleanup skipped ({public_ip_name}): {e}")

    async def _delete_nsg(self, nsg_name: str, resource_group: str) -> None:
        """Delete Network Security Group.

        Args:
            nsg_name: NSG name to delete
            resource_group: Resource group name
        """
        try:
            poller = await self.network_client.network_security_groups.begin_delete(
                resource_group_name=resource_group,
                network_security_group_name=nsg_name,
            )
            await poller
            logger.info(f"NSG deleted: {nsg_name}")
        except Exception as e:
            logger.info(f"NSG cleanup skipped ({nsg_name}): {e}")


__all__ = ["NetworkResourceManager"]
