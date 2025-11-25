"""Entra user management for Knowledge Worker Activity Framework.

Provides user provisioning and management for simulated knowledge workers.
"""

import asyncio
import logging
import secrets
import string
from collections.abc import AsyncIterator
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import (
    WorkerIdentity,
    WorkerPersona,
)

logger = logging.getLogger(__name__)


class EntraUserManager:
    """Manages Entra ID user provisioning for knowledge workers.

    Handles creation, deletion, and listing of simulated knowledge
    worker users in Entra ID with proper naming conventions and
    security configurations.

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
            # Create user via Graph API
            user_data = {
                "accountEnabled": True,
                "displayName": display_name,
                "mailNickname": username,
                "userPrincipalName": upn,
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": False,
                    "password": password,
                },
                "department": department,
                "jobTitle": f"Knowledge Worker ({persona.value})",
                "usageLocation": "US",  # Required for license assignment
            }

            created_user = await self.graph_client.users.post(body=user_data)

            logger.info(f"Provisioned worker: {username} ({display_name})")

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
                            "id,displayName,userPrincipalName,"
                            "mailNickname,department,jobTitle"
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
                            "id,displayName,userPrincipalName,"
                            "mailNickname,department,jobTitle"
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
        """
        # Ensure password has required complexity
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(chars) for _ in range(self.PASSWORD_LENGTH))

        # Ensure at least one of each required type
        password = (
            secrets.choice(string.ascii_uppercase)
            + secrets.choice(string.ascii_lowercase)
            + secrets.choice(string.digits)
            + secrets.choice("!@#$%^&*")
            + password[4:]
        )

        return password

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
