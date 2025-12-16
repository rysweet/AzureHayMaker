"""Team models for Knowledge Worker Activity Framework.

Defines data structures for teams of knowledge workers with shared
context, resources, and communication boundaries.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Team(BaseModel):
    """Team of knowledge workers with shared context.

    Represents a logical team within the simulated organization,
    including Entra security groups, M365 unified groups, and
    Teams team resources.

    Attributes:
        team_id: Unique identifier for this team
        team_name: Human-readable team display name
        department: Department classification
        security_group_id: Entra security group ID for access control
        m365_group_id: M365 unified group ID for collaboration
        teams_team_id: Microsoft Teams team ID
        member_ids: List of worker IDs in this team
        manager_ids: List of worker IDs designated as managers
        allowed_peer_team_ids: Teams allowed for cross-team communication
        sharepoint_site_id: SharePoint site ID for team documents
        shared_mailbox: Shared mailbox address for team email
        created_at: Timestamp when team was created
        run_id: HayMaker run ID that created this team
    """

    team_id: str = Field(..., description="Unique team identifier")
    team_name: str = Field(..., description="Team display name")
    department: str = Field(..., description="Department classification")

    # Entra identifiers
    security_group_id: str = Field(default="", description="Entra security group ID")
    m365_group_id: str = Field(default="", description="M365 unified group ID")
    teams_team_id: str = Field(default="", description="Microsoft Teams team ID")

    # Members
    member_ids: list[str] = Field(default_factory=list)
    manager_ids: list[str] = Field(default_factory=list)

    # Cross-team communication
    allowed_peer_team_ids: list[str] = Field(
        default_factory=list,
        description="Teams allowed for cross-team communication",
    )

    # Shared resources
    sharepoint_site_id: str = Field(default="")
    shared_mailbox: str = Field(default="")

    # Tracking
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    run_id: str = Field(default="", description="HayMaker run ID")

    model_config = {
        "validate_assignment": True,
    }

    @property
    def member_count(self) -> int:
        """Get the number of members in the team."""
        return len(self.member_ids)

    @property
    def manager_count(self) -> int:
        """Get the number of managers in the team."""
        return len(self.manager_ids)

    def is_member(self, worker_id: str) -> bool:
        """Check if a worker is a member of this team.

        Args:
            worker_id: Worker ID to check

        Returns:
            True if worker is a team member
        """
        return worker_id in self.member_ids

    def is_manager(self, worker_id: str) -> bool:
        """Check if a worker is a manager of this team.

        Args:
            worker_id: Worker ID to check

        Returns:
            True if worker is a team manager
        """
        return worker_id in self.manager_ids

    def can_communicate_with_team(self, other_team_id: str) -> bool:
        """Check if cross-team communication is allowed.

        Args:
            other_team_id: ID of the other team

        Returns:
            True if communication is allowed with the other team
        """
        return other_team_id in self.allowed_peer_team_ids


class TeamConfig(BaseModel):
    """Configuration for team creation and management.

    Defines constraints and defaults for creating teams of
    knowledge workers.

    Attributes:
        min_members: Minimum team size
        max_members: Maximum team size
        manager_ratio: Ratio of managers to total members
        cross_team_communication_enabled: Whether cross-team comms are allowed
        max_peer_teams: Maximum number of peer teams for cross-team comms
    """

    # Team size
    min_members: int = Field(default=3, ge=1)
    max_members: int = Field(default=15, le=50)
    manager_ratio: float = Field(default=0.1, ge=0, le=0.5)

    # Cross-team rules
    cross_team_communication_enabled: bool = Field(default=True)
    max_peer_teams: int = Field(default=3, ge=0, le=10)

    model_config = {
        "validate_assignment": True,
    }

    def calculate_manager_count(self, member_count: int) -> int:
        """Calculate number of managers for a given team size.

        Args:
            member_count: Total number of team members

        Returns:
            Number of managers (minimum 1 for teams with 3+ members)
        """
        if member_count < 3:
            return 0
        manager_count = int(member_count * self.manager_ratio)
        return max(1, manager_count)

    def validate_team_size(self, size: int) -> bool:
        """Check if a team size is within configured bounds.

        Args:
            size: Proposed team size

        Returns:
            True if size is valid
        """
        return self.min_members <= size <= self.max_members
