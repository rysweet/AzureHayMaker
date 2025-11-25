"""Teams operations for Knowledge Worker Activity Framework.

Provides Teams messaging, channel posting, and chat operations via
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


class TeamsOperations(M365OperationBase):
    """Microsoft Teams messaging operations.

    Supported operations:
    - Post to channel
    - Send direct message (chat)
    - Reply to thread
    - React to message

    All operations that target specific users validate recipients
    against the internal-only allowlist.

    Example:
        >>> ops = TeamsOperations(worker, client, validator)
        >>> message_id = await ops.post_to_channel(
        ...     team_id="team-uuid",
        ...     channel_id="channel-uuid",
        ...     content="Great progress on the project!",
        ... )
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        validator: CommunicationValidator,
    ):
        """Initialize TeamsOperations.

        Args:
            worker_identity: Identity of the worker performing operations
            m365_client: M365 client for Graph API calls
            validator: Communication validator for recipient checks
        """
        super().__init__(worker_identity, m365_client, validator)
        self._chat_cache: dict[str, str] = {}  # recipient_id -> chat_id

    async def execute(self, **kwargs: Any) -> Any:
        """Execute a Teams operation.

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

        if operation == "channel_post":
            return await self.post_to_channel(**kwargs)
        elif operation == "chat":
            return await self.send_chat_message(**kwargs)
        elif operation == "reply":
            return await self.reply_to_thread(**kwargs)
        elif operation == "react":
            return await self.react_to_message(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def post_to_channel(
        self,
        team_id: str,
        channel_id: str,
        content: str,
        mentions: list[str] | None = None,
        importance: str = "normal",
    ) -> str | None:
        """Post message to Teams channel.

        Args:
            team_id: Teams team ID
            channel_id: Channel ID within the team
            content: Message content (HTML supported)
            mentions: List of user IDs to @mention
            importance: Message importance (normal, urgent)

        Returns:
            Message ID if posted successfully
        """
        # Validate mentioned users are internal
        valid_mentions: list[str] = []
        if mentions:
            valid_mentions = [m for m in mentions if self.validate_recipient(m)]

        await self._rate_limit()

        try:
            # Build message body
            body_content = content
            mentioned_entities: list[dict[str, Any]] = []

            if valid_mentions:
                # Build mention entities
                for i, mention_id in enumerate(valid_mentions):
                    mentioned_entities.append(
                        {
                            "id": i,
                            "mentionText": f"@User{i}",
                            "mentioned": {
                                "user": {"id": mention_id},
                            },
                        }
                    )

            message_body: dict[str, Any] = {
                "body": {
                    "contentType": "html",
                    "content": body_content,
                },
                "importance": importance,
            }

            if mentioned_entities:
                message_body["mentions"] = mentioned_entities

            result = await self.client.graph.teams.by_team_id(
                team_id
            ).channels.by_channel_id(
                channel_id
            ).messages.post(
                body=message_body
            )

            self._log_operation(
                "teams_channel_post",
                {
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "mentions_count": len(valid_mentions),
                },
            )

            return result.id if result else None

        except Exception as e:
            self._log_error(
                "teams_channel_post",
                e,
                {"team_id": team_id, "channel_id": channel_id},
            )
            raise

    async def send_chat_message(
        self,
        recipient_upn: str,
        content: str,
    ) -> str | None:
        """Send direct chat message to another worker.

        SECURITY: Uses UPN (user principal name / email address) for recipient
        identification to ensure proper validation against the internal allowlist.
        The UPN is resolved to an Entra object ID internally.

        Args:
            recipient_upn: User Principal Name (email) of the recipient
            content: Message content

        Returns:
            Message ID if sent, None if recipient is external
        """
        # SECURITY: Validate recipient UPN is internal
        if not self.validate_recipient(recipient_upn):
            logger.warning(
                f"Chat blocked: external recipient "
                f"(worker: {self.worker.worker_id}, recipient: {recipient_upn})"
            )
            return None

        await self._rate_limit()

        try:
            # Resolve UPN to object ID for chat creation
            recipient_id = await self._resolve_upn_to_object_id(recipient_upn)

            if not recipient_id:
                logger.warning(
                    f"Chat blocked: could not resolve recipient "
                    f"(worker: {self.worker.worker_id}, recipient: {recipient_upn})"
                )
                return None

            # Get or create 1:1 chat
            chat_id = await self._get_or_create_chat(recipient_id)

            result = await self.client.graph.chats.by_chat_id(
                chat_id
            ).messages.post(
                body={
                    "body": {
                        "contentType": "text",
                        "content": content,
                    }
                }
            )

            self._log_operation(
                "teams_chat_message",
                {"chat_id": chat_id, "recipient_upn": recipient_upn},
            )

            return result.id if result else None

        except Exception as e:
            self._log_error(
                "teams_chat_message", e, {"recipient": recipient_upn}
            )
            raise

    async def _resolve_upn_to_object_id(self, upn: str) -> str | None:
        """Resolve a UPN to an Entra object ID.

        Args:
            upn: User Principal Name (email address)

        Returns:
            Entra object ID if found, None otherwise
        """
        try:
            user = await self.client.graph.users.by_user_id(upn).get()
            return user.id if user else None
        except Exception as e:
            logger.debug(f"Could not resolve UPN {upn}: {e}")
            return None

    async def reply_to_thread(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> str | None:
        """Reply to existing Teams thread.

        Args:
            team_id: Teams team ID
            channel_id: Channel ID within the team
            message_id: ID of the parent message
            content: Reply content

        Returns:
            Reply message ID
        """
        await self._rate_limit()

        try:
            result = await self.client.graph.teams.by_team_id(
                team_id
            ).channels.by_channel_id(
                channel_id
            ).messages.by_chat_message_id(
                message_id
            ).replies.post(
                body={
                    "body": {
                        "contentType": "text",
                        "content": content,
                    }
                }
            )

            self._log_operation(
                "teams_reply",
                {
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "parent_message_id": message_id,
                },
            )

            return result.id if result else None

        except Exception as e:
            self._log_error(
                "teams_reply",
                e,
                {"team_id": team_id, "message_id": message_id},
            )
            raise

    async def react_to_message(
        self,
        team_id: str,
        channel_id: str,
        message_id: str,
        reaction_type: str = "like",
    ) -> bool:
        """React to a Teams message.

        Args:
            team_id: Teams team ID
            channel_id: Channel ID within the team
            message_id: ID of the message to react to
            reaction_type: Type of reaction (like, heart, laugh, surprised, sad, angry)

        Returns:
            True if reaction was added successfully
        """
        await self._rate_limit()

        try:
            # Set reaction via Graph API
            # Note: The exact API structure may vary; this follows the documented pattern
            await self.client.graph.teams.by_team_id(
                team_id
            ).channels.by_channel_id(
                channel_id
            ).messages.by_chat_message_id(
                message_id
            ).set_reaction.post(
                body={"reactionType": reaction_type}
            )

            self._log_operation(
                "teams_react",
                {
                    "team_id": team_id,
                    "channel_id": channel_id,
                    "message_id": message_id,
                    "reaction": reaction_type,
                },
            )

            return True

        except Exception as e:
            self._log_error(
                "teams_react",
                e,
                {"message_id": message_id, "reaction": reaction_type},
            )
            raise

    async def list_channels(self, team_id: str) -> list[dict[str, Any]]:
        """List channels in a team.

        Args:
            team_id: Teams team ID

        Returns:
            List of channel info dictionaries
        """
        await self._rate_limit()

        try:
            channels = await self.client.graph.teams.by_team_id(
                team_id
            ).channels.get()

            return [
                {
                    "id": c.id,
                    "display_name": c.display_name,
                    "description": c.description,
                }
                for c in (channels.value or [])
            ]

        except Exception as e:
            self._log_error("teams_list_channels", e, {"team_id": team_id})
            raise

    async def list_recent_messages(
        self,
        team_id: str,
        channel_id: str,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent messages in a channel.

        Args:
            team_id: Teams team ID
            channel_id: Channel ID within the team
            count: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        await self._rate_limit()

        try:
            messages = await self.client.graph.teams.by_team_id(
                team_id
            ).channels.by_channel_id(
                channel_id
            ).messages.get(
                request_configuration={
                    "query_parameters": {
                        "top": count,
                    }
                }
            )

            return [
                {
                    "id": m.id,
                    "content": m.body.content if m.body else None,
                    "from": m.from_.user.id if m.from_ and m.from_.user else None,
                    "created": m.created_date_time,
                }
                for m in (messages.value or [])
            ]

        except Exception as e:
            self._log_error(
                "teams_list_messages",
                e,
                {"team_id": team_id, "channel_id": channel_id},
            )
            raise

    async def _get_or_create_chat(self, recipient_id: str) -> str:
        """Get or create a 1:1 chat with a user.

        Args:
            recipient_id: Entra object ID of the recipient

        Returns:
            Chat ID
        """
        # Check cache first
        if recipient_id in self._chat_cache:
            return self._chat_cache[recipient_id]

        # Create new 1:1 chat
        result = await self.client.graph.chats.post(
            body={
                "chatType": "oneOnOne",
                "members": [
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": (
                            f"https://graph.microsoft.com/v1.0/users('{self.worker.entra_object_id}')"
                        ),
                    },
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": (
                            f"https://graph.microsoft.com/v1.0/users('{recipient_id}')"
                        ),
                    },
                ],
            }
        )

        chat_id = result.id
        self._chat_cache[recipient_id] = chat_id

        return chat_id
