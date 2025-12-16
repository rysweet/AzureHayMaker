"""Document operations for Knowledge Worker Activity Framework.

Provides SharePoint/OneDrive document operations via Microsoft Graph API
with built-in recipient validation for sharing.
"""

import logging
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity
from azure_haymaker.knowledge_worker.operations.base import (
    M365Client,
    M365OperationBase,
)
from azure_haymaker.knowledge_worker.operations.validators import (
    CommunicationValidator,
)

logger = logging.getLogger(__name__)


class DocumentOperations(M365OperationBase):
    """SharePoint/OneDrive document operations.

    Supported operations:
    - Create document (Word, Excel, PowerPoint)
    - Upload file
    - Share with team members (internal only)
    - Download/read document
    - List documents

    All share operations validate recipients against the internal-only
    allowlist before executing.

    Example:
        >>> ops = DocumentOperations(worker, client, validator)
        >>> doc_id = await ops.create_document(
        ...     name="report.docx",
        ...     content=document_bytes,
        ...     folder_path="Documents/Reports",
        ... )
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        validator: CommunicationValidator,
    ):
        """Initialize DocumentOperations.

        Args:
            worker_identity: Identity of the worker performing operations
            m365_client: M365 client for Graph API calls
            validator: Communication validator for recipient checks
        """
        super().__init__(worker_identity, m365_client, validator)

    async def execute(self, **kwargs: Any) -> Any:
        """Execute a document operation.

        Dispatches to the appropriate method based on the 'operation' kwarg.

        Args:
            **kwargs: Must include 'operation' key

        Returns:
            Operation result

        Raises:
            ValueError: If operation is not specified or unknown
        """
        operation = kwargs.pop("operation", None)
        if not operation:
            raise ValueError("operation must be specified")

        if operation == "create":
            return await self.create_document(**kwargs)
        elif operation == "upload":
            return await self.upload_file(**kwargs)
        elif operation == "share":
            return await self.share_with_team(**kwargs)
        elif operation == "download":
            return await self.download_document(**kwargs)
        elif operation == "list":
            return await self.list_documents(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def create_document(
        self,
        name: str,
        content: bytes,
        folder_path: str = "Documents",
        content_type: str | None = None,
    ) -> str | None:
        """Create document in worker's OneDrive.

        Args:
            name: File name including extension
            content: File content as bytes
            folder_path: Path within OneDrive (default: Documents)
            content_type: MIME type (auto-detected from extension if not specified)

        Returns:
            Document ID if created successfully
        """
        await self._rate_limit()

        try:
            # Upload to OneDrive
            result = (
                await self.client.graph.users.by_user_id(self.worker.entra_object_id)
                .drive.root.item_with_path(f"{folder_path}/{name}")
                .content.put(content)
            )

            self._log_operation(
                "document_create",
                {"name": name, "folder": folder_path, "size_bytes": len(content)},
            )

            return result.id if result else None

        except Exception as e:
            self._log_error("document_create", e, {"name": name})
            raise

    async def upload_file(
        self,
        name: str,
        content: bytes,
        folder_path: str = "Documents",
    ) -> str | None:
        """Upload file to worker's OneDrive.

        Alias for create_document for semantic clarity.

        Args:
            name: File name including extension
            content: File content as bytes
            folder_path: Path within OneDrive

        Returns:
            Document ID if uploaded successfully
        """
        return await self.create_document(name, content, folder_path)

    async def share_with_team(
        self,
        item_id: str,
        team_members: list[str],
        permission: str = "read",
        send_invitation: bool = True,
        message: str = "",
    ) -> bool:
        """Share document with team members (internal only).

        Args:
            item_id: Drive item ID to share
            team_members: List of member email addresses or UPNs
            permission: Permission level (read, write)
            send_invitation: Whether to send email notification
            message: Optional message to include in invitation

        Returns:
            True if shared successfully, False if all recipients blocked
        """
        # Validate all recipients are internal
        valid_members = self.validate_recipients(team_members)

        if not valid_members:
            logger.warning(
                f"Share blocked: no valid recipients "
                f"(worker: {self.worker.worker_id}, item_id: {item_id})"
            )
            return False

        await self._rate_limit()

        try:
            # Create sharing invitation
            roles = ["read"] if permission == "read" else ["write"]

            await (
                self.client.graph.users.by_user_id(self.worker.entra_object_id)
                .drive.items.by_drive_item_id(item_id)
                .invite.post(
                    body={
                        "recipients": [{"email": member} for member in valid_members],
                        "roles": roles,
                        "requireSignIn": True,
                        "sendInvitation": send_invitation,
                        "message": message,
                    }
                )
            )

            self._log_operation(
                "document_share",
                {
                    "item_id": item_id,
                    "recipients": valid_members,
                    "permission": permission,
                },
            )

            return True

        except Exception as e:
            self._log_error("document_share", e, {"item_id": item_id})
            raise

    async def download_document(
        self,
        item_id: str,
    ) -> bytes | None:
        """Download document content.

        Args:
            item_id: Drive item ID to download

        Returns:
            Document content as bytes
        """
        await self._rate_limit()

        try:
            content = (
                await self.client.graph.users.by_user_id(self.worker.entra_object_id)
                .drive.items.by_drive_item_id(item_id)
                .content.get()
            )

            self._log_operation(
                "document_download",
                {"item_id": item_id},
            )

            return content

        except Exception as e:
            self._log_error("document_download", e, {"item_id": item_id})
            raise

    async def list_documents(
        self,
        folder_path: str = "Documents",
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """List documents in a folder.

        Args:
            folder_path: Path within OneDrive
            count: Maximum number of items to return

        Returns:
            List of document info dictionaries
        """
        await self._rate_limit()

        try:
            items = (
                await self.client.graph.users.by_user_id(self.worker.entra_object_id)
                .drive.root.item_with_path(folder_path)
                .children.get(
                    request_configuration={
                        "query_parameters": {
                            "top": count,
                            "select": "id,name,size,createdDateTime,lastModifiedDateTime",
                        }
                    }
                )
            )

            self._log_operation(
                "document_list",
                {"folder": folder_path, "count": len(items.value or [])},
            )

            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "size": item.size,
                    "created": item.created_date_time,
                    "modified": item.last_modified_date_time,
                }
                for item in (items.value or [])
            ]

        except Exception as e:
            self._log_error("document_list", e, {"folder": folder_path})
            raise

    async def upload_to_sharepoint(
        self,
        site_id: str,
        library_name: str,
        file_name: str,
        content: bytes,
    ) -> str | None:
        """Upload document to SharePoint site.

        Args:
            site_id: SharePoint site ID
            library_name: Document library name
            file_name: Name for the uploaded file
            content: File content as bytes

        Returns:
            Document ID if uploaded successfully
        """
        await self._rate_limit()

        try:
            # Get drive for document library
            drives = await self.client.graph.sites.by_site_id(site_id).drives.get()

            library_drive = next(
                (d for d in (drives.value or []) if d.name == library_name),
                None,
            )

            if not library_drive:
                logger.warning(f"Library not found: {library_name}")
                return None

            # Upload file
            result = (
                await self.client.graph.drives.by_drive_id(library_drive.id)
                .root.item_with_path(file_name)
                .content.put(content)
            )

            self._log_operation(
                "document_upload_sharepoint",
                {
                    "site_id": site_id,
                    "library": library_name,
                    "file": file_name,
                    "size_bytes": len(content),
                },
            )

            return result.id if result else None

        except Exception as e:
            self._log_error(
                "document_upload_sharepoint",
                e,
                {"site_id": site_id, "file": file_name},
            )
            raise

    async def create_folder(
        self,
        folder_name: str,
        parent_path: str = "",
    ) -> str | None:
        """Create a folder in OneDrive.

        Args:
            folder_name: Name of the folder to create
            parent_path: Parent folder path (empty for root)

        Returns:
            Folder ID if created successfully
        """
        await self._rate_limit()

        try:
            if parent_path:
                parent = (
                    await self.client.graph.users.by_user_id(self.worker.entra_object_id)
                    .drive.root.item_with_path(parent_path)
                    .get()
                )
                parent_id = parent.id
            else:
                parent_id = "root"

            result = (
                await self.client.graph.users.by_user_id(self.worker.entra_object_id)
                .drive.items.by_drive_item_id(parent_id)
                .children.post(
                    body={
                        "name": folder_name,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": "rename",
                    }
                )
            )

            self._log_operation(
                "document_create_folder",
                {"name": folder_name, "parent": parent_path},
            )

            return result.id if result else None

        except Exception as e:
            self._log_error(
                "document_create_folder",
                e,
                {"name": folder_name, "parent": parent_path},
            )
            raise
