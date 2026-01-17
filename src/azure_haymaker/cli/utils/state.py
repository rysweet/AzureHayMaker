"""State management utilities for the CLI.

Provides wrappers around the DeploymentStateManager for CLI usage.
Small, focused functions following the single-responsibility principle.

Addresses Issue #22: Refactor long CLI methods.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from azure_haymaker.knowledge_worker.state_manager import DeploymentStateManager

from ..constants import DURATION_UNITS


def get_state_manager() -> DeploymentStateManager:
    """Get a DeploymentStateManager instance.

    Uses HAYMAKER_STATE_DIR environment variable if set,
    otherwise uses default ~/.azure_haymaker.

    Returns:
        Configured DeploymentStateManager
    """
    state_dir = os.environ.get("HAYMAKER_STATE_DIR")
    if state_dir:
        return DeploymentStateManager(Path(state_dir))
    return DeploymentStateManager()


def parse_duration(duration_str: str) -> timedelta:
    """Parse a duration string into a timedelta.

    Supports formats like: 24h, 7d, 30m, 1w

    Args:
        duration_str: Duration string (e.g., "24h", "7d")

    Returns:
        Parsed timedelta

    Raises:
        ValueError: If format is invalid
    """
    pattern = r"^(\d+)([smhdw])$"
    match = re.match(pattern, duration_str.lower())

    if not match:
        valid_units = ", ".join(DURATION_UNITS.keys())
        raise ValueError(
            f"Invalid duration format: {duration_str}. "
            f"Use format like '24h' or '7d'. Valid units: {valid_units}"
        )

    value = int(match.group(1))
    unit = match.group(2)

    seconds = value * DURATION_UNITS[unit]
    return timedelta(seconds=seconds)


def filter_deployments_by_age(
    deployments: list[dict[str, Any]], max_age: timedelta
) -> list[dict[str, Any]]:
    """Filter deployments older than a given age.

    Args:
        deployments: List of deployment dictionaries
        max_age: Maximum age (deployments older than this are included)

    Returns:
        Filtered list of deployments
    """
    now = datetime.now()
    result = []

    for deployment in deployments:
        started_at_str = deployment.get("started_at")
        if not started_at_str:
            continue

        # Parse ISO format
        started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
        # Make naive for comparison
        if started_at.tzinfo:
            started_at = started_at.replace(tzinfo=None)

        age = now - started_at
        if age > max_age:
            result.append(deployment)

    return result


def get_deployment_or_exit(run_id: str) -> dict[str, Any]:
    """Get a deployment by run_id, or raise an error.

    Args:
        run_id: Deployment run ID

    Returns:
        Deployment dictionary

    Raises:
        click.ClickException: If deployment not found
    """
    import click

    state_manager = get_state_manager()
    deployment = state_manager.load_deployment(run_id)

    if not deployment:
        raise click.ClickException(f"Deployment not found: {run_id}")

    return deployment


def get_workers_for_deployment(run_id: str) -> list[dict[str, Any]]:
    """Get all workers for a deployment.

    Args:
        run_id: Deployment run ID

    Returns:
        List of worker dictionaries
    """
    state_manager = get_state_manager()
    return state_manager.load_workers(run_id)


def get_log_path(run_id: str) -> Path:
    """Get the log directory path for a deployment.

    Args:
        run_id: Deployment run ID

    Returns:
        Path to log directory
    """
    state_manager = get_state_manager()
    return state_manager.state_dir / "logs" / run_id


__all__ = [
    "get_state_manager",
    "parse_duration",
    "filter_deployments_by_age",
    "get_deployment_or_exit",
    "get_workers_for_deployment",
    "get_log_path",
]
