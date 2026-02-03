"""KW deploy command - Create a new Knowledge Worker deployment.

Deploys simulated knowledge workers that perform M365 activities
(email, Teams, calendar, documents).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import click

from ...constants import DEFAULT_OUTPUT_FORMAT, EXIT_ERROR
from ...utils.output import format_json
from ...utils.state import get_state_manager


@click.command()
@click.option(
    "--name",
    "-n",
    default=None,
    help="Deployment name (auto-generated if not provided)",
)
@click.option(
    "--workers",
    "-w",
    type=click.IntRange(min=1),
    default=10,
    help="Number of workers to deploy (minimum 1)",
)
@click.option(
    "--department",
    "-d",
    default="engineering",
    help="Department name for workers",
)
@click.option(
    "--duration",
    type=click.IntRange(min=1),
    default=8,
    help="Duration in hours for worker activities (minimum 1)",
)
@click.option(
    "--tenant-domain",
    help="M365 tenant domain (e.g., contoso.onmicrosoft.com)",
)
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Load deployment config from YAML/JSON file",
)
@click.option(
    "--enable-ai-generation/--no-ai-generation",
    default=False,
    help="Enable AI-powered email content generation",
)
@click.option(
    "--email-directive",
    help="AI directive for email generation (e.g., 'Write as limericks')",
)
@click.option(
    "--marker-format",
    default="MARKER",
    help="Format for email markers (e.g., MARKER, TAG, LIMERICK)",
)
@click.option(
    "--start/--no-start",
    default=True,
    help="Start the deployment immediately after creation",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def deploy(
    name: str | None,
    workers: int,
    department: str,
    duration: int,
    tenant_domain: str | None,
    config_file: str | None,
    enable_ai_generation: bool,
    email_directive: str | None,
    marker_format: str,
    start: bool,
    output_format: str,
) -> None:
    """Create a new Knowledge Worker deployment.

    Deploys simulated knowledge workers that perform M365 activities
    (email, Teams, calendar, documents).

    Examples:
        # Deploy 25 workers with AI limerick emails
        haymaker kw deploy --workers 25 --enable-ai-generation \\
            --email-directive "Write all emails as limericks"

        # Deploy from config file
        haymaker kw deploy --config-file deployment.yaml

        # Deploy without starting
        haymaker kw deploy --workers 10 --no-start
    """
    config_dict: dict[str, Any] = {}

    # Load from config file if provided
    if config_file:
        config_dict = _load_config_file(config_file)
        click.echo(f"Loaded configuration from: {config_file}")

    # Override with CLI options (CLI takes precedence)
    if name:
        config_dict["name"] = name
    elif "name" not in config_dict:
        config_dict["name"] = f"kw-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    config_dict["total_workers"] = config_dict.get("total_workers", workers)
    config_dict["duration_hours"] = config_dict.get("duration_hours", duration)

    if tenant_domain:
        config_dict["tenant_domain"] = tenant_domain
    elif "tenant_domain" not in config_dict:
        # Try environment variable
        config_dict["tenant_domain"] = os.environ.get("KW_TENANT_DOMAIN", "")

    # Department config
    if "departments" not in config_dict:
        config_dict["departments"] = {
            department: {
                "count": config_dict["total_workers"],
                "endpoint_type": "cli_container",
                "activity": {
                    "email_per_hour": 4,
                    "teams_messages_per_hour": 15,
                    "documents_per_day": 5,
                    "meetings_per_day": 4,
                },
            }
        }

    # Email generation config
    if enable_ai_generation or email_directive:
        config_dict["email_generation"] = {
            "enabled": True,
            "directive": email_directive or "Generate professional work emails",
        }

    config_dict["marker_format"] = marker_format

    # Validate required fields
    if not config_dict.get("tenant_domain"):
        click.echo(
            "❌ Error: tenant_domain is required. "
            "Use --tenant-domain or set KW_TENANT_DOMAIN environment variable.",
            err=True,
        )
        sys.exit(EXIT_ERROR)

    # Create deployment
    run_id = _create_deployment(config_dict)

    if output_format == "json":
        click.echo(format_json({"run_id": run_id, "config": config_dict}))
    else:
        click.echo(f"✅ Created deployment: {run_id}")
        click.echo(f"   Name: {config_dict['name']}")
        click.echo(f"   Workers: {config_dict['total_workers']}")
        click.echo(f"   Duration: {config_dict['duration_hours']} hours")
        click.echo(f"   Tenant: {config_dict['tenant_domain']}")

    # Start if requested
    if start:
        click.echo()
        click.echo("Starting deployment...")
        _start_deployment_async(run_id)
        click.echo(f"✅ Deployment {run_id} started!")
        click.echo()
        click.echo("Monitor with:")
        click.echo(f"  haymaker kw status --run-id {run_id}")
        click.echo(f"  haymaker kw logs --run-id {run_id} --follow")


def _load_config_file(path: str) -> dict[str, Any]:
    """Load deployment configuration from YAML or JSON file.

    Args:
        path: Path to config file

    Returns:
        Configuration dictionary

    Raises:
        SystemExit: On file read or parse errors
    """
    file_path = Path(path)

    # Read file with error handling
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        click.echo(f"❌ Error: Config file is not a valid text file: {path}", err=True)
        sys.exit(EXIT_ERROR)
    except PermissionError:
        click.echo(f"❌ Error: Permission denied reading config file: {path}", err=True)
        sys.exit(EXIT_ERROR)
    except OSError as e:
        click.echo(f"❌ Error: Cannot read config file: {e}", err=True)
        sys.exit(EXIT_ERROR)

    # Parse based on file extension
    if file_path.suffix in (".yaml", ".yml"):
        return _parse_yaml(content, path)
    elif file_path.suffix == ".json":
        return _parse_json(content, path)
    else:
        # Try JSON first, then YAML
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return _parse_yaml(content, path)


def _parse_yaml(content: str, path: str) -> dict[str, Any]:
    """Parse YAML content with error handling."""
    try:
        import yaml

        return yaml.safe_load(content)
    except ImportError:
        click.echo(
            "❌ Error: PyYAML not installed. Install with: pip install pyyaml",
            err=True,
        )
        sys.exit(EXIT_ERROR)
    except Exception as e:
        # Catch yaml.YAMLError and any other YAML parsing errors
        click.echo(f"❌ Error: Invalid YAML in config file {path}: {e}", err=True)
        sys.exit(EXIT_ERROR)


def _parse_json(content: str, path: str) -> dict[str, Any]:
    """Parse JSON content with error handling."""
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON in config file {path}: {e}", err=True)
        sys.exit(EXIT_ERROR)


def _create_deployment(config_dict: dict[str, Any]) -> str:
    """Create a deployment and persist to state.

    Args:
        config_dict: Deployment configuration

    Returns:
        Run ID
    """
    state_manager = get_state_manager()

    run_id = f"kw-{uuid4().hex[:8]}"
    name = config_dict.get("name", run_id)

    state_manager.save_deployment(
        run_id=run_id,
        name=name,
        phase="initializing",
        status="pending",
        worker_count=0,
        config=config_dict,
    )

    return run_id


def _start_deployment_async(run_id: str) -> None:
    """Start a deployment asynchronously.

    This updates the state to 'running' and would trigger
    the actual orchestration in a full implementation.
    """
    state_manager = get_state_manager()
    deployment = state_manager.get_deployment(run_id)

    if not deployment:
        click.echo(f"❌ Deployment not found: {run_id}", err=True)
        sys.exit(EXIT_ERROR)

    # Update state
    state_manager.save_deployment(
        run_id=run_id,
        name=deployment.get("name", run_id),
        phase="executing",
        status="running",
        worker_count=deployment.get("config", {}).get("total_workers", 0),
        config=deployment.get("config", {}),
    )
