"""Calendar operations for Knowledge Worker Activity Framework.

Provides calendar event management via Microsoft Graph API with
built-in attendee validation.
"""

import logging
from datetime import datetime
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


class CalendarOperations(M365OperationBase):
    """Calendar and meeting operations.

    Supported operations:
    - Create event with internal attendees only
    - Accept/decline invitation
    - Update event
    - Cancel event
    - List events

    All event creation operations validate attendees against the
    internal-only allowlist before executing.

    Example:
        >>> ops = CalendarOperations(worker, client, validator)
        >>> event_id = await ops.create_event(
        ...     subject="Project Sync",
        ...     start_time=datetime(2025, 1, 15, 14, 0),
        ...     end_time=datetime(2025, 1, 15, 15, 0),
        ...     attendees=["colleague@tenant.onmicrosoft.com"],
        ... )
    """

    def __init__(
        self,
        worker_identity: WorkerIdentity,
        m365_client: M365Client,
        validator: CommunicationValidator,
    ):
        """Initialize CalendarOperations.

        Args:
            worker_identity: Identity of the worker performing operations
            m365_client: M365 client for Graph API calls
            validator: Communication validator for attendee checks
        """
        super().__init__(worker_identity, m365_client, validator)

    async def execute(self, **kwargs: Any) -> Any:
        """Execute a calendar operation.

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
            return await self.create_event(**kwargs)
        elif operation == "respond":
            return await self.respond_to_invitation(**kwargs)
        elif operation == "update":
            return await self.update_event(**kwargs)
        elif operation == "cancel":
            return await self.cancel_event(**kwargs)
        elif operation == "list":
            return await self.list_events(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def create_event(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        attendees: list[str],
        location: str | None = None,
        is_online: bool = True,
        body: str = "",
        is_all_day: bool = False,
        reminder_minutes: int = 15,
    ) -> str | None:
        """Create calendar event with internal attendees only.

        Args:
            subject: Event subject/title
            start_time: Event start time (UTC)
            end_time: Event end time (UTC)
            attendees: List of attendee email addresses
            location: Optional physical location
            is_online: Whether to create Teams meeting
            body: Optional event body/description (HTML)
            is_all_day: Whether this is an all-day event
            reminder_minutes: Minutes before event to send reminder

        Returns:
            Event ID if created, None if all attendees are external
        """
        # Validate all attendees are internal
        valid_attendees = self.validate_recipients(attendees)

        if not valid_attendees:
            logger.warning(
                f"Event blocked: no valid attendees "
                f"(worker: {self.worker.worker_id}, subject: {subject})"
            )
            return None

        await self._rate_limit()

        try:
            event_body: dict[str, Any] = {
                "subject": subject,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                },
                "attendees": [
                    {
                        "emailAddress": {"address": addr},
                        "type": "required",
                    }
                    for addr in valid_attendees
                ],
                "isAllDay": is_all_day,
                "reminderMinutesBeforeStart": reminder_minutes,
            }

            if location:
                event_body["location"] = {"displayName": location}

            if is_online:
                event_body["isOnlineMeeting"] = True
                event_body["onlineMeetingProvider"] = "teamsForBusiness"

            if body:
                event_body["body"] = {
                    "contentType": "html",
                    "content": body,
                }

            result = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).calendar.events.post(body=event_body)

            self._log_operation(
                "calendar_create_event",
                {
                    "subject": subject,
                    "attendees": valid_attendees,
                    "is_online": is_online,
                    "start": start_time.isoformat(),
                },
            )

            return result.id if result else None

        except Exception as e:
            self._log_error("calendar_create_event", e, {"subject": subject})
            raise

    async def respond_to_invitation(
        self,
        event_id: str,
        response: str,
        comment: str = "",
        send_response: bool = True,
    ) -> bool:
        """Respond to meeting invitation.

        Args:
            event_id: ID of the event to respond to
            response: Response type (accept, tentative, decline)
            comment: Optional comment to include
            send_response: Whether to send response to organizer

        Returns:
            True if response was sent successfully
        """
        await self._rate_limit()

        try:
            response_body = {
                "comment": comment,
                "sendResponse": send_response,
            }

            if response == "accept":
                await self.client.graph.users.by_user_id(
                    self.worker.entra_object_id
                ).events.by_event_id(event_id).accept.post(body=response_body)
            elif response == "tentative":
                await self.client.graph.users.by_user_id(
                    self.worker.entra_object_id
                ).events.by_event_id(event_id).tentatively_accept.post(
                    body=response_body
                )
            elif response == "decline":
                await self.client.graph.users.by_user_id(
                    self.worker.entra_object_id
                ).events.by_event_id(event_id).decline.post(body=response_body)
            else:
                raise ValueError(f"Invalid response type: {response}")

            self._log_operation(
                "calendar_respond",
                {"event_id": event_id, "response": response},
            )

            return True

        except Exception as e:
            self._log_error(
                "calendar_respond",
                e,
                {"event_id": event_id, "response": response},
            )
            raise

    async def update_event(
        self,
        event_id: str,
        subject: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        location: str | None = None,
        body: str | None = None,
    ) -> bool:
        """Update an existing event.

        Args:
            event_id: ID of the event to update
            subject: New subject (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            location: New location (optional)
            body: New body content (optional)

        Returns:
            True if updated successfully
        """
        await self._rate_limit()

        try:
            update_body: dict[str, Any] = {}

            if subject is not None:
                update_body["subject"] = subject
            if start_time is not None:
                update_body["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                }
            if end_time is not None:
                update_body["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                }
            if location is not None:
                update_body["location"] = {"displayName": location}
            if body is not None:
                update_body["body"] = {
                    "contentType": "html",
                    "content": body,
                }

            if not update_body:
                logger.warning("No fields to update for event")
                return False

            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).events.by_event_id(event_id).patch(body=update_body)

            self._log_operation(
                "calendar_update_event",
                {"event_id": event_id, "fields_updated": list(update_body.keys())},
            )

            return True

        except Exception as e:
            self._log_error("calendar_update_event", e, {"event_id": event_id})
            raise

    async def cancel_event(
        self,
        event_id: str,
        comment: str = "",
    ) -> bool:
        """Cancel an event and notify attendees.

        Args:
            event_id: ID of the event to cancel
            comment: Optional cancellation message

        Returns:
            True if cancelled successfully
        """
        await self._rate_limit()

        try:
            await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).events.by_event_id(event_id).cancel.post(
                body={"comment": comment}
            )

            self._log_operation(
                "calendar_cancel_event",
                {"event_id": event_id},
            )

            return True

        except Exception as e:
            self._log_error("calendar_cancel_event", e, {"event_id": event_id})
            raise

    async def list_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """List calendar events.

        Args:
            start_date: Filter events starting from this date
            end_date: Filter events ending before this date
            count: Maximum number of events to return

        Returns:
            List of event info dictionaries
        """
        await self._rate_limit()

        try:
            query_params: dict[str, Any] = {
                "top": count,
                "orderby": "start/dateTime",
                "select": (
                    "id,subject,start,end,location,isOnlineMeeting,"
                    "attendees,organizer,isCancelled"
                ),
            }

            # Build filter for date range
            filters: list[str] = []
            if start_date:
                filters.append(f"start/dateTime ge '{start_date.isoformat()}'")
            if end_date:
                filters.append(f"end/dateTime le '{end_date.isoformat()}'")
            if filters:
                query_params["filter"] = " and ".join(filters)

            events = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).calendar.events.get(
                request_configuration={"query_parameters": query_params}
            )

            self._log_operation(
                "calendar_list_events",
                {"count": len(events.value or [])},
            )

            return [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "start": e.start.date_time if e.start else None,
                    "end": e.end.date_time if e.end else None,
                    "location": (
                        e.location.display_name if e.location else None
                    ),
                    "is_online": e.is_online_meeting,
                    "is_cancelled": e.is_cancelled,
                    "attendee_count": len(e.attendees or []),
                }
                for e in (events.value or [])
            ]

        except Exception as e:
            self._log_error("calendar_list_events", e)
            raise

    async def get_free_busy(
        self,
        attendees: list[str],
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get free/busy information for attendees.

        Args:
            attendees: List of attendee email addresses
            start_time: Start of time range to check
            end_time: End of time range to check

        Returns:
            Dictionary mapping attendee to list of busy time slots
        """
        # Validate all attendees are internal
        valid_attendees = self.validate_recipients(attendees)

        if not valid_attendees:
            return {}

        await self._rate_limit()

        try:
            result = await self.client.graph.users.by_user_id(
                self.worker.entra_object_id
            ).calendar.get_schedule.post(
                body={
                    "schedules": valid_attendees,
                    "startTime": {
                        "dateTime": start_time.isoformat(),
                        "timeZone": "UTC",
                    },
                    "endTime": {
                        "dateTime": end_time.isoformat(),
                        "timeZone": "UTC",
                    },
                    "availabilityViewInterval": 30,
                }
            )

            self._log_operation(
                "calendar_get_free_busy",
                {"attendees": valid_attendees},
            )

            return {
                schedule.schedule_id: [
                    {
                        "start": item.start.date_time if item.start else None,
                        "end": item.end.date_time if item.end else None,
                        "status": item.status,
                    }
                    for item in (schedule.schedule_items or [])
                ]
                for schedule in (result.value or [])
            }

        except Exception as e:
            self._log_error("calendar_get_free_busy", e)
            raise
