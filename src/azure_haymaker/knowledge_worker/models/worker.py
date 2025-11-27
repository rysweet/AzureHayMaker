"""Worker identity and configuration models.

Defines the core data structures for simulated knowledge workers including
their identity, persona, and activity configuration.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkerPersona(str, Enum):
    """Knowledge worker persona types.

    Each persona has characteristic activity patterns that influence
    email frequency, Teams usage, document creation, and meeting schedules.
    """

    EXECUTIVE = "executive"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    HR = "hr"
    FINANCE = "finance"
    SALES = "sales"
    OPERATIONS = "operations"
    MARKETING = "marketing"


class EndpointType(str, Enum):
    """Endpoint type for worker activity.

    Workers can execute activities from either:
    - CLOUD_PC: Windows 365 Cloud PC for rich desktop telemetry
    - WINDOWS_VM: Azure Windows VM fallback for Computer Use Agents
    - CLI_CONTAINER: M365 CLI container for cost-efficient API-only activity
    """

    CLOUD_PC = "cloud_pc"
    WINDOWS_VM = "windows_vm"
    CLI_CONTAINER = "cli_container"


class WorkerIdentity(BaseModel):
    """Identity of a simulated knowledge worker.

    Represents a worker's Entra ID identity and associated metadata
    for M365 activity simulation.

    Attributes:
        worker_id: Unique identifier for this worker
        display_name: Human-readable name shown in Entra and M365
        user_principal_name: UPN for M365 authentication
        department: Department/team classification
        persona: Worker persona type influencing activity patterns
        entra_object_id: Entra ID object ID after provisioning
        endpoint_type: Type of endpoint assigned to this worker
        endpoint_id: ID of assigned endpoint (Cloud PC or container)
        team_ids: List of M365 Teams team IDs the worker belongs to
        security_group_ids: List of Entra security group IDs
        created_at: Timestamp when worker was created
        last_activity_at: Timestamp of most recent activity
    """

    worker_id: str = Field(..., description="Unique worker identifier")
    display_name: str = Field(..., description="Display name in Entra")
    user_principal_name: str = Field(..., description="UPN for M365 login")
    department: str = Field(..., description="Department/team name")
    persona: WorkerPersona = Field(..., description="Worker persona type")

    # Entra identifiers
    entra_object_id: str = Field(default="", description="Entra object ID")

    # Endpoint assignment
    endpoint_type: EndpointType = Field(
        default=EndpointType.CLI_CONTAINER,
        description="Type of endpoint for this worker",
    )
    endpoint_id: str = Field(default="", description="Assigned endpoint ID")

    # Team membership
    team_ids: list[str] = Field(default_factory=list)
    security_group_ids: list[str] = Field(default_factory=list)

    # Tracking
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    last_activity_at: datetime | None = Field(
        default=None, description="Last activity timestamp"
    )

    model_config = {
        "use_enum_values": False,
        "validate_assignment": True,
    }


class WorkerConfig(BaseModel):
    """Configuration for worker activity patterns.

    Defines the frequency and timing of M365 activities for a worker.
    Used to generate realistic, varied activity patterns.

    Attributes:
        email_per_hour: Average emails to send per hour
        teams_messages_per_hour: Average Teams messages per hour
        documents_per_day: Average documents to create per day
        meetings_per_day: Average meetings to create/attend per day
        activity_variance_percent: Random variation in activity frequency
        work_start_hour: Start of working hours (UTC)
        work_end_hour: End of working hours (UTC)
        preferred_communication: Primary communication channel (email or teams)
    """

    # Activity frequency
    email_per_hour: int = Field(default=5, ge=0, le=50)
    teams_messages_per_hour: int = Field(default=10, ge=0, le=100)
    documents_per_day: int = Field(default=3, ge=0, le=20)
    meetings_per_day: int = Field(default=4, ge=0, le=15)

    # Activity variation
    activity_variance_percent: int = Field(
        default=30,
        ge=0,
        le=100,
        description="Random variation in activity frequency",
    )

    # Working hours (UTC)
    work_start_hour: int = Field(default=8, ge=0, le=23)
    work_end_hour: int = Field(default=17, ge=0, le=23)

    # Communication preferences
    preferred_communication: str = Field(
        default="teams",
        description="Primary communication channel",
    )

    model_config = {
        "validate_assignment": True,
    }


# Default activity configurations per persona
DEFAULT_PERSONA_CONFIGS: dict[WorkerPersona, WorkerConfig] = {
    WorkerPersona.EXECUTIVE: WorkerConfig(
        email_per_hour=8,
        teams_messages_per_hour=5,
        documents_per_day=2,
        meetings_per_day=6,
        preferred_communication="email",
    ),
    WorkerPersona.LEGAL: WorkerConfig(
        email_per_hour=6,
        teams_messages_per_hour=3,
        documents_per_day=8,
        meetings_per_day=3,
        preferred_communication="email",
    ),
    WorkerPersona.ENGINEERING: WorkerConfig(
        email_per_hour=4,
        teams_messages_per_hour=15,
        documents_per_day=5,
        meetings_per_day=4,
        preferred_communication="teams",
    ),
    WorkerPersona.HR: WorkerConfig(
        email_per_hour=10,
        teams_messages_per_hour=8,
        documents_per_day=4,
        meetings_per_day=5,
        preferred_communication="email",
    ),
    WorkerPersona.FINANCE: WorkerConfig(
        email_per_hour=7,
        teams_messages_per_hour=4,
        documents_per_day=6,
        meetings_per_day=4,
        preferred_communication="email",
    ),
    WorkerPersona.SALES: WorkerConfig(
        email_per_hour=12,
        teams_messages_per_hour=10,
        documents_per_day=3,
        meetings_per_day=8,
        preferred_communication="email",
    ),
    WorkerPersona.OPERATIONS: WorkerConfig(
        email_per_hour=5,
        teams_messages_per_hour=12,
        documents_per_day=4,
        meetings_per_day=3,
        preferred_communication="teams",
    ),
    WorkerPersona.MARKETING: WorkerConfig(
        email_per_hour=8,
        teams_messages_per_hour=8,
        documents_per_day=6,
        meetings_per_day=5,
        preferred_communication="teams",
    ),
}


def get_default_config_for_persona(persona: WorkerPersona) -> WorkerConfig:
    """Get the default activity configuration for a persona.

    Args:
        persona: Worker persona type

    Returns:
        Default WorkerConfig for the persona
    """
    return DEFAULT_PERSONA_CONFIGS.get(persona, WorkerConfig())
