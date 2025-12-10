"""Example: Knowledge Worker deployment with AI-generated emails and markers.

This example demonstrates how to configure Knowledge Worker deployments with:
1. Email markers for tracking and analytics
2. AI-generated email content using Claude (Anthropic)
3. Custom directives per department (e.g., limericks in signatures)

Requirements:
    - KW_TENANT_ID: Azure AD tenant ID
    - KW_APP_ID: Application client ID with Graph permissions
    - KW_CLIENT_SECRET: Client secret
    - ANTHROPIC_API_KEY: Anthropic API key for Claude (if AI generation enabled)

Usage:
    python examples/ai_email_deployment.py
"""

import asyncio
import logging
import os

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

from azure_haymaker.knowledge_worker.content import EmailGenerationConfig
from azure_haymaker.knowledge_worker.orchestrator import (
    DeploymentConfig,
    KnowledgeWorkerOrchestrator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run Knowledge Worker deployment with AI-generated emails."""

    # Configuration: AI Email Generation with Limericks
    # This configuration enables AI-generated emails with a fun directive
    # to include limericks about working in the age of AI
    config = DeploymentConfig(
        name="ai-email-demo",
        total_workers=5,
        departments={
            "engineering": {
                "count": 3,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 6,
                    "teams_messages_per_hour": 15,
                    "documents_per_day": 5,
                    "meetings_per_day": 4,
                },
            },
            "marketing": {
                "count": 2,
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 8,
                    "teams_messages_per_hour": 20,
                    "documents_per_day": 3,
                    "meetings_per_day": 3,
                },
            },
        },
        duration_hours=1,  # Run for 1 hour for demo
        tenant_domain=os.environ["KW_TENANT_DOMAIN"],
        # Email markers enabled by default
        email_markers_enabled=True,
        marker_format="MARKER",
        marker_style="subject",  # Options: "subject", "hidden", "both"
        # AI email generation with custom directive
        email_generation=EmailGenerationConfig(
            enabled=True,  # Enable AI generation
            # api_key will use ANTHROPIC_API_KEY env var if not specified
            # model defaults to Anthropic SDK default (sonnet)
            directive=(
                "Include a humorous limerick about working in the age of AI "
                "in your email signature. The limerick should be clever, lighthearted, "
                "and relate to the email's content or workplace context."
            ),
            max_tokens=1024,
            temperature=0.7,
            timeout_seconds=30,
        ),
    )

    # Initialize Graph client
    tenant_id = os.environ["KW_TENANT_ID"]
    app_id = os.environ["KW_APP_ID"]
    client_secret = os.environ["KW_CLIENT_SECRET"]

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=app_id,
        client_secret=client_secret,
    )

    graph_client = GraphServiceClient(credentials=credential)

    # Create orchestrator with config
    orchestrator = KnowledgeWorkerOrchestrator(graph_client, config)

    logger.info("=" * 80)
    logger.info("Knowledge Worker Deployment - AI Email Generation with Limericks")
    logger.info("=" * 80)
    logger.info(f"Workers: {config.total_workers}")
    logger.info(f"Departments: {list(config.departments.keys())}")
    logger.info(f"Duration: {config.duration_hours} hour(s)")
    logger.info(f"Email markers: {config.email_markers_enabled}")
    logger.info(f"AI generation: {config.email_generation.enabled}")
    logger.info(f"Custom directive: {config.email_generation.directive[:50]}...")
    logger.info("=" * 80)

    # Create and start deployment
    run_id = orchestrator.create_deployment(config)
    logger.info(f"Created deployment: {run_id}")

    success = await orchestrator.start_deployment(run_id)

    if success:
        logger.info("Deployment started successfully")
        logger.info("Workers will now generate AI-powered emails with limericks")
        logger.info("Email markers will be added for tracking")

        # Wait for deployment to complete
        # In production, you would monitor status and handle completion
        await asyncio.sleep(config.duration_hours * 3600)

        # Stop deployment
        await orchestrator.stop_deployment(run_id)
        logger.info("Deployment stopped")

        # Cleanup
        await orchestrator.cleanup_deployment(run_id)
        logger.info("Deployment cleanup complete")

    else:
        logger.error("Failed to start deployment")


# Example configurations for different scenarios
def example_markers_only() -> DeploymentConfig:
    """Example: Email markers without AI generation (fallback content)."""
    return DeploymentConfig(
        name="markers-only",
        total_workers=3,
        duration_hours=1,
        tenant_domain=os.environ["KW_TENANT_DOMAIN"],
        # Markers enabled, AI disabled
        email_markers_enabled=True,
        marker_format="TRACK",
        marker_style="both",  # Both subject and hidden markers
        email_generation=EmailGenerationConfig(enabled=False),
    )


def example_per_department_directives() -> DeploymentConfig:
    """Example: Different directives per department (future enhancement).

    Note: Current implementation uses a single directive for all departments.
    This example shows the intended future design.
    """
    return DeploymentConfig(
        name="dept-specific",
        total_workers=6,
        departments={
            "engineering": {
                "count": 2,
                "activity": {"email_per_hour": 5},
                # Future: Per-department directives
                # "email_directive": "Include technical jargon and code references"
            },
            "marketing": {
                "count": 2,
                "activity": {"email_per_hour": 8},
                # Future: Per-department directives
                # "email_directive": "Use marketing buzzwords and enthusiasm"
            },
            "finance": {
                "count": 2,
                "activity": {"email_per_hour": 4},
                # Future: Per-department directives
                # "email_directive": "Include financial metrics and ROI discussions"
            },
        },
        duration_hours=1,
        tenant_domain=os.environ["KW_TENANT_DOMAIN"],
        email_markers_enabled=True,
        email_generation=EmailGenerationConfig(
            enabled=True,
            directive="Tailor your email to your department's communication style",
        ),
    )


def example_hidden_markers_analytics() -> DeploymentConfig:
    """Example: Hidden markers for stealth analytics."""
    return DeploymentConfig(
        name="stealth-analytics",
        total_workers=10,
        duration_hours=8,
        tenant_domain=os.environ["KW_TENANT_DOMAIN"],
        # Hidden markers only (not visible in subject)
        email_markers_enabled=True,
        marker_format="ANALYTICS",
        marker_style="hidden",  # Only in HTML comments
        email_generation=EmailGenerationConfig(
            enabled=True,
            directive="Write natural, professional emails that blend in with normal traffic",
            temperature=0.8,  # Higher temperature for more variety
        ),
    )


if __name__ == "__main__":
    # Check required environment variables
    required_vars = [
        "KW_TENANT_ID",
        "KW_APP_ID",
        "KW_CLIENT_SECRET",
        "KW_TENANT_DOMAIN",
        "ANTHROPIC_API_KEY",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before running this example")
        exit(1)

    # Run the example
    asyncio.run(main())
