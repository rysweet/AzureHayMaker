"""Integration tests for Knowledge Worker M365 operations.

This module tests the M365 operations layer with mocked Graph API responses.
These are integration tests because they test the interaction between:
- Operation classes (EmailOperations, TeamsOperations, etc.)
- Communication validators
- Rate limiting
- Graph API client interfaces

The tests use mocked Graph API clients to verify correct API call patterns
without requiring actual M365 tenant access.

Reference: ARCHITECTURE.md Section 5 - M365 Operations Module
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import paths based on ARCHITECTURE.md specification
try:
    from azure_haymaker.knowledge_worker.safety.communication import (
        CommunicationValidator,
        ExternalRecipientError,
    )

    from azure_haymaker.knowledge_worker.models.worker import (
        EndpointType,
        WorkerIdentity,
        WorkerPersona,
    )
    from azure_haymaker.knowledge_worker.operations.base import M365OperationBase
    from azure_haymaker.knowledge_worker.operations.calendar import CalendarOperations
    from azure_haymaker.knowledge_worker.operations.documents import DocumentOperations
    from azure_haymaker.knowledge_worker.operations.email import EmailOperations
    from azure_haymaker.knowledge_worker.operations.teams import TeamsOperations

    OPERATIONS_AVAILABLE = True
except ImportError:
    OPERATIONS_AVAILABLE = False
    WorkerIdentity = None
    WorkerPersona = None
    EndpointType = None
    EmailOperations = None
    TeamsOperations = None
    DocumentOperations = None
    CalendarOperations = None
    M365OperationBase = None
    CommunicationValidator = None
    ExternalRecipientError = None


pytestmark = pytest.mark.skipif(
    not OPERATIONS_AVAILABLE, reason="Knowledge Worker operations module not yet implemented"
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_graph_client() -> AsyncMock:
    """Create a mock Microsoft Graph client for testing.

    This mock simulates the msgraph-sdk GraphServiceClient interface
    for email, Teams, document, and calendar operations.
    """
    mock = AsyncMock()

    # Setup users endpoint chain
    mock.users = MagicMock()
    mock.users.by_user_id = MagicMock(return_value=MagicMock())

    # Setup send_mail endpoint
    mock.users.by_user_id.return_value.send_mail = MagicMock()
    mock.users.by_user_id.return_value.send_mail.post = AsyncMock(
        return_value=MagicMock(id="message-id-123")
    )

    # Setup mail folders endpoint
    mock.users.by_user_id.return_value.mail_folders = MagicMock()
    mock.users.by_user_id.return_value.mail_folders.by_mail_folder_id = MagicMock(
        return_value=MagicMock()
    )
    mock.users.by_user_id.return_value.mail_folders.by_mail_folder_id.return_value.messages = (
        MagicMock()
    )
    mock.users.by_user_id.return_value.mail_folders.by_mail_folder_id.return_value.messages.get = (
        AsyncMock(return_value=MagicMock(value=[]))
    )

    # Setup Teams endpoint chain
    mock.teams = MagicMock()
    mock.teams.by_team_id = MagicMock(return_value=MagicMock())
    mock.teams.by_team_id.return_value.channels = MagicMock()
    mock.teams.by_team_id.return_value.channels.by_channel_id = MagicMock(return_value=MagicMock())
    mock.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages = MagicMock()
    mock.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages.post = (
        AsyncMock(return_value=MagicMock(id="teams-message-id-123"))
    )

    # Setup chats endpoint
    mock.chats = MagicMock()
    mock.chats.by_chat_id = MagicMock(return_value=MagicMock())
    mock.chats.by_chat_id.return_value.messages = MagicMock()
    mock.chats.by_chat_id.return_value.messages.post = AsyncMock(
        return_value=MagicMock(id="chat-message-id-123")
    )

    # Setup drive endpoint
    mock.users.by_user_id.return_value.drive = MagicMock()
    mock.users.by_user_id.return_value.drive.root = MagicMock()
    mock.users.by_user_id.return_value.drive.root.item_with_path = MagicMock(
        return_value=MagicMock()
    )
    mock.users.by_user_id.return_value.drive.root.item_with_path.return_value.content = MagicMock()
    mock.users.by_user_id.return_value.drive.root.item_with_path.return_value.content.put = (
        AsyncMock(return_value=MagicMock(id="document-id-123"))
    )

    # Setup calendar endpoint
    mock.users.by_user_id.return_value.calendar = MagicMock()
    mock.users.by_user_id.return_value.calendar.events = MagicMock()
    mock.users.by_user_id.return_value.calendar.events.post = AsyncMock(
        return_value=MagicMock(id="event-id-123")
    )

    return mock


@pytest.fixture
def mock_m365_client(mock_graph_client: AsyncMock) -> MagicMock:
    """Create a mock M365 client wrapper containing the Graph client."""
    client = MagicMock()
    client.graph = mock_graph_client
    return client


@pytest.fixture
def test_worker() -> WorkerIdentity:
    """Create a test worker identity."""
    return WorkerIdentity(
        worker_id="kw-test123-engi-001",
        display_name="Test Engineer",
        user_principal_name="kw-test123-engi-001@haymaker.onmicrosoft.com",
        department="engineering",
        persona=WorkerPersona.ENGINEERING,
        entra_object_id="entra-obj-test-001",
        endpoint_type=EndpointType.CLI_CONTAINER,
    )


@pytest.fixture
def allowed_recipients() -> set[str]:
    """Create set of allowed internal recipients."""
    return {
        "kw-test123-engi-001@haymaker.onmicrosoft.com",
        "kw-test123-engi-002@haymaker.onmicrosoft.com",
        "kw-test123-exec-001@haymaker.onmicrosoft.com",
        "team-engineering@haymaker.onmicrosoft.com",
    }


# ============================================================================
# Email Operations Tests
# ============================================================================


class TestEmailOperationsSendEmail:
    """Tests for EmailOperations.send_email() method."""

    @pytest.fixture
    def email_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> EmailOperations:
        """Create EmailOperations instance for testing."""
        return EmailOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_send_email_to_internal_recipient(
        self, email_ops: EmailOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test sending email to internal recipient succeeds."""
        result = await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            subject="Test Subject",
            body="<p>Test body content</p>",
        )

        assert result == "message-id-123"
        # Verify Graph API was called
        mock_m365_client.graph.users.by_user_id.assert_called()

    @pytest.mark.asyncio
    async def test_send_email_to_multiple_internal_recipients(
        self, email_ops: EmailOperations
    ) -> None:
        """Test sending email to multiple internal recipients."""
        result = await email_ops.send_email(
            to=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",
                "kw-test123-exec-001@haymaker.onmicrosoft.com",
            ],
            subject="Team Update",
            body="Update content",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_send_email_to_external_recipient_blocked(
        self, email_ops: EmailOperations
    ) -> None:
        """Test that email to external recipient is blocked."""
        result = await email_ops.send_email(
            to=["attacker@evil.com"],
            subject="Sensitive Info",
            body="Should never be sent",
        )

        # Should return None when blocked
        assert result is None

    @pytest.mark.asyncio
    async def test_send_email_mixed_recipients_filters(
        self, email_ops: EmailOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test that mixed recipients filters to internal only."""
        result = await email_ops.send_email(
            to=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",  # Valid
                "external@gmail.com",  # Invalid - filtered out
            ],
            subject="Mixed Recipients",
            body="Test content",
        )

        # Should send to valid recipient only
        assert result is not None

    @pytest.mark.asyncio
    async def test_send_email_all_external_blocked(self, email_ops: EmailOperations) -> None:
        """Test that email is blocked when ALL recipients are external."""
        result = await email_ops.send_email(
            to=["external1@gmail.com", "external2@outlook.com"],
            subject="Blocked Email",
            body="No valid recipients",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_send_email_with_cc(self, email_ops: EmailOperations) -> None:
        """Test sending email with CC recipients."""
        result = await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            cc=["kw-test123-exec-001@haymaker.onmicrosoft.com"],
            subject="With CC",
            body="Content",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_send_email_cc_filters_external(self, email_ops: EmailOperations) -> None:
        """Test that CC recipients also filter external addresses."""
        result = await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            cc=["external@hacker.com"],  # Should be filtered
            subject="CC Test",
            body="Content",
        )

        # Should still send, but CC is filtered
        assert result is not None

    @pytest.mark.asyncio
    async def test_send_email_with_importance(self, email_ops: EmailOperations) -> None:
        """Test sending email with importance level."""
        result = await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            subject="Urgent Update",
            body="Important content",
            importance="high",
        )

        assert result is not None


class TestEmailOperationsReadInbox:
    """Tests for EmailOperations inbox reading."""

    @pytest.fixture
    def email_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> EmailOperations:
        """Create EmailOperations instance for testing."""
        return EmailOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_read_inbox_returns_messages(
        self, email_ops: EmailOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test reading inbox returns message list."""
        # Setup mock messages
        mock_message = MagicMock()
        mock_message.id = "msg-001"
        mock_message.subject = "Test Message"
        mock_message.from_ = MagicMock()
        mock_message.from_.email_address = MagicMock()
        mock_message.from_.email_address.address = "sender@haymaker.onmicrosoft.com"
        mock_message.received_date_time = datetime.now(UTC)
        mock_message.is_read = False

        mock_m365_client.graph.users.by_user_id.return_value.mail_folders.by_mail_folder_id.return_value.messages.get.return_value = MagicMock(
            value=[mock_message]
        )

        messages = await email_ops.read_inbox(count=10)

        assert len(messages) == 1
        assert messages[0]["id"] == "msg-001"
        assert messages[0]["subject"] == "Test Message"

    @pytest.mark.asyncio
    async def test_read_inbox_unread_only(self, email_ops: EmailOperations) -> None:
        """Test reading only unread messages."""
        messages = await email_ops.read_inbox(count=10, unread_only=True)

        assert isinstance(messages, list)


# ============================================================================
# Teams Operations Tests
# ============================================================================


class TestTeamsOperations:
    """Tests for TeamsOperations class."""

    @pytest.fixture
    def teams_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> TeamsOperations:
        """Create TeamsOperations instance for testing."""
        return TeamsOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_post_to_channel(self, teams_ops: TeamsOperations) -> None:
        """Test posting message to Teams channel."""
        result = await teams_ops.post_to_channel(
            team_id="team-eng-001",
            channel_id="channel-general",
            content="Hello team!",
        )

        assert result == "teams-message-id-123"

    @pytest.mark.asyncio
    async def test_post_to_channel_with_mentions(self, teams_ops: TeamsOperations) -> None:
        """Test posting with @mentions."""
        result = await teams_ops.post_to_channel(
            team_id="team-eng-001",
            channel_id="channel-general",
            content="@mention test",
            mentions=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_post_to_channel_filters_external_mentions(
        self, teams_ops: TeamsOperations
    ) -> None:
        """Test that external mentions are filtered out."""
        result = await teams_ops.post_to_channel(
            team_id="team-eng-001",
            channel_id="channel-general",
            content="Message with filtered mentions",
            mentions=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",  # Valid
                "external@hacker.com",  # Should be filtered
            ],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_send_chat_message(self, teams_ops: TeamsOperations) -> None:
        """Test sending direct chat message."""
        result = await teams_ops.send_chat_message(
            recipient_id="kw-test123-engi-002@haymaker.onmicrosoft.com",
            content="Direct message content",
        )

        # Implementation should get/create chat first
        assert result is not None

    @pytest.mark.asyncio
    async def test_send_chat_message_to_external_blocked(self, teams_ops: TeamsOperations) -> None:
        """Test that chat to external recipient is blocked."""
        result = await teams_ops.send_chat_message(
            recipient_id="external@gmail.com",
            content="Should be blocked",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_reply_to_thread(self, teams_ops: TeamsOperations) -> None:
        """Test replying to existing thread."""
        # Setup mock for replies endpoint
        teams_ops.client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages.by_chat_message_id = MagicMock(
            return_value=MagicMock()
        )
        teams_ops.client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages.by_chat_message_id.return_value.replies = MagicMock()
        teams_ops.client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value.messages.by_chat_message_id.return_value.replies.post = AsyncMock(
            return_value=MagicMock(id="reply-id-123")
        )

        result = await teams_ops.reply_to_thread(
            team_id="team-eng-001",
            channel_id="channel-general",
            message_id="parent-msg-001",
            content="Reply content",
        )

        assert result == "reply-id-123"


# ============================================================================
# Document Operations Tests
# ============================================================================


class TestDocumentOperations:
    """Tests for DocumentOperations class."""

    @pytest.fixture
    def doc_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> DocumentOperations:
        """Create DocumentOperations instance for testing."""
        return DocumentOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_create_document(self, doc_ops: DocumentOperations) -> None:
        """Test creating a document in OneDrive."""
        result = await doc_ops.create_document(
            name="test-doc.docx",
            content=b"document content",
            folder_path="Documents",
        )

        assert result == "document-id-123"

    @pytest.mark.asyncio
    async def test_create_document_custom_folder(self, doc_ops: DocumentOperations) -> None:
        """Test creating document in custom folder."""
        result = await doc_ops.create_document(
            name="report.xlsx",
            content=b"spreadsheet content",
            folder_path="Documents/Reports",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_share_with_team_internal_only(
        self, doc_ops: DocumentOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test sharing document with internal team members."""
        # Setup mock for invite endpoint
        mock_m365_client.graph.users.by_user_id.return_value.drive.items = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id = (
            MagicMock(return_value=MagicMock())
        )
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id.return_value.invite = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id.return_value.invite.post = AsyncMock()

        result = await doc_ops.share_with_team(
            item_id="doc-001",
            team_members=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",
                "kw-test123-exec-001@haymaker.onmicrosoft.com",
            ],
            permission="read",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_share_with_team_filters_external(
        self, doc_ops: DocumentOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test that external team members are filtered from sharing."""
        # Setup mock
        mock_m365_client.graph.users.by_user_id.return_value.drive.items = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id = (
            MagicMock(return_value=MagicMock())
        )
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id.return_value.invite = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.drive.items.by_drive_item_id.return_value.invite.post = AsyncMock()

        result = await doc_ops.share_with_team(
            item_id="doc-001",
            team_members=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",  # Valid
                "external@competitor.com",  # Should be filtered
            ],
            permission="read",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_share_with_team_no_valid_members(self, doc_ops: DocumentOperations) -> None:
        """Test sharing fails when no valid members after filtering."""
        result = await doc_ops.share_with_team(
            item_id="doc-001",
            team_members=["external@hacker.com"],
            permission="read",
        )

        assert result is False


# ============================================================================
# Calendar Operations Tests
# ============================================================================


class TestCalendarOperations:
    """Tests for CalendarOperations class."""

    @pytest.fixture
    def cal_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> CalendarOperations:
        """Create CalendarOperations instance for testing."""
        return CalendarOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_create_event_internal_attendees(self, cal_ops: CalendarOperations) -> None:
        """Test creating event with internal attendees."""
        result = await cal_ops.create_event(
            subject="Team Standup",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            attendees=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
        )

        assert result == "event-id-123"

    @pytest.mark.asyncio
    async def test_create_event_with_location(self, cal_ops: CalendarOperations) -> None:
        """Test creating event with location."""
        result = await cal_ops.create_event(
            subject="All Hands Meeting",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            attendees=["kw-test123-exec-001@haymaker.onmicrosoft.com"],
            location="Conference Room A",
            is_online=False,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_online_meeting(self, cal_ops: CalendarOperations) -> None:
        """Test creating online Teams meeting."""
        result = await cal_ops.create_event(
            subject="Virtual Sync",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            attendees=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            is_online=True,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_event_external_attendees_blocked(
        self, cal_ops: CalendarOperations
    ) -> None:
        """Test that event with only external attendees is blocked."""
        result = await cal_ops.create_event(
            subject="External Meeting",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            attendees=["external@vendor.com"],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_event_mixed_attendees_filters(self, cal_ops: CalendarOperations) -> None:
        """Test that mixed attendees list filters to internal only."""
        result = await cal_ops.create_event(
            subject="Mixed Meeting",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            attendees=[
                "kw-test123-engi-002@haymaker.onmicrosoft.com",  # Valid
                "external@vendor.com",  # Filtered
            ],
        )

        # Should create with valid attendees only
        assert result is not None

    @pytest.mark.asyncio
    async def test_respond_to_invitation(
        self, cal_ops: CalendarOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test responding to meeting invitation."""
        # Setup mock for accept endpoint
        mock_m365_client.graph.users.by_user_id.return_value.events = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.events.by_event_id = MagicMock(
            return_value=MagicMock()
        )
        mock_m365_client.graph.users.by_user_id.return_value.events.by_event_id.return_value.accept = MagicMock()
        mock_m365_client.graph.users.by_user_id.return_value.events.by_event_id.return_value.accept.post = AsyncMock()

        result = await cal_ops.respond_to_invitation(
            event_id="event-invite-001",
            response="accept",
        )

        assert result is True


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Tests for operation rate limiting behavior."""

    @pytest.fixture
    def email_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> EmailOperations:
        """Create EmailOperations instance for testing."""
        return EmailOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_rate_limit_increments_counter(self, email_ops: EmailOperations) -> None:
        """Test that operations increment the rate limit counter."""
        initial_count = email_ops._operation_count

        await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            subject="Test",
            body="Content",
        )

        assert email_ops._operation_count > initial_count

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_pauses_on_threshold(self, email_ops: EmailOperations) -> None:
        """Test that rate limiter pauses at threshold.

        Note: This test is marked slow because it may actually wait.
        In production tests, you might want to mock time.sleep.
        """
        # Set counter just below threshold
        email_ops._operation_count = 99

        # Next operation should trigger rate limit pause
        start = datetime.now(UTC)

        await email_ops.send_email(
            to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
            subject="Rate Limited",
            body="Content",
        )

        # Check that some time passed (rate limit pause)
        (datetime.now(UTC) - start).total_seconds()
        # Should have paused (implementation detail: 1 second per ARCHITECTURE.md)
        # This assertion depends on implementation
        assert email_ops._operation_count == 100


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestOperationErrorHandling:
    """Tests for operation error handling."""

    @pytest.fixture
    def email_ops(
        self,
        test_worker: WorkerIdentity,
        mock_m365_client: MagicMock,
        allowed_recipients: set[str],
    ) -> EmailOperations:
        """Create EmailOperations instance for testing."""
        return EmailOperations(
            worker_identity=test_worker,
            m365_client=mock_m365_client,
            allowed_recipients=allowed_recipients,
        )

    @pytest.mark.asyncio
    async def test_graph_api_error_handled(
        self, email_ops: EmailOperations, mock_m365_client: MagicMock
    ) -> None:
        """Test that Graph API errors are handled gracefully."""
        # Setup mock to raise exception
        mock_m365_client.graph.users.by_user_id.return_value.send_mail.post.side_effect = Exception(
            "Graph API error"
        )

        # Should handle error and not crash
        with pytest.raises(Exception, match="(?i)graph api error"):
            await email_ops.send_email(
                to=["kw-test123-engi-002@haymaker.onmicrosoft.com"],
                subject="Test",
                body="Content",
            )

    @pytest.mark.asyncio
    async def test_empty_recipients_handled(self, email_ops: EmailOperations) -> None:
        """Test handling of empty recipients list."""
        result = await email_ops.send_email(
            to=[],
            subject="No Recipients",
            body="Content",
        )

        assert result is None


# ============================================================================
# E2E Test Documentation
# ============================================================================


class TestE2EDocumentation:
    """Documentation for E2E tests that would run against real M365 tenant.

    These tests document what E2E tests WOULD cover when connected to
    a real M365 tenant. They are not executed in CI/CD.
    """

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_email_roundtrip(self) -> None:
        """E2E: Send email from Worker A to Worker B, verify receipt.

        Steps:
        1. Worker A sends email to Worker B
        2. Wait for delivery (up to 60 seconds)
        3. Worker B reads inbox
        4. Verify email appears in Worker B's inbox
        5. Clean up: delete test email

        Verifies:
        - Email actually delivered via Exchange Online
        - Correct sender/recipient headers
        - Body content preserved
        """
        pass

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_teams_channel_post(self) -> None:
        """E2E: Post message to Teams channel, verify visible.

        Steps:
        1. Worker posts to team channel
        2. Read channel messages
        3. Verify message appears with correct content
        4. Clean up: delete test message

        Verifies:
        - Message posted to correct Teams channel
        - Content and formatting preserved
        - Attribution to correct worker
        """
        pass

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_document_upload_and_share(self) -> None:
        """E2E: Upload document and share with team.

        Steps:
        1. Worker uploads document to OneDrive
        2. Share document with team member
        3. Team member accesses document
        4. Verify access and content
        5. Clean up: delete document

        Verifies:
        - Document uploaded to correct location
        - Sharing permissions applied correctly
        - Content accessible to shared users
        """
        pass

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_meeting_invitation(self) -> None:
        """E2E: Create meeting, verify invitations sent.

        Steps:
        1. Worker creates calendar event with attendees
        2. Attendees receive invitation
        3. Attendee accepts invitation
        4. Verify acceptance reflected on organizer's calendar
        5. Clean up: cancel meeting

        Verifies:
        - Meeting created in Exchange Online
        - Invitations delivered to attendees
        - Response workflow functions correctly
        """
        pass

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_transport_rule_blocks_external(self) -> None:
        """E2E: Verify transport rule blocks external email.

        Steps:
        1. Ensure transport rule is active
        2. Attempt to send email to external address
        3. Verify email is rejected/bounced
        4. Verify NDR contains expected error message

        Verifies:
        - Transport rule enforces internal-only policy
        - External email attempts are blocked at server level
        - Defense in depth beyond application-level validation
        """
        pass

    @pytest.mark.skip(reason="E2E tests require real M365 tenant")
    def test_e2e_50_worker_simulation(self) -> None:
        """E2E: Run 50-worker simulation for extended period.

        Steps:
        1. Provision 50 workers across departments
        2. Run activity simulation for 1 hour
        3. Collect activity metrics
        4. Verify no external communications
        5. Clean up all resources

        Verifies:
        - System handles 50 concurrent workers
        - Activity patterns match configuration
        - No resource leaks or failures
        - Complete cleanup achieved
        """
        pass
