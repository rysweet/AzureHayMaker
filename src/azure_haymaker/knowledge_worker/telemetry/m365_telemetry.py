"""M365 Telemetry Collection for Knowledge Worker Activity Framework.

Collects and aggregates Microsoft 365 telemetry data including email,
calendar events, and Teams messages for workers.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from azure_haymaker.knowledge_worker.models.worker import WorkerIdentity

logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGES_PER_QUERY = 1000


@dataclass
class EmailEvidence:
    """Email telemetry evidence for a worker.

    Attributes:
        message_id: Unique message ID from Graph API
        subject: Email subject line
        sender: Sender email address
        recipients: List of recipient email addresses
        sent_datetime: When the email was sent
        worker_id: Worker who sent/received this email
        body_preview: Preview of email body (optional)
    """

    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    sent_datetime: datetime
    worker_id: str
    body_preview: str | None = None


@dataclass
class CalendarEvidence:
    """Calendar event telemetry evidence for a worker.

    Attributes:
        event_id: Unique event ID from Graph API
        subject: Event subject/title
        organizer: Organizer email address
        attendees: List of attendee email addresses
        start_time: Event start time
        end_time: Event end time
        is_online_meeting: Whether this is a Teams/online meeting
        worker_id: Worker who organized/attended this event
        location: Meeting location (optional)
    """

    event_id: str
    subject: str
    organizer: str
    attendees: list[str]
    start_time: datetime
    end_time: datetime
    is_online_meeting: bool
    worker_id: str
    location: str | None = None


@dataclass
class TeamsEvidence:
    """Teams message telemetry evidence for a worker.

    Attributes:
        message_id: Unique message ID from Graph API
        content: Message content/body
        sender_id: Sender user ID
        team_id: Team ID where message was posted
        channel_id: Channel ID where message was posted
        created_datetime: When the message was created
        worker_id: Worker who sent this message
        importance: Message importance level (optional)
    """

    message_id: str
    content: str
    sender_id: str
    team_id: str
    channel_id: str
    created_datetime: datetime
    worker_id: str
    importance: str | None = None


class M365TelemetryCollector:
    """Collects M365 telemetry data for knowledge workers.

    Uses Microsoft Graph API to query:
    - Email messages (sent/received)
    - Calendar events (organized/attended)
    - Teams messages (posted in channels)

    Attributes:
        graph_client: Microsoft Graph API client
        run_id: HayMaker run ID for this deployment
    """

    def __init__(self, graph_client: Any, run_id: str):
        """Initialize M365TelemetryCollector.

        Args:
            graph_client: Microsoft Graph API client with `graph` property
            run_id: HayMaker run ID for resource tagging
        """
        self.graph_client = graph_client
        self.run_id = run_id

    async def get_emails_for_worker(
        self,
        worker: WorkerIdentity,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[EmailEvidence]:
        """Get email messages for a worker.

        Queries the worker's mailbox for messages within the specified time range.

        Args:
            worker: Worker identity
            start_time: Start of time range (optional)
            end_time: End of time range (optional)

        Returns:
            List of EmailEvidence objects
        """
        try:
            # Build OData filter for time range
            filter_parts = []
            if start_time:
                filter_parts.append(f"receivedDateTime ge {start_time.isoformat()}")
            if end_time:
                filter_parts.append(f"receivedDateTime le {end_time.isoformat()}")

            request_config = {}
            if filter_parts:
                request_config = {
                    "query_parameters": {
                        "filter": " and ".join(filter_parts),
                        "top": MAX_MESSAGES_PER_QUERY,
                    }
                }

            # Query messages via Graph API
            messages = await self.graph_client.graph.users.by_user_id(
                worker.entra_object_id
            ).messages.get(request_configuration=request_config if filter_parts else None)

            # Convert to EmailEvidence objects
            evidence_list = []
            for msg in messages.value or []:
                # Extract recipients
                recipients = []
                if msg.to_recipients:
                    recipients.extend([r.email_address.address for r in msg.to_recipients])

                evidence = EmailEvidence(
                    message_id=msg.id,
                    subject=msg.subject or "(no subject)",
                    sender=msg.from_.email_address.address if msg.from_ else "unknown",
                    recipients=recipients,
                    sent_datetime=msg.received_date_time,
                    worker_id=worker.worker_id,
                    body_preview=getattr(msg, "body_preview", None),
                )
                evidence_list.append(evidence)

            logger.info(f"Collected {len(evidence_list)} email messages for {worker.worker_id}")
            return evidence_list

        except Exception as e:
            logger.error(f"Failed to get emails for {worker.worker_id}: {e}")
            raise

    async def get_calendar_events_for_worker(
        self,
        worker: WorkerIdentity,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CalendarEvidence]:
        """Get calendar events for a worker.

        Queries the worker's calendar for events within the specified time range.

        Args:
            worker: Worker identity
            start_time: Start of time range (optional)
            end_time: End of time range (optional)

        Returns:
            List of CalendarEvidence objects
        """
        try:
            # Build OData filter for time range
            filter_parts = []
            if start_time:
                filter_parts.append(f"start/dateTime ge '{start_time.isoformat()}'")
            if end_time:
                filter_parts.append(f"end/dateTime le '{end_time.isoformat()}'")

            request_config = {}
            if filter_parts:
                request_config = {
                    "query_parameters": {
                        "filter": " and ".join(filter_parts),
                        "top": MAX_MESSAGES_PER_QUERY,
                    }
                }

            # Query calendar events via Graph API
            events = await self.graph_client.graph.users.by_user_id(
                worker.entra_object_id
            ).calendar.events.get(request_configuration=request_config if filter_parts else None)

            # Convert to CalendarEvidence objects
            evidence_list = []
            for event in events.value or []:
                # Extract attendees
                attendees = []
                if event.attendees:
                    attendees.extend([a.email_address.address for a in event.attendees])

                # Parse datetime strings
                start_dt = datetime.fromisoformat(event.start.date_time)
                end_dt = datetime.fromisoformat(event.end.date_time)

                evidence = CalendarEvidence(
                    event_id=event.id,
                    subject=event.subject or "(no subject)",
                    organizer=(
                        event.organizer.email_address.address if event.organizer else "unknown"
                    ),
                    attendees=attendees,
                    start_time=start_dt,
                    end_time=end_dt,
                    is_online_meeting=getattr(event, "is_online_meeting", False),
                    worker_id=worker.worker_id,
                    location=(
                        event.location.display_name
                        if hasattr(event, "location") and event.location
                        else None
                    ),
                )
                evidence_list.append(evidence)

            logger.info(f"Collected {len(evidence_list)} calendar events for {worker.worker_id}")
            return evidence_list

        except Exception as e:
            logger.error(f"Failed to get calendar events for {worker.worker_id}: {e}")
            raise

    async def get_teams_messages_for_worker(
        self,
        worker: WorkerIdentity,
        team_id: str,
        channel_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[TeamsEvidence]:
        """Get Teams messages for a worker in a specific channel.

        Queries Teams channel messages. To get all messages across channels,
        call this method for each channel the worker belongs to.

        Args:
            worker: Worker identity
            team_id: Team ID to query
            channel_id: Channel ID to query
            start_time: Start of time range (optional)
            end_time: End of time range (optional)

        Returns:
            List of TeamsEvidence objects
        """
        try:
            # Query Teams channel messages via Graph API
            messages = (
                await self.graph_client.graph.teams.by_team_id(team_id)
                .channels.by_channel_id(channel_id)
                .messages.get()
            )

            # Filter and convert to TeamsEvidence objects
            evidence_list = []
            for msg in messages.value or []:
                # Apply time filtering if specified
                msg_time = msg.created_date_time
                if start_time and msg_time < start_time:
                    continue
                if end_time and msg_time > end_time:
                    continue

                # Only include messages from this worker
                sender_id = msg.from_.user.id if msg.from_ and hasattr(msg.from_, "user") else None

                if not sender_id or sender_id != worker.entra_object_id:
                    continue

                evidence = TeamsEvidence(
                    message_id=msg.id,
                    content=msg.body.content if msg.body else "",
                    sender_id=sender_id,
                    team_id=team_id,
                    channel_id=channel_id,
                    created_datetime=msg_time,
                    worker_id=worker.worker_id,
                    importance=getattr(msg, "importance", None),
                )
                evidence_list.append(evidence)

            logger.info(
                f"Collected {len(evidence_list)} Teams messages for {worker.worker_id} "
                f"in team {team_id}, channel {channel_id}"
            )
            return evidence_list

        except Exception as e:
            logger.error(f"Failed to get Teams messages for {worker.worker_id}: {e}")
            raise

    async def get_run_summary(
        self,
        workers: list[WorkerIdentity],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated activity summary for all workers in a run.

        Collects telemetry from all workers and returns aggregate counts.

        Args:
            workers: List of worker identities
            start_time: Start of time range (optional)
            end_time: End of time range (optional)

        Returns:
            Dictionary with aggregated counts:
            - total_workers: Number of workers
            - email_count: Total emails across all workers
            - calendar_count: Total calendar events
            - teams_count: Total Teams messages
            - by_worker: Per-worker breakdown
        """
        summary = {
            "run_id": self.run_id,
            "total_workers": len(workers),
            "email_count": 0,
            "calendar_count": 0,
            "teams_count": 0,
            "by_worker": {},
        }

        for worker in workers:
            try:
                # Collect telemetry for this worker
                emails = await self.get_emails_for_worker(worker, start_time, end_time)
                calendar_events = await self.get_calendar_events_for_worker(
                    worker, start_time, end_time
                )

                # Aggregate Teams messages from all worker's teams
                teams_messages = []
                for team_id in worker.team_ids:
                    # Note: This is simplified - in production you'd query
                    # all channels in each team
                    try:
                        messages = await self.get_teams_messages_for_worker(
                            worker, team_id, "general", start_time, end_time
                        )
                        teams_messages.extend(messages)
                    except Exception as e:
                        logger.warning(
                            f"Failed to get Teams messages for {worker.worker_id} "
                            f"in team {team_id}: {e}"
                        )

                # Update summary
                summary["email_count"] += len(emails)
                summary["calendar_count"] += len(calendar_events)
                summary["teams_count"] += len(teams_messages)

                summary["by_worker"][worker.worker_id] = {
                    "email_count": len(emails),
                    "calendar_count": len(calendar_events),
                    "teams_count": len(teams_messages),
                }

            except Exception as e:
                logger.error(f"Failed to collect telemetry for {worker.worker_id}: {e}")
                summary["by_worker"][worker.worker_id] = {
                    "error": str(e),
                    "email_count": 0,
                    "calendar_count": 0,
                    "teams_count": 0,
                }

        logger.info(
            f"Run summary for {self.run_id}: "
            f"{summary['email_count']} emails, "
            f"{summary['calendar_count']} calendar events, "
            f"{summary['teams_count']} Teams messages"
        )

        return summary
