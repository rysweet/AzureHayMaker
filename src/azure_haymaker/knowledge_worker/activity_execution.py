"""Activity execution service for knowledge workers.

This module handles the execution of worker activities including
email sending and calendar event creation.

Philosophy:
- Single responsibility: Activity execution
- Async task management for worker activities
- Coordinates with email content service
"""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from azure_haymaker.knowledge_worker.agent import KnowledgeWorkerAgent
from azure_haymaker.knowledge_worker.email_content_service import EmailContentService

logger = logging.getLogger(__name__)


class ActivityExecutionService:
    """Handles execution of worker activities.

    Manages the activity loop for workers, generating and executing
    email and calendar activities at configured intervals.

    Example:
        >>> service = ActivityExecutionService(email_content_service)
        >>> await service.run_worker(worker, duration_hours=8)
    """

    def __init__(self, email_content_service: EmailContentService) -> None:
        """Initialize the activity execution service.

        Args:
            email_content_service: Service for generating email content
        """
        self._email_content_service = email_content_service

    async def run_worker(
        self,
        worker: KnowledgeWorkerAgent,
        duration_hours: int,
    ) -> None:
        """Run worker with M365 operations.

        Args:
            worker: Worker agent
            duration_hours: How long to run
        """
        worker_id = worker.worker_config.worker_id

        try:
            logger.info(f"Worker {worker_id} starting M365 operations")

            # Initialize the worker (creates M365 client)
            worker.on_start()

            # Run activity loop
            await self.run_activity_loop(worker, duration_hours)

            # Cleanup
            worker.on_cleanup(0)

            logger.info(f"Worker {worker_id} completed M365 operations")

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
            worker.on_cleanup(1)
            raise
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            logger.error(f"Worker {worker_id} exception details:", exc_info=True)
            worker.on_cleanup(1)

    async def run_activity_loop(
        self,
        worker: KnowledgeWorkerAgent,
        duration_hours: int,
    ) -> None:
        """Run the activity generation loop for a worker.

        Generates and executes activities at configured intervals.

        Args:
            worker: Worker agent with initialized M365 client
            duration_hours: How long to run (in hours)
        """
        worker_id = worker.worker_config.worker_id
        config = worker.activity_config

        end_time = datetime.now(UTC) + timedelta(hours=duration_hours)
        activity_count = 0

        # Calculate base interval (in seconds) from emails_per_hour
        base_interval = 3600.0 / max(config.email_per_hour, 1)

        while datetime.now(UTC) < end_time:
            try:
                # Add variance to interval (50-150% of base)
                interval = base_interval * random.uniform(0.5, 1.5)

                # Pick random activity type
                activity_type = random.choice(["email", "calendar"])

                if activity_type == "email":
                    await self._execute_email_activity(worker, activity_count)
                elif activity_type == "calendar":
                    await self._execute_calendar_activity(worker, activity_count)

                activity_count += 1

                # Wait before next activity
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Worker {worker_id} activity error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

        logger.info(f"Worker {worker_id} completed {activity_count} activities")

    async def _execute_email_activity(
        self,
        worker: KnowledgeWorkerAgent,
        activity_count: int,
    ) -> None:
        """Execute an email activity.

        Args:
            worker: Worker agent
            activity_count: Current activity count
        """
        worker_id = worker.worker_config.worker_id

        # Generate and send email to a random allowed recipient
        recipients = worker.get_allowed_recipients()
        if not recipients:
            logger.debug(f"Worker {worker_id}: no recipients available")
            return

        to = [random.choice(recipients)]

        # Generate email content
        email_content = await self._email_content_service.generate_email_content(
            worker_id=worker_id,
            activity_count=activity_count,
            recipient=to[0],
            department=worker.worker_config.department,
        )

        await worker.send_email(to=to, subject=email_content.subject, body=email_content.body)
        logger.info(f"Worker {worker_id} sent email to {to[0]}")

    async def _execute_calendar_activity(
        self,
        worker: KnowledgeWorkerAgent,
        activity_count: int,
    ) -> None:
        """Execute a calendar activity.

        Args:
            worker: Worker agent
            activity_count: Current activity count
        """
        worker_id = worker.worker_config.worker_id

        # Create a calendar event
        start = datetime.now(UTC) + timedelta(hours=1)
        end = start + timedelta(minutes=30)

        await worker.create_calendar_event(
            subject=f"Meeting {activity_count + 1}",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            body="Automated meeting created by KW agent",
        )
        logger.info(f"Worker {worker_id} created calendar event")


__all__ = ["ActivityExecutionService"]
