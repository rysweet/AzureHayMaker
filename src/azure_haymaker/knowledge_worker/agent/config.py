"""Configuration module for knowledge worker agents.

This module provides configuration management and worker identity construction
following the Bricks & Studs pattern. It is self-contained with no external
dependencies beyond the standard library.

Philosophy:
- Single responsibility: Configuration and identity management
- Standard library only (dataclasses, logging, no M365 dependencies)
- Self-contained and regeneratable
- No business logic - pure data structures and simple transformations

Public API (the "studs"):
    KnowledgeWorkerConfig: Configuration dataclass extending AgentConfig
    build_worker_identity: Factory function to construct WorkerIdentity from config

Usage:
    >>> from azure_haymaker.knowledge_worker.agent.config import (
    ...     KnowledgeWorkerConfig,
    ...     build_worker_identity,
    ... )
    >>> config = KnowledgeWorkerConfig(
    ...     worker_id="kw-abc12345-engi-001",
    ...     display_name="Alex Developer",
    ...     department="engineering",
    ...     persona="engineering",
    ...     tenant_domain="tenant.onmicrosoft.com",
    ... )
    >>> identity = build_worker_identity(config)
    >>> print(f"Worker: {identity.display_name}")
    Worker: Alex Developer

Module Structure:
    - KnowledgeWorkerConfig: Extends AgentConfig with worker-specific fields
    - build_worker_identity(): Converts config to WorkerIdentity model
    - Auto-generation of name/goal from worker_id/display_name
    - Enum mapping for persona and endpoint_type

Dependencies:
    - dataclasses (standard library)
    - logging (standard library)
    - azure_haymaker.agent_base.AgentConfig (parent config)
    - azure_haymaker.knowledge_worker.models.worker (data models)

See Also:
    - core.py: Core agent lifecycle management
    - m365_integration.py: M365 API integration
    - README.md: Module overview and quick start
"""

import logging
from dataclasses import dataclass, field

from azure_haymaker.agent_base import AgentConfig
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerIdentity,
    WorkerPersona,
)

logger = logging.getLogger(__name__)

__all__ = ["KnowledgeWorkerConfig", "build_worker_identity"]


@dataclass
class KnowledgeWorkerConfig(AgentConfig):
    """Configuration for a knowledge worker agent.

    Extends AgentConfig with knowledge worker-specific settings
    including identity, team membership, and M365 credentials.

    Attributes:
        name: Agent name (auto-generated from worker_id if empty)
        goal: Agent goal (auto-generated from display_name if empty)
        worker_id: Unique worker identifier
        display_name: Display name in Entra
        department: Department/team name
        persona: Worker persona type
        team_id: ID of the worker's team
        team_name: Name of the worker's team
        activity_types: List of activity types to perform
        activity_frequency_minutes: Base interval between activities
        endpoint_type: Type of endpoint (cloud_pc or cli_container)
        endpoint_id: ID of assigned endpoint
        m365_app_id: M365 application client ID
        m365_cert_thumbprint: Certificate thumbprint for auth
        tenant_domain: M365 tenant domain
    """

    # Override parent required fields with defaults (populated in __post_init__)
    name: str = ""
    goal: str = ""

    # Worker identity
    worker_id: str = ""
    display_name: str = ""
    department: str = ""
    persona: str = ""

    # Team membership
    team_id: str = ""
    team_name: str = ""

    # Activity configuration
    activity_types: list[str] = field(default_factory=list)
    activity_frequency_minutes: int = 30

    # Endpoint configuration
    endpoint_type: str = "cli_container"  # "cli_container" or "cloud_pc"
    endpoint_id: str = ""

    # M365 credentials
    m365_app_id: str = ""
    m365_cert_thumbprint: str = ""
    tenant_domain: str = ""

    def __post_init__(self) -> None:
        """Set default name and goal if not provided."""
        if not self.name:
            self.name = f"knowledge-worker-{self.worker_id}"
        if not self.goal:
            self.goal = f"Perform M365 activities as {self.display_name or self.worker_id}"


def build_worker_identity(config: KnowledgeWorkerConfig) -> WorkerIdentity:
    """Build WorkerIdentity from configuration.

    Args:
        config: Knowledge worker configuration

    Returns:
        WorkerIdentity model populated from config
    """
    # Map persona string to enum
    try:
        persona = WorkerPersona(config.persona.lower())
    except ValueError:
        logger.warning(
            f"Unknown persona '{config.persona}', defaulting to ENGINEERING"
        )
        persona = WorkerPersona.ENGINEERING

    # Map endpoint type string to enum
    try:
        endpoint_type = EndpointType(config.endpoint_type.lower())
    except ValueError:
        endpoint_type = EndpointType.CLI_CONTAINER

    return WorkerIdentity(
        worker_id=config.worker_id,
        display_name=config.display_name,
        user_principal_name="",  # Set during provisioning
        department=config.department,
        persona=persona,
        endpoint_type=endpoint_type,
        endpoint_id=config.endpoint_id,
        team_ids=[config.team_id] if config.team_id else [],
    )
