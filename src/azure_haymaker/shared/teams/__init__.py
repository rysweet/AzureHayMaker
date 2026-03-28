"""Microsoft Teams integration module.

Provides Teams team creation, member management, channel setup,
and messaging via Microsoft Graph API. Domain-independent and
usable by any Azure HayMaker component.

Public API:
    TeamsIntegration: Main integration class
    TeamsIntegrationError: Exception for Teams operations

Example:
    >>> from azure_haymaker.shared.teams import TeamsIntegration
    >>> teams = TeamsIntegration(graph_client, run_id="haymaker-001")
    >>> result = await teams.setup_team(...)
"""

from azure_haymaker.shared.teams.integration import (
    TeamsIntegration,
    TeamsIntegrationError,
)

__all__ = [
    "TeamsIntegration",
    "TeamsIntegrationError",
]
