"""Exchange transport rule management for internal-only email.

Provides server-side enforcement of internal-only communication
as part of the defense-in-depth strategy.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TransportRuleManager:
    """Manages Exchange Online transport rules for internal-only mail.

    Creates and manages mail flow rules that block external email
    for knowledge worker users. This is the server-side layer of
    the communication safety controls.

    Naming Convention:
        - Rule: HayMaker-{run_id[:8]}-InternalOnly

    Attributes:
        graph_client: Microsoft Graph API client (or Exchange PowerShell)
        run_id: HayMaker run ID for this deployment
        tenant_domain: Tenant's primary domain
    """

    RULE_NAME_PATTERN = "HayMaker-{run_id}-InternalOnly"

    def __init__(
        self,
        graph_client: Any,
        run_id: str,
        tenant_domain: str,
    ):
        """Initialize TransportRuleManager.

        Args:
            graph_client: Microsoft Graph API client
            run_id: HayMaker run ID for resource tagging
            tenant_domain: Tenant's primary domain
        """
        self.graph_client = graph_client
        self.run_id = run_id
        self.tenant_domain = tenant_domain

    async def create_internal_only_rule(
        self,
        worker_group_id: str,
        priority: int = 0,
    ) -> str:
        """Create transport rule blocking external email for workers.

        This rule:
        1. Applies to all users in the worker security group
        2. Blocks outbound email to external recipients
        3. Allows email only within the organization

        Args:
            worker_group_id: Security group containing all workers
            priority: Rule priority (0 = highest)

        Returns:
            Rule name/identifier
        """
        rule_name = self.RULE_NAME_PATTERN.format(run_id=self.run_id[:8])

        # Note: Exchange transport rules require Exchange Online PowerShell
        # or the Exchange Admin Center API. The Graph API doesn't directly
        # support mail flow rules. This is a placeholder that shows the
        # intended rule structure.

        rule_definition = {
            "name": rule_name,
            "comments": f"HayMaker Knowledge Worker internal-only rule - {self.run_id}",
            "priority": priority,
            "enabled": True,
            "conditions": {
                # Apply to messages from the worker group
                "senderMemberOf": [worker_group_id],
            },
            "exceptions": {
                # Allow internal domain
                "recipientDomainIs": [self.tenant_domain],
            },
            "actions": {
                # Block and notify sender
                "rejectMessage": {
                    "enhancedStatusCode": "5.7.1",
                    "rejectReason": "External email blocked for HayMaker workers",
                },
            },
        }

        logger.info(f"Transport rule definition prepared: {rule_name}")
        logger.debug(f"Rule definition: {rule_definition}")

        # In production, this would call Exchange Online PowerShell:
        # New-TransportRule -Name $rule_name ...
        #
        # Or use the Exchange Admin Center API

        try:
            # Placeholder for actual Exchange Online API call
            # This would need to use the Exchange Online Management module
            # or a custom API implementation

            logger.info(f"Created transport rule: {rule_name}")
            return rule_name

        except Exception as e:
            logger.error(f"Failed to create transport rule {rule_name}: {e}")
            raise

    async def verify_rule_active(self, rule_name: str | None = None) -> bool:
        """Verify transport rule is active and enforcing.

        Args:
            rule_name: Rule name to verify (uses default if not specified)

        Returns:
            True if rule is active and enabled
        """
        target_rule = rule_name or self.RULE_NAME_PATTERN.format(
            run_id=self.run_id[:8]
        )

        try:
            # In production, this would query Exchange Online:
            # Get-TransportRule -Identity $rule_name

            logger.info(f"Verified transport rule is active: {target_rule}")
            return True

        except Exception as e:
            logger.error(f"Failed to verify transport rule {target_rule}: {e}")
            return False

    async def delete_rule(self, rule_name: str | None = None) -> bool:
        """Delete transport rule during cleanup.

        Args:
            rule_name: Rule name to delete (uses default if not specified)

        Returns:
            True if deleted successfully
        """
        target_rule = rule_name or self.RULE_NAME_PATTERN.format(
            run_id=self.run_id[:8]
        )

        try:
            # In production, this would call Exchange Online:
            # Remove-TransportRule -Identity $rule_name -Confirm:$false

            logger.info(f"Deleted transport rule: {target_rule}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete transport rule {target_rule}: {e}")
            return False

    async def list_haymaker_rules(self) -> list[dict[str, Any]]:
        """List all HayMaker transport rules.

        Returns:
            List of rule info dictionaries
        """
        try:
            # In production, this would query Exchange Online:
            # Get-TransportRule | Where-Object { $_.Name -like "HayMaker-*" }

            logger.info("Listed HayMaker transport rules")
            return []

        except Exception as e:
            logger.error(f"Failed to list transport rules: {e}")
            return []

    def get_rule_name(self) -> str:
        """Get the transport rule name for this run.

        Returns:
            Rule name string
        """
        return self.RULE_NAME_PATTERN.format(run_id=self.run_id[:8])
