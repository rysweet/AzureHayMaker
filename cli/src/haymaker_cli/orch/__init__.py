"""Orchestrator CLI commands for Azure Container Apps management.

This package provides CLI commands for managing and monitoring Azure Container Apps
used by the HayMaker orchestrator.

Public API:
    Models:
        - ContainerAppInfo: Container App information
        - RevisionInfo: Revision information
        - ReplicaInfo: Replica information
        - HealthCheckResult: Health check results
        - OrchClientError: Base exception class
        - ConfigError: Configuration errors (exit code 1)
        - NetworkError: Network errors (exit code 2)
        - ApiError: API errors (exit code 3)
        - ServerError: Server errors (exit code 4)

    Configuration:
        - OrchestratorConfig: Configuration model
        - load_orchestrator_config: Load configuration
        - save_orchestrator_config: Save configuration
        - set_orchestrator_config_value: Set single config value
        - get_orchestrator_config_value: Get single config value

    Client:
        - ContainerAppsClient: Azure Container Apps API wrapper

    Formatters:
        - format_container_app_status: Format app status with revisions
        - format_replicas: Format replicas table
        - format_logs: Format log entries with colors
        - format_health_results: Format health check results
        - format_health_check_result: Format HealthCheckResult model
        - format_json: Format as JSON (re-exported from formatters)
        - format_yaml: Format as YAML (re-exported from formatters)

    Health Checks:
        - check_container_app_status: Check app status
        - check_endpoint_connectivity: Check DNS/TCP connectivity
        - check_replica_health: Check replica health
        - check_http_health_endpoint: Deep HTTP health check
        - run_health_checks: Run all checks in parallel

    Commands:
        - orch: Main CLI command group (import separately to avoid circular deps)

Example:
    >>> from haymaker_cli.orch import (
    ...     ContainerAppsClient,
    ...     load_orchestrator_config,
    ...     run_health_checks
    ... )
    >>> config = load_orchestrator_config()  # doctest: +SKIP
    >>> client = ContainerAppsClient(
    ...     config.subscription_id,
    ...     config.resource_group
    ... )  # doctest: +SKIP
    >>> app = await client.get_container_app("my-app")  # doctest: +SKIP
    >>> results = await run_health_checks(client, "my-app")  # doctest: +SKIP
"""

from haymaker_cli.orch.client import ContainerAppsClient
from haymaker_cli.orch.config import (
    OrchestratorConfig,
    get_orchestrator_config_value,
    load_orchestrator_config,
    save_orchestrator_config,
    set_orchestrator_config_value,
)
from haymaker_cli.orch.formatters import (
    format_container_app_status,
    format_health_check_result,
    format_health_results,
    format_json,
    format_logs,
    format_replicas,
    format_yaml,
)
from haymaker_cli.orch.health import (
    check_container_app_status,
    check_endpoint_connectivity,
    check_http_health_endpoint,
    check_replica_health,
    run_health_checks,
)
from haymaker_cli.orch.models import (
    ApiError,
    ConfigError,
    ContainerAppInfo,
    HealthCheckResult,
    NetworkError,
    OrchClientError,
    ReplicaInfo,
    RevisionInfo,
    ServerError,
)

__all__ = [
    # Models
    "ContainerAppInfo",
    "RevisionInfo",
    "ReplicaInfo",
    "HealthCheckResult",
    "OrchClientError",
    "ConfigError",
    "NetworkError",
    "ApiError",
    "ServerError",
    # Configuration
    "OrchestratorConfig",
    "load_orchestrator_config",
    "save_orchestrator_config",
    "set_orchestrator_config_value",
    "get_orchestrator_config_value",
    # Client
    "ContainerAppsClient",
    # Formatters
    "format_container_app_status",
    "format_replicas",
    "format_logs",
    "format_health_results",
    "format_health_check_result",
    "format_json",
    "format_yaml",
    # Health Checks
    "check_container_app_status",
    "check_endpoint_connectivity",
    "check_replica_health",
    "check_http_health_endpoint",
    "run_health_checks",
]
