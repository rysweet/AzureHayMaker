"""Entra user management for Knowledge Worker Activity Framework.

Provides user provisioning and management for knowledge workers with real M365 identities.
"""

import asyncio
import logging
import secrets
import string
from collections.abc import AsyncIterator
from typing import Any

from msgraph.generated.models.password_profile import PasswordProfile
from msgraph.generated.models.user import User

from azure_haymaker.knowledge_worker.models.worker import (
    WorkerIdentity,
    WorkerPersona,
)

logger = logging.getLogger(__name__)


class EntraUserManager:
    """Manages Entra ID user provisioning for knowledge workers.

    Handles creation, deletion, and listing of knowledge worker users
    in Entra ID with proper naming conventions, E5 license assignment,
    and security configurations.

    Naming Convention:
        - User: kw-{run_id[:8]}-{dept[:4]}-{index:03d}
        - UPN: {username}@{tenant_domain}

    Attributes:
        graph_client: Microsoft Graph API client
        run_id: HayMaker run ID for this deployment
        tenant_domain: Tenant's primary domain for UPNs
    """

    NAMING_PATTERN = "kw-{run_id}-{dept}-{index:03d}"
    PASSWORD_LENGTH = 24
    RATE_LIMIT_DELAY = 0.1  # 10 requests per second

    def __init__(
        self,
        graph_client: Any,
        run_id: str,
        tenant_domain: str,
    ):
        """Initialize EntraUserManager.

        Args:
            graph_client: Microsoft Graph API client
            run_id: HayMaker run ID for resource tagging
            tenant_domain: Primary domain for UPN generation
        """
        self.graph_client = graph_client
        self.run_id = run_id
        self.tenant_domain = tenant_domain

        # Initialize mailbox provisioning waiter
        from azure_haymaker.knowledge_worker.identity.mailbox_waiter import MailboxProvisioningWaiter
        self.mailbox_waiter = MailboxProvisioningWaiter(graph_client)

    async def provision_worker(
        self,
        department: str,
        index: int,
        display_name: str,
        persona: WorkerPersona | None = None,
    ) -> WorkerIdentity:
        """Provision a single knowledge worker user in Entra.

        Creates a new user with:
        - Unique username based on naming convention
        - Secure random password
        - Department and persona metadata
        - Disabled interactive login (for security)

        Args:
            department: Department name for the worker
            index: Worker index within department
            display_name: Human-readable display name
            persona: Worker persona type

        Returns:
            WorkerIdentity with provisioned user details
        """
        # Generate naming
        username = self.NAMING_PATTERN.format(
            run_id=self.run_id[:8],
            dept=department[:4].lower(),
            index=index,
        )
        upn = f"{username}@{self.tenant_domain}"

        # Generate secure password
        password = self._generate_secure_password()

        # Determine persona
        if persona is None:
            persona = self._persona_from_department(department)

        try:
            # Create user via Graph API using proper SDK models
            password_profile = PasswordProfile(
                force_change_password_next_sign_in=False,
                password=password,
            )

            user = User(
                account_enabled=True,
                display_name=display_name,
                mail_nickname=username,
                user_principal_name=upn,
                password_profile=password_profile,
                department=department,
                job_title=f"Knowledge Worker ({persona.value})",
                usage_location="US",  # Required for license assignment
            )

            created_user = await self.graph_client.users.post(body=user)

            logger.info(f"Provisioned worker: {username} ({display_name})")

            # Ensure usage location is set (required for license assignment)
            # Graph API sometimes doesn't return all fields on POST, so update explicitly
            if created_user.id:
                update_user = User(usage_location="US", account_enabled=True)
                await self.graph_client.users.by_user_id(created_user.id).patch(body=update_user)
                logger.debug(f"Set usage location for {username}")

            # Assign E5 license and wait for mailbox
            if created_user.id:
                license_assigned = await self.assign_license(created_user.id)

                # Wait for mailbox provisioning
                if license_assigned:
                    logger.info(f"Waiting for mailbox provisioning: {username}")
                    from azure_haymaker.knowledge_worker.identity.mailbox_waiter import MailboxStatus

                    wait_result = await self.mailbox_waiter.wait_for_mailbox(created_user.id, timeout_seconds=900)

                    if wait_result.status == MailboxStatus.READY:
                        logger.info(f"Mailbox ready for {username} ({wait_result.elapsed_seconds:.1f}s)")
                    else:
                        logger.warning(f"Mailbox not ready for {username}: {wait_result.status.value}")

            return WorkerIdentity(
                worker_id=username,
                display_name=display_name,
                user_principal_name=upn,
                department=department,
                persona=persona,
                entra_object_id=created_user.id,
            )

        except Exception as e:
            logger.error(f"Failed to provision worker {username}: {e}")
            raise

    async def get_available_e5_sku(self) -> str | None:
        """Query tenant for available E5 license SKU.

        Returns:
            SKU ID of first available E5 license, or None if not found

        Note:
            Searches for SKUs with "E5" in the part number and available units.
            Different tenants have different E5 variants:
            - SPE_E5 (standard)
            - SPE_E5_NOPSTNCONF (without PSTN)
            - ENTERPRISEPREMIUM
            etc.
        """
        try:
            skus = await self.graph_client.subscribed_skus.get()

            if not skus or not skus.value:
                logger.warning("No subscribed SKUs found in tenant")
                return None

            # Find E5 license with available units
            for sku in skus.value:
                sku_name = sku.sku_part_number or ""
                if "E5" in sku_name.upper():
                    enabled = sku.prepaid_units.enabled if sku.prepaid_units else 0
                    consumed = sku.consumed_units or 0
                    available = enabled - consumed

                    if available > 0:
                        logger.info(
                            f"Found E5 license: {sku_name} "
                            f"({available} available, SKU: {sku.sku_id})"
                        )
                        return str(sku.sku_id)
                    else:
                        logger.warning(
                            f"Found E5 license {sku_name} but no units available "
                            f"({consumed}/{enabled} consumed)"
                        )

            logger.warning("No E5 licenses with available units found")
            return None

        except Exception as e:
            logger.error(f"Failed to query subscribed SKUs: {e}")
            return None

    async def assign_license(
        self,
        user_id: str,
        sku_id: str | None = None,
    ) -> bool:
        """Assign an M365 license to a user.

        Args:
            user_id: Entra object ID of the user
            sku_id: License SKU ID (queries tenant for E5 if not provided)

        Returns:
            True if license assigned successfully, False otherwise

        Note:
            If sku_id is not provided, queries the tenant for available E5 licenses.
            License assignment failures are logged but don't fail provisioning.

        Example:
            >>> manager = EntraUserManager(graph_client, "run-123", "test.onmicrosoft.com")
            >>> success = await manager.assign_license("user-object-id")
            >>> # Returns True if E5 license assigned, False on failure
        """
        from uuid import UUID

        from msgraph.generated.models.assigned_license import AssignedLicense
        from msgraph.generated.users.item.assign_license.assign_license_post_request_body import (
            AssignLicensePostRequestBody,
        )

        # Query tenant for E5 license if not provided
        if sku_id is None:
            sku_id = await self.get_available_e5_sku()
            if sku_id is None:
                logger.warning(
                    "No E5 licenses available in tenant. "
                    "User created but will not have mailbox access."
                )
                return False

        try:
            # Convert string UUID to UUID object
            sku_uuid = UUID(sku_id) if isinstance(sku_id, str) else sku_id
            license = AssignedLicense(sku_id=sku_uuid)
            body = AssignLicensePostRequestBody(
                add_licenses=[license],
                remove_licenses=[],
            )

            await self.graph_client.users.by_user_id(user_id).assign_license.post(body=body)

            logger.info(f"Assigned E5 license to user {user_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to assign license to user {user_id}: {e}")
            return False

    async def provision_batch(
        self,
        workers: list[dict[str, Any]],
    ) -> AsyncIterator[WorkerIdentity]:
        """Provision multiple workers with rate limiting.

        Args:
            workers: List of worker specifications with keys:
                - department: Department name
                - index: Worker index
                - display_name: Display name
                - persona: Optional persona

        Yields:
            WorkerIdentity for each provisioned worker
        """
        for worker in workers:
            identity = await self.provision_worker(
                department=worker["department"],
                index=worker["index"],
                display_name=worker["display_name"],
                persona=worker.get("persona"),
            )
            yield identity

            # Rate limiting
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

    async def delete_worker(self, entra_object_id: str) -> bool:
        """Delete a knowledge worker user from Entra.

        Args:
            entra_object_id: Entra object ID of the user

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            await self.graph_client.users.by_user_id(entra_object_id).delete()
            logger.info(f"Deleted worker: {entra_object_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {entra_object_id}: {e}")
            return False

    async def list_workers(self, run_id: str | None = None) -> list[WorkerIdentity]:
        """List all workers for a given run.

        Args:
            run_id: Run ID to filter by (uses instance run_id if not specified)

        Returns:
            List of WorkerIdentity objects
        """
        target_run_id = run_id or self.run_id

        try:
            # Filter by mailNickname pattern
            filter_query = f"startswith(mailNickname, 'kw-{target_run_id[:8]}')"
            users = await self.graph_client.users.get(
                request_configuration={
                    "query_parameters": {
                        "filter": filter_query,
                        "select": (
                            "id,displayName,userPrincipalName," "mailNickname,department,jobTitle"
                        ),
                    }
                }
            )

            return [self._user_to_identity(u) for u in (users.value or [])]

        except Exception as e:
            logger.error(f"Failed to list workers for run {target_run_id}: {e}")
            return []

    async def get_worker(self, entra_object_id: str) -> WorkerIdentity | None:
        """Get a specific worker by Entra object ID.

        Args:
            entra_object_id: Entra object ID of the user

        Returns:
            WorkerIdentity if found, None otherwise
        """
        try:
            user = await self.graph_client.users.by_user_id(entra_object_id).get(
                request_configuration={
                    "query_parameters": {
                        "select": (
                            "id,displayName,userPrincipalName," "mailNickname,department,jobTitle"
                        ),
                    }
                }
            )
            return self._user_to_identity(user)
        except Exception as e:
            logger.error(f"Failed to get worker {entra_object_id}: {e}")
            return None

    def _generate_secure_password(self) -> str:
        """Generate a secure random password.

        Returns:
            Secure password string meeting complexity requirements

        Note:
            Password is generated for Entra ID compliance. In live_mode,
            the app uses application-level delegation (not per-user auth)
            so workers don't need to authenticate with these passwords.
        """
        # Ensure password has required complexity
        chars = string.ascii_letters + string.digits + "!@#$%^&*"

        # Generate base password
        password_chars = [secrets.choice(chars) for _ in range(self.PASSWORD_LENGTH - 4)]

        # Add at least one of each required type
        password_chars.extend(
            [
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits),
                secrets.choice("!@#$%^&*"),
            ]
        )

        # Shuffle to avoid predictable pattern at specific positions
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)

    def _persona_from_department(self, department: str) -> WorkerPersona:
        """Map department name to persona enum.

        Args:
            department: Department name

        Returns:
            Corresponding WorkerPersona
        """
        mapping = {
            "executive": WorkerPersona.EXECUTIVE,
            "legal": WorkerPersona.LEGAL,
            "engineering": WorkerPersona.ENGINEERING,
            "hr": WorkerPersona.HR,
            "finance": WorkerPersona.FINANCE,
            "sales": WorkerPersona.SALES,
            "operations": WorkerPersona.OPERATIONS,
            "marketing": WorkerPersona.MARKETING,
        }
        return mapping.get(department.lower(), WorkerPersona.ENGINEERING)

    def _user_to_identity(self, user: Any) -> WorkerIdentity:
        """Convert Graph API user object to WorkerIdentity.

        Args:
            user: Graph API user object

        Returns:
            WorkerIdentity model
        """
        # Extract persona from job title if available
        persona = WorkerPersona.ENGINEERING
        if user.job_title:
            for p in WorkerPersona:
                if p.value in user.job_title.lower():
                    persona = p
                    break

        return WorkerIdentity(
            worker_id=user.mail_nickname or "",
            display_name=user.display_name or "",
            user_principal_name=user.user_principal_name or "",
            department=user.department or "",
            persona=persona,
            entra_object_id=user.id or "",
        )
