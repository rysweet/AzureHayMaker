"""Knowledge Worker Activity Framework for Azure HayMaker.

This module provides infrastructure for simulating knowledge workers performing
everyday M365 activities (email, Teams, documents, calendar) to generate
realistic benign telemetry for cybersecurity analysis.

Key Components:
- KnowledgeWorkerAgent: Base class for worker activity agents
- KnowledgeWorkerOrchestrator: Deployment coordination
- Models: WorkerIdentity, Team, WorkerConfig, etc.
- Operations: Email, Teams, Documents, Calendar M365 operations
- Identity: Entra user/group management
- Endpoints: Cloud PC and CLI container provisioning
- Cleanup: Resource tracking and cleanup management
"""

from azure_haymaker.knowledge_worker.agent import (
    KnowledgeWorkerAgent,
    KnowledgeWorkerConfig,
)
from azure_haymaker.knowledge_worker.m365_client import (
    M365Client,
    M365ClientConfig,
    M365ClientFactory,
)
from azure_haymaker.knowledge_worker.models.team import (
    Team,
    TeamConfig,
)
from azure_haymaker.knowledge_worker.models.worker import (
    EndpointType,
    WorkerConfig,
    WorkerIdentity,
    WorkerPersona,
)
from azure_haymaker.knowledge_worker.orchestrator import (
    DeploymentConfig,
    DeploymentPhase,
    DeploymentState,
    DeploymentStatus,
    KnowledgeWorkerOrchestrator,
)

__all__ = [
    # Agent
    "KnowledgeWorkerAgent",
    "KnowledgeWorkerConfig",
    # M365 Client
    "M365Client",
    "M365ClientConfig",
    "M365ClientFactory",
    # Orchestrator
    "DeploymentConfig",
    "DeploymentPhase",
    "DeploymentState",
    "DeploymentStatus",
    "KnowledgeWorkerOrchestrator",
    # Worker models
    "EndpointType",
    "WorkerConfig",
    "WorkerIdentity",
    "WorkerPersona",
    # Team models
    "Team",
    "TeamConfig",
]
