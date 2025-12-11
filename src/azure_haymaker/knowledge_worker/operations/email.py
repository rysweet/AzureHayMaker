"""Email operations for Knowledge Worker Activity Framework.

Provides email send, read, reply, and organize operations via
Microsoft Graph API with built-in recipient validation.
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


class EmailOperations(M365OperationBase):
    """Email operations using Graph API.

    Supported operations:
    - Send email (to, cc, bcc) with recipient validation
    - Read inbox messages
    - Organize (move to folders)
    - Reply/forward

    All send operations validate recipients against the internal-only
    allowlist before executing.

    Example:
        >>> ops = EmailOperations(worker, client, validator)
        >>> message_id = await ops.send_email(
        ...     to=["colleague@tenant.onmicrosoft.com"],
        ...     subject="Project Update",
        ...     body="<p>Here's the latest...</p>",
        ... )
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        validator: CommunicationValidator,
    ):
        """Initialize EmailOperations.

        Args:
            worker_identity: Identity of the worker performing operations
            m365_client: M365 client for Graph API calls
            validator: Communication validator for recipient checks
        """
        super().__init__(worker_identity, m365_client, validator)

    async def execute(self, **kwargs: Any) -> Any:
        """Execute an email operation.

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

        if operation == "send":
            return await self.send_email(**kwargs)
        elif operation == "read":
            return await self.read_inbox(**kwargs)
        elif operation == "reply":
            return await self.reply(**kwargs)
        elif operation == "move":
            return await self.move_to_folder(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        importance: str = "normal",
        save_to_sent: bool = True,
    ) -> str | None:
        """Send email from worker to internal recipients only.

        Args:
            to: List of recipient email addresses
            subject: Email subject line
            body: Email body (HTML supported)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            importance: Email importance (low, normal, high)
            save_to_sent: Whether to save to sent items

        Returns:
            Message ID if sent successfully, None if blocked

        Note:
            All recipients are validated against the internal allowlist.
            Email will not be sent if all recipients are external.
        """
        # Validate all recipients are internal
        valid_to = self.validate_recipients(to)
        valid_cc = self.validate_recipients(cc or [])
        valid_bcc = self.validate_recipients(bcc or [])

        if not valid_to:
            logger.warning(
                f"Email blocked: no valid recipients "
                f"(worker: {self.worker.worker_id}, subject: {subject})"
            )
            return None

        # Build message via Graph API
        await self._rate_limit()

        message_data = {
            "subject": subject,
            "body": {
                "contentType": "html",
                "content": body,
            },
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in valid_to
            ],
            "importance": importance,
        }

        if valid_cc:
            message_data["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in valid_cc
            ]

        if valid_bcc:
            message_data["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in valid_bcc
            ]

        try:
            # Send via Graph API
            from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
            from msgraph.generated.models.message import Message
            from msgraph.generated.models.recipient import Recipient
            from msgraph.generated.models.email_address import EmailAddress
            from msgraph.generated.models.item_body import ItemBody

            # Create proper Message object with proper nested objects
            message = Message()
            message.subject = message_data["subject"]

            # Create ItemBody object (not dict)
            body_obj = ItemBody()
            body_obj.content_type = message_data["body"]["contentType"]
            body_obj.content = message_data["body"]["content"]
            message.body = body_obj

            # Create Recipient objects (not dicts)
            message.to_recipients = [
                Recipient(email_address=EmailAddress(address=addr["emailAddress"]["address"]))
                for addr in message_data["toRecipients"]
            ]

            if "ccRecipients" in message_data:
                message.cc_recipients = [
                    Recipient(email_address=EmailAddress(address=addr["emailAddress"]["address"]))
                    for addr in message_data["ccRecipients"]
                ]

            if "bccRecipients" in message_data:
                message.bcc_recipients = [
                    Recipient(email_address=EmailAddress(address=addr["emailAddress"]["address"]))
                    for addr in message_data["bccRecipients"]
                ]

            message.importance = message_data.get("importance", "normal")

            # Create request body
            request_body = SendMailPostRequestBody(
                message=message,
                save_to_sent_items=save_to_sent
            )

            result = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).send_mail.post(request_body)

            self._log_operation(
                "email_send",
                {
                    "to": valid_to,
                    "subject": subject[:50],
                    "cc_count": len(valid_cc),
                    "bcc_count": len(valid_bcc),
                },
            )

            return result.id if result else "sent"

        except Exception as e:
            self._log_error("email_send", e, {"subject": subject[:50]})
            raise

    async def read_inbox(
        self,
        count: int = 10,
        unread_only: bool = False,
        folder: str = "inbox",
    ) -> list[dict[str, Any]]:
        """Read messages from worker's inbox.

        Args:
            count: Maximum number of messages to retrieve
            unread_only: If True, only return unread messages
            folder: Mail folder to read from (default: inbox)

        Returns:
            List of message dictionaries with id, subject, from, etc.
        """
        await self._rate_limit()

        query_params: dict[str, Any] = {
            "top": count,
            "orderby": "receivedDateTime desc",
            "select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
        }

        if unread_only:
            query_params["filter"] = "isRead eq false"

        try:
            messages = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).mail_folders.by_mail_folder_id(
                folder
            ).messages.get(
                request_configuration={"query_parameters": query_params}
            )

            self._log_operation(
                "email_read",
                {"folder": folder, "count": len(messages.value or [])},
            )

            return [
                {
                    "id": m.id,
                    "subject": m.subject,
                    "from": (
                        m.from_.email_address.address
                        if m.from_ and m.from_.email_address
                        else None
                    ),
                    "received": m.received_date_time,
                    "is_read": m.is_read,
                    "preview": m.body_preview,
                }
                for m in (messages.value or [])
            ]

        except Exception as e:
            self._log_error("email_read", e, {"folder": folder})
            raise

    async def move_to_folder(
        self,
        message_id: str,
        folder_name: str,
    ) -> bool:
        """Move message to specified folder.

        Args:
            message_id: ID of the message to move
            folder_name: Name of the destination folder

        Returns:
            True if moved successfully
        """
        await self._rate_limit()

        try:
            # Get or create the destination folder
            folder_id = await self._get_or_create_folder(folder_name)

            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).messages.by_message_id(
                message_id
            ).move.post(
                body={"destinationId": folder_id}
            )

            self._log_operation(
                "email_move",
                {"message_id": message_id, "folder": folder_name},
            )

            return True

        except Exception as e:
            self._log_error(
                "email_move", e, {"message_id": message_id, "folder": folder_name}
            )
            raise

    async def reply(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> str | None:
        """Reply to a message with internal-only recipient validation.

        SECURITY: This method validates that all reply recipients (original
        sender and, for reply_all, all original recipients) are internal
        before sending. This prevents accidental replies to external addresses.

        Args:
            message_id: ID of the message to reply to
            body: Reply body content (HTML supported)
            reply_all: If True, reply to all recipients

        Returns:
            Message ID of the reply, or None if blocked due to external recipients
        """
        await self._rate_limit()

        try:
            # SECURITY: Fetch original message to validate reply recipients
            original = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).messages.by_message_id(message_id).get()

            # Extract sender address
            sender = None
            if original.from_ and original.from_.email_address:
                sender = original.from_.email_address.address

            if not sender:
                logger.warning(
                    f"Reply blocked: could not extract sender from message "
                    f"(worker: {self.worker.worker_id}, message_id: {message_id})"
                )
                return None

            # Validate sender is internal
            if not self.validate_recipient(sender):
                logger.warning(
                    f"Reply blocked: original sender is external "
                    f"(worker: {self.worker.worker_id}, sender: {sender})"
                )
                return None

            # For reply_all, also validate all original recipients
            if reply_all:
                all_recipients: list[str] = []

                # Collect all original To recipients
                if original.to_recipients:
                    for r in original.to_recipients:
                        if r.email_address and r.email_address.address:
                            all_recipients.append(r.email_address.address)

                # Collect all original CC recipients
                if original.cc_recipients:
                    for r in original.cc_recipients:
                        if r.email_address and r.email_address.address:
                            all_recipients.append(r.email_address.address)

                # Validate all are internal (excluding self)
                external_recipients = [
                    r for r in all_recipients
                    if not self.validate_recipient(r)
                    and r.lower() != self.worker.user_principal_name.lower()
                ]

                if external_recipients:
                    logger.warning(
                        f"Reply-all blocked: external recipients in original "
                        f"(worker: {self.worker.worker_id}, external: {external_recipients})"
                    )
                    return None

            # All recipients validated - safe to reply
            if reply_all:
                await self.client.graph.users.by_user_id(
                    self.worker.entra_object_id
                ).messages.by_message_id(
                    message_id
                ).reply_all.post(
                    body={"comment": body}
                )
            else:
                await self.client.graph.users.by_user_id(
                    self.worker.entra_object_id
                ).messages.by_message_id(
                    message_id
                ).reply.post(
                    body={"comment": body}
                )

            self._log_operation(
                "email_reply",
                {"message_id": message_id, "reply_all": reply_all},
            )

            return message_id

        except Exception as e:
            self._log_error("email_reply", e, {"message_id": message_id})
            raise

    async def forward(
        self,
        message_id: str,
        to: list[str],
        comment: str = "",
    ) -> str | None:
        """Forward a message to internal recipients.

        Args:
            message_id: ID of the message to forward
            to: List of recipient email addresses
            comment: Optional comment to include

        Returns:
            Message ID if forwarded, None if blocked
        """
        # Validate all recipients are internal
        valid_to = self.validate_recipients(to)

        if not valid_to:
            logger.warning(
                f"Forward blocked: no valid recipients "
                f"(worker: {self.worker.worker_id}, message_id: {message_id})"
            )
            return None

        await self._rate_limit()

        try:
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).messages.by_message_id(
                message_id
            ).forward.post(
                body={
                    "comment": comment,
                    "toRecipients": [
                        {"emailAddress": {"address": addr}} for addr in valid_to
                    ],
                }
            )

            self._log_operation(
                "email_forward",
                {"message_id": message_id, "to": valid_to},
            )

            return message_id

        except Exception as e:
            self._log_error("email_forward", e, {"message_id": message_id})
            raise

    async def _get_or_create_folder(self, folder_name: str) -> str:
        """Get or create a mail folder.

        Args:
            folder_name: Name of the folder

        Returns:
            Folder ID
        """
        # List existing folders
        folders = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).mail_folders.get()

        # Find existing folder
        for folder in folders.value or []:
            if folder.display_name.lower() == folder_name.lower():
                return folder.id

        # Create new folder
        result = await self.client.graph.users.by_user_id(
            self.worker.entra_object_id
        ).mail_folders.post(
            body={"displayName": folder_name}
        )

        return result.id
