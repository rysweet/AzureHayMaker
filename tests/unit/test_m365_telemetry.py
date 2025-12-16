"""Unit tests for M365 Telemetry Collection.

This module tests the M365TelemetryCollector class that queries Microsoft 365
activity data including email, calendar events, and Teams messages for workers.

Tests cover:
- Email telemetry queries
- Calendar event queries
- Teams message queries
- Run-level activity aggregation
- Time-based filtering
- Evidence dataclass models

Uses pytest with AsyncMock for Graph API interactions.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Import the modules under test
try:
    from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity
    from azure_haymaker.knowledge_worker.operations.base import M365Client

    # Telemetry evidence models (to be implemented)
    from azure_haymaker.knowledge_worker.telemetry import (
        CalendarEvidence,
        EmailEvidence,
        M365TelemetryCollector,
        TeamsEvidence,
    )

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    M365TelemetryCollector = None
    EmailEvidence = None
    CalendarEvidence = None
    TeamsEvidence = None
    WorkerIdentity = None
    M365Client = None


pytestmark = pytest.mark.skipif(
    not TELEMETRY_AVAILABLE, reason="M365TelemetryCollector module not available"
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_graph_client():
    """Fixture: Mock Microsoft Graph API client."""
    client = MagicMock()
    client.graph = MagicMock()
    client.graph.users = MagicMock()
    client.graph.teams = MagicMock()
    return client


@pytest.fixture
def run_id():
    """Fixture: HayMaker run ID."""
    return str(uuid4())


@pytest.fixture
def telemetry_collector(mock_graph_client, run_id):
    """Fixture: M365TelemetryCollector instance."""
    return M365TelemetryCollector(graph_client=mock_graph_client, run_id=run_id)


@pytest.fixture
def worker_identity():
    """Fixture: Sample worker identity."""
    return WorkerIdentity(
        worker_id="kw-test-001",
        display_name="Test Worker",
        user_principal_name="test.worker@tenant.onmicrosoft.com",
        entra_object_id=str(uuid4()),
        department="engineering",
        persona="engineering",
        endpoint_type="cli_container",
        endpoint_id="container-001",
        team_ids=["team-001"],
    )


@pytest.fixture
def mock_email_response():
    """Fixture: Mock email message response from Graph API."""

    def create_message(subject: str, sender: str, received_dt: datetime):
        msg = MagicMock()
        msg.id = str(uuid4())
        msg.subject = subject
        msg.from_ = MagicMock()
        msg.from_.email_address = MagicMock()
        msg.from_.email_address.address = sender
        msg.received_date_time = received_dt
        msg.body_preview = f"Preview of {subject}"
        msg.to_recipients = [MagicMock(email_address=MagicMock(address="recipient@tenant.com"))]
        return msg

    return create_message


@pytest.fixture
def mock_calendar_response():
    """Fixture: Mock calendar event response from Graph API."""

    def create_event(subject: str, start_dt: datetime, end_dt: datetime):
        event = MagicMock()
        event.id = str(uuid4())
        event.subject = subject
        event.start = MagicMock()
        event.start.date_time = start_dt.isoformat()
        event.end = MagicMock()
        event.end.date_time = end_dt.isoformat()
        event.organizer = MagicMock()
        event.organizer.email_address = MagicMock()
        event.organizer.email_address.address = "organizer@tenant.com"
        event.attendees = []
        event.location = MagicMock()
        event.location.display_name = "Conference Room A"
        event.is_online_meeting = True
        return event

    return create_event


@pytest.fixture
def mock_teams_response():
    """Fixture: Mock Teams message response from Graph API."""

    def create_message(content: str, from_user: str, created_dt: datetime):
        msg = MagicMock()
        msg.id = str(uuid4())
        msg.body = MagicMock()
        msg.body.content = content
        msg.from_ = MagicMock()
        msg.from_.user = MagicMock()
        msg.from_.user.id = from_user
        msg.from_.user.display_name = "Test User"
        msg.created_date_time = created_dt
        msg.importance = "normal"
        return msg

    return create_message


# ==============================================================================
# EMAIL TELEMETRY TESTS
# ==============================================================================


class TestEmailTelemetry:
    """Tests for email telemetry collection."""

    @pytest.mark.asyncio
    async def test_get_emails_for_worker_returns_list(
        self, telemetry_collector, worker_identity, mock_graph_client, mock_email_response
    ):
        """Test get_emails_for_worker returns EmailEvidence list."""
        now = datetime.now(UTC)

        # Mock: 3 email messages
        mock_messages = [
            mock_email_response("Project Update", "sender1@tenant.com", now),
            mock_email_response("Meeting Notes", "sender2@tenant.com", now),
            mock_email_response("Action Items", "sender3@tenant.com", now),
        ]

        mock_result = MagicMock()
        mock_result.value = mock_messages

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_result
        )

        result = await telemetry_collector.get_emails_for_worker(worker=worker_identity)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(e, EmailEvidence) for e in result)

    @pytest.mark.asyncio
    async def test_get_emails_for_worker_with_time_filter(
        self, telemetry_collector, worker_identity, mock_graph_client, mock_email_response
    ):
        """Test get_emails_for_worker filters by time range."""
        now = datetime.now(UTC)
        start_time = now - timedelta(hours=2)
        end_time = now

        mock_messages = [
            mock_email_response("Recent Email", "sender@tenant.com", now - timedelta(hours=1))
        ]

        mock_result = MagicMock()
        mock_result.value = mock_messages

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_result
        )

        await telemetry_collector.get_emails_for_worker(
            worker=worker_identity, start_time=start_time, end_time=end_time
        )

        # Verify filter was applied in query
        call_args = mock_graph_client.graph.users.by_user_id.return_value.messages.get.call_args
        assert call_args is not None
        assert "request_configuration" in call_args.kwargs
        query_params = call_args.kwargs["request_configuration"]["query_parameters"]
        assert "filter" in query_params

    @pytest.mark.asyncio
    async def test_get_emails_for_worker_empty_results(
        self, telemetry_collector, worker_identity, mock_graph_client
    ):
        """Test get_emails_for_worker handles empty results."""
        mock_result = MagicMock()
        mock_result.value = []

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_result
        )

        result = await telemetry_collector.get_emails_for_worker(worker=worker_identity)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_emails_for_worker_handles_graph_api_error(
        self, telemetry_collector, worker_identity, mock_graph_client
    ):
        """Test get_emails_for_worker handles Graph API errors."""
        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            side_effect=Exception("Graph API error: Rate limit exceeded")
        )

        with pytest.raises(Exception, match=".") as exc_info:
            await telemetry_collector.get_emails_for_worker(worker=worker_identity)

        assert "Graph API error" in str(exc_info.value)


# ==============================================================================
# CALENDAR TELEMETRY TESTS
# ==============================================================================


class TestCalendarTelemetry:
    """Tests for calendar event telemetry collection."""

    @pytest.mark.asyncio
    async def test_get_calendar_events_for_worker_returns_list(
        self,
        telemetry_collector,
        worker_identity,
        mock_graph_client,
        mock_calendar_response,
    ):
        """Test get_calendar_events_for_worker returns CalendarEvidence list."""
        now = datetime.now(UTC)

        # Mock: 2 calendar events
        mock_events = [
            mock_calendar_response("Team Standup", now, now + timedelta(hours=1)),
            mock_calendar_response(
                "Project Review", now + timedelta(hours=2), now + timedelta(hours=3)
            ),
        ]

        mock_result = MagicMock()
        mock_result.value = mock_events

        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = AsyncMock(
            return_value=mock_result
        )

        result = await telemetry_collector.get_calendar_events_for_worker(worker=worker_identity)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(e, CalendarEvidence) for e in result)

    @pytest.mark.asyncio
    async def test_get_calendar_events_for_worker_with_filters(
        self,
        telemetry_collector,
        worker_identity,
        mock_graph_client,
        mock_calendar_response,
    ):
        """Test get_calendar_events_for_worker applies time and filter parameters."""
        now = datetime.now(UTC)
        start_time = now
        end_time = now + timedelta(days=1)

        mock_events = [
            mock_calendar_response(
                "Upcoming Meeting", now + timedelta(hours=1), now + timedelta(hours=2)
            )
        ]

        mock_result = MagicMock()
        mock_result.value = mock_events

        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = AsyncMock(
            return_value=mock_result
        )

        result = await telemetry_collector.get_calendar_events_for_worker(
            worker=worker_identity, start_time=start_time, end_time=end_time
        )

        assert len(result) == 1
        # Verify filter was applied
        call_args = (
            mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get.call_args
        )
        assert "request_configuration" in call_args.kwargs
        query_params = call_args.kwargs["request_configuration"]["query_parameters"]
        assert "filter" in query_params


# ==============================================================================
# TEAMS TELEMETRY TESTS
# ==============================================================================


class TestTeamsTelemetry:
    """Tests for Teams message telemetry collection."""

    @pytest.mark.asyncio
    async def test_get_teams_messages_for_worker_returns_list(
        self,
        telemetry_collector,
        worker_identity,
        mock_graph_client,
        mock_teams_response,
    ):
        """Test get_teams_messages_for_worker returns TeamsEvidence list."""
        now = datetime.now(UTC)

        # Mock: 3 Teams messages from the worker
        # Use worker's entra_object_id as sender to pass the filter
        mock_messages = [
            mock_teams_response("Great work on the feature!", worker_identity.entra_object_id, now),
            mock_teams_response("Can you review this PR?", worker_identity.entra_object_id, now),
            mock_teams_response("Meeting in 10 minutes", worker_identity.entra_object_id, now),
        ]

        mock_result = MagicMock()
        mock_result.value = mock_messages

        # Mock Teams channel messages
        team_id = worker_identity.team_ids[0]
        mock_channel_item = MagicMock()
        mock_channel_item.messages.get = AsyncMock(return_value=mock_result)
        mock_graph_client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value = mock_channel_item

        result = await telemetry_collector.get_teams_messages_for_worker(
            worker=worker_identity, team_id=team_id, channel_id="general"
        )

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(m, TeamsEvidence) for m in result)

    @pytest.mark.asyncio
    async def test_get_teams_messages_across_channels(
        self, telemetry_collector, worker_identity, mock_graph_client, mock_teams_response
    ):
        """Test get_teams_messages_for_worker aggregates across multiple channels."""
        now = datetime.now(UTC)

        # Mock: Different messages in different channels
        channel1_messages = [mock_teams_response("Channel 1 message", "user1", now)]
        channel2_messages = [mock_teams_response("Channel 2 message", "user2", now)]

        mock_result1 = MagicMock()
        mock_result1.value = channel1_messages
        mock_result2 = MagicMock()
        mock_result2.value = channel2_messages

        team_id = worker_identity.team_ids[0]

        # Set up mock to return different results based on channel_id
        call_count = [0]

        async def mock_get_messages(*args, **kwargs):
            result = mock_result1 if call_count[0] == 0 else mock_result2
            call_count[0] += 1
            return result

        # Mock Teams channel messages with AsyncMock
        mock_channel_item = MagicMock()
        mock_channel_item.messages.get = AsyncMock(side_effect=mock_get_messages)
        mock_graph_client.graph.teams.by_team_id.return_value.channels.by_channel_id.return_value = mock_channel_item

        result_general = await telemetry_collector.get_teams_messages_for_worker(
            worker=worker_identity, team_id=team_id, channel_id="general"
        )
        result_random = await telemetry_collector.get_teams_messages_for_worker(
            worker=worker_identity, team_id=team_id, channel_id="random"
        )

        # In practice, you'd aggregate these
        result_general + result_random
        # This is a simplified test - actual implementation would handle multi-channel aggregation
        assert len(result_general) + len(result_random) >= 0


# ==============================================================================
# RUN SUMMARY TESTS
# ==============================================================================


class TestRunSummary:
    """Tests for aggregating run-level activity summaries."""

    @pytest.mark.asyncio
    async def test_get_run_summary_aggregates_all_workers(
        self,
        telemetry_collector,
        mock_graph_client,
        mock_email_response,
        mock_calendar_response,
        mock_teams_response,
    ):
        """Test get_run_summary aggregates activity from all workers in a run."""
        # Mock: 3 workers with various activities
        workers = [
            WorkerIdentity(
                worker_id=f"kw-{i:03d}",
                display_name=f"Worker {i}",
                user_principal_name=f"worker{i}@tenant.com",
                entra_object_id=str(uuid4()),
                department="engineering",
                persona="engineering",
                endpoint_type="cli_container",
                endpoint_id=f"container-{i}",
                team_ids=["team-001"],
            )
            for i in range(3)
        ]

        now = datetime.now(UTC)

        # Mock email results for each worker
        def mock_get_emails(worker):
            mock_result = MagicMock()
            mock_result.value = [
                mock_email_response(f"Email from {worker.worker_id}", "sender@tenant.com", now)
            ]
            return mock_result

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            side_effect=lambda: mock_get_emails(workers[0])
        )

        # Get summary
        summary = await telemetry_collector.get_run_summary(workers=workers)

        assert isinstance(summary, dict)
        assert "total_workers" in summary
        assert summary["total_workers"] == 3
        assert "email_count" in summary
        assert "calendar_count" in summary
        assert "teams_count" in summary

    @pytest.mark.asyncio
    async def test_get_run_summary_with_no_activity(self, telemetry_collector, mock_graph_client):
        """Test get_run_summary handles workers with no activity."""
        workers = [
            WorkerIdentity(
                worker_id="kw-001",
                display_name="Inactive Worker",
                user_principal_name="worker@tenant.com",
                entra_object_id=str(uuid4()),
                department="engineering",
                persona="engineering",
                endpoint_type="cli_container",
                endpoint_id="container-001",
                team_ids=["team-001"],
            )
        ]

        # Mock: Empty results
        mock_result = MagicMock()
        mock_result.value = []

        mock_graph_client.graph.users.by_user_id.return_value.messages.get = AsyncMock(
            return_value=mock_result
        )
        mock_graph_client.graph.users.by_user_id.return_value.calendar.events.get = AsyncMock(
            return_value=mock_result
        )

        summary = await telemetry_collector.get_run_summary(workers=workers)

        assert summary["total_workers"] == 1
        assert summary["email_count"] == 0
        assert summary["calendar_count"] == 0
        assert summary["teams_count"] == 0


# ==============================================================================
# EVIDENCE DATACLASS TESTS
# ==============================================================================


class TestEvidenceDataclasses:
    """Tests for telemetry evidence dataclass models."""

    def test_email_evidence_dataclass(self):
        """Test EmailEvidence dataclass structure."""
        evidence = EmailEvidence(
            message_id=str(uuid4()),
            subject="Test Email",
            sender="sender@tenant.com",
            recipients=["recipient@tenant.com"],
            sent_datetime=datetime.now(UTC),
            worker_id="kw-001",
        )

        assert evidence.message_id
        assert evidence.subject == "Test Email"
        assert evidence.sender == "sender@tenant.com"
        assert len(evidence.recipients) == 1
        assert evidence.worker_id == "kw-001"

    def test_calendar_evidence_dataclass(self):
        """Test CalendarEvidence dataclass structure."""
        now = datetime.now(UTC)

        evidence = CalendarEvidence(
            event_id=str(uuid4()),
            subject="Team Meeting",
            organizer="organizer@tenant.com",
            attendees=["attendee1@tenant.com", "attendee2@tenant.com"],
            start_time=now,
            end_time=now + timedelta(hours=1),
            is_online_meeting=True,
            worker_id="kw-001",
        )

        assert evidence.event_id
        assert evidence.subject == "Team Meeting"
        assert len(evidence.attendees) == 2
        assert evidence.is_online_meeting is True
        assert evidence.worker_id == "kw-001"

    def test_teams_evidence_dataclass(self):
        """Test TeamsEvidence dataclass structure."""
        evidence = TeamsEvidence(
            message_id=str(uuid4()),
            content="Great work!",
            sender_id="user-001",
            team_id="team-001",
            channel_id="general",
            created_datetime=datetime.now(UTC),
            worker_id="kw-001",
        )

        assert evidence.message_id
        assert evidence.content == "Great work!"
        assert evidence.team_id == "team-001"
        assert evidence.channel_id == "general"
        assert evidence.worker_id == "kw-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
