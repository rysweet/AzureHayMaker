"""Click CLI commands for Knowledge Worker management (haymaker kw).

This module provides CLI commands for managing Knowledge Worker simulations
including initialization, provisioning, execution, and cleanup.

Commands:
    - haymaker kw status: Show KW framework status and configuration
    - haymaker kw test: Run a test KW agent locally
    - haymaker kw list-personas: List available worker personas

Example:
    >>> # Show KW framework status
    >>> haymaker kw status

    >>> # Test KW agent locally
    >>> haymaker kw test --persona engineering
"""

import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()


def format_json(data: Any) -> str:
    """Format data as JSON."""
    import json

    return json.dumps(data, indent=2, default=str)


def format_yaml(data: Any) -> str:
    """Format data as YAML."""
    import yaml

    return yaml.dump(data, default_flow_style=False)


@click.group()
def kw():
    """Manage Knowledge Worker simulations.

    Commands for managing Knowledge Worker activity simulations
    that generate M365 telemetry (email, Teams, documents, calendar).

    Examples:
        haymaker kw status
        haymaker kw test --persona engineering
        haymaker kw list-personas
    """


@kw.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.pass_context
def status(ctx: click.Context, output_format: str):
    """Show Knowledge Worker framework status.

    Displays information about the KW framework including:
    - Available modules
    - Configuration status
    - Prerequisites check

    Examples:
        haymaker kw status
        haymaker kw status --format json
    """
    try:
        # Check framework availability
        framework_status = _check_framework_status()

        if output_format == "json":
            console.print(format_json(framework_status))
        elif output_format == "yaml":
            console.print(format_yaml(framework_status))
        else:
            _display_status_table(framework_status)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)


@kw.command("list-personas")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.pass_context
def list_personas(ctx: click.Context, output_format: str):
    """List available worker personas.

    Shows all persona types that can be assigned to knowledge workers,
    along with their default activity patterns.

    Examples:
        haymaker kw list-personas
        haymaker kw list-personas --format json
    """
    try:
        from azure_haymaker.knowledge_worker.models.worker import WorkerPersona

        personas = []
        persona_configs = {
            "executive": {"email_per_hour": 8, "teams_per_hour": 5, "meetings_per_day": 6},
            "legal": {"email_per_hour": 6, "teams_per_hour": 3, "meetings_per_day": 3},
            "engineering": {"email_per_hour": 4, "teams_per_hour": 15, "meetings_per_day": 4},
            "hr": {"email_per_hour": 10, "teams_per_hour": 8, "meetings_per_day": 5},
            "finance": {"email_per_hour": 7, "teams_per_hour": 4, "meetings_per_day": 4},
            "sales": {"email_per_hour": 12, "teams_per_hour": 10, "meetings_per_day": 8},
            "operations": {"email_per_hour": 5, "teams_per_hour": 12, "meetings_per_day": 3},
            "marketing": {"email_per_hour": 8, "teams_per_hour": 8, "meetings_per_day": 5},
        }

        for persona in WorkerPersona:
            config = persona_configs.get(persona.value, {})
            personas.append({
                "name": persona.value,
                "display_name": persona.value.title(),
                "email_per_hour": config.get("email_per_hour", 5),
                "teams_per_hour": config.get("teams_per_hour", 5),
                "meetings_per_day": config.get("meetings_per_day", 4),
            })

        if output_format == "json":
            console.print(format_json(personas))
        elif output_format == "yaml":
            console.print(format_yaml(personas))
        else:
            table = Table(title="Knowledge Worker Personas")
            table.add_column("Persona", style="cyan")
            table.add_column("Email/hr", justify="right")
            table.add_column("Teams/hr", justify="right")
            table.add_column("Meetings/day", justify="right")

            for p in personas:
                table.add_row(
                    p["display_name"],
                    str(p["email_per_hour"]),
                    str(p["teams_per_hour"]),
                    str(p["meetings_per_day"]),
                )

            console.print(table)

    except ImportError as e:
        console.print(f"[red]KW framework not available:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)


@kw.command()
@click.option(
    "--persona",
    type=click.Choice(
        ["executive", "legal", "engineering", "hr", "finance", "sales", "operations", "marketing"],
        case_sensitive=False,
    ),
    default="engineering",
    help="Worker persona to simulate",
)
@click.option(
    "--worker-id",
    default="test-worker-001",
    help="Worker ID for the test agent",
)
@click.option(
    "--display-name",
    default="Test Worker",
    help="Display name for the test agent",
)
@click.option(
    "--tenant-domain",
    default="test.onmicrosoft.com",
    help="Tenant domain for validation",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be executed without running",
)
@click.pass_context
def test(
    ctx: click.Context,
    persona: str,
    worker_id: str,
    display_name: str,
    tenant_domain: str,
    dry_run: bool,
):
    """Test Knowledge Worker agent locally.

    Creates and initializes a KW agent to verify the framework
    is working correctly. Does not connect to M365 - for local
    validation only.

    Examples:
        haymaker kw test
        haymaker kw test --persona sales --worker-id sales-001
        haymaker kw test --dry-run
    """
    try:
        from azure_haymaker.knowledge_worker import (
            KnowledgeWorkerAgent,
            KnowledgeWorkerConfig,
        )

        console.print(f"[cyan]Creating test KW agent...[/cyan]")
        console.print(f"  Worker ID: {worker_id}")
        console.print(f"  Display Name: {display_name}")
        console.print(f"  Persona: {persona}")
        console.print(f"  Tenant Domain: {tenant_domain}")
        console.print()

        # Create configuration
        config = KnowledgeWorkerConfig(
            worker_id=worker_id,
            display_name=display_name,
            department=persona,
            persona=persona,
            tenant_domain=tenant_domain,
        )

        console.print(f"[green]Config created successfully![/green]")
        console.print(f"  name: {config.name}")
        console.print(f"  goal: {config.goal}")

        if dry_run:
            console.print("\n[yellow]Dry run - not creating agent[/yellow]")
            return

        # Create agent
        agent = KnowledgeWorkerAgent(worker_config=config)

        console.print(f"\n[green]Agent created successfully![/green]")
        console.print(f"  Worker Identity: {agent.worker_identity.worker_id}")
        console.print(f"  Persona: {agent.worker_identity.persona.value}")
        console.print(f"  Endpoint Type: {agent.worker_identity.endpoint_type.value}")

        # Get stats (without starting - no M365 connection)
        stats = agent.get_worker_stats()
        console.print(f"\n[cyan]Agent Stats:[/cyan]")
        for key, value in stats.items():
            console.print(f"  {key}: {value}")

        console.print(f"\n[green]KW framework test passed![/green]")

    except ImportError as e:
        console.print(f"[red]KW framework not available:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@kw.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.pass_context
def check(ctx: click.Context, output_format: str):
    """Check KW framework prerequisites.

    Verifies all required components are available:
    - KW module imports
    - Model classes
    - Operation modules
    - Validators

    Examples:
        haymaker kw check
        haymaker kw check --format json
    """
    try:
        checks = []

        # Check core imports
        try:
            from azure_haymaker.knowledge_worker import (
                KnowledgeWorkerAgent,
                KnowledgeWorkerConfig,
            )
            checks.append({"name": "KW Agent", "status": "OK", "details": "Import successful"})
        except ImportError as e:
            checks.append({"name": "KW Agent", "status": "FAIL", "details": str(e)})

        # Check models
        try:
            from azure_haymaker.knowledge_worker.models import (
                WorkerIdentity,
                WorkerPersona,
                EndpointType,
                WorkerConfig,
                Team,
                TeamConfig,
            )
            checks.append({"name": "KW Models", "status": "OK", "details": "All models available"})
        except ImportError as e:
            checks.append({"name": "KW Models", "status": "FAIL", "details": str(e)})

        # Check operations
        try:
            from azure_haymaker.knowledge_worker.operations import (
                EmailOperations,
                TeamsOperations,
                DocumentOperations,
                CalendarOperations,
            )
            checks.append({"name": "KW Operations", "status": "OK", "details": "All operations available"})
        except ImportError as e:
            checks.append({"name": "KW Operations", "status": "FAIL", "details": str(e)})

        # Check validators
        try:
            from azure_haymaker.knowledge_worker.operations.validators import (
                CommunicationValidator,
                ExternalRecipientError,
            )
            checks.append({"name": "KW Validators", "status": "OK", "details": "Validators available"})
        except ImportError as e:
            checks.append({"name": "KW Validators", "status": "FAIL", "details": str(e)})

        # Check identity modules
        try:
            from azure_haymaker.knowledge_worker.identity import (
                EntraUserManager,
                EntraGroupManager,
                TransportRuleManager,
            )
            checks.append({"name": "KW Identity", "status": "OK", "details": "Identity modules available"})
        except ImportError as e:
            checks.append({"name": "KW Identity", "status": "FAIL", "details": str(e)})

        # Check endpoints
        try:
            from azure_haymaker.knowledge_worker.endpoints import (
                EndpointManager,
                M365CLIContainerManager,
                Windows365CloudPCManager,
            )
            checks.append({"name": "KW Endpoints", "status": "OK", "details": "Endpoint managers available"})
        except ImportError as e:
            checks.append({"name": "KW Endpoints", "status": "FAIL", "details": str(e)})

        # Check cleanup
        try:
            from azure_haymaker.knowledge_worker.cleanup import (
                KnowledgeWorkerCleanupManager,
                KnowledgeWorkerResourceInventory,
            )
            checks.append({"name": "KW Cleanup", "status": "OK", "details": "Cleanup manager available"})
        except ImportError as e:
            checks.append({"name": "KW Cleanup", "status": "FAIL", "details": str(e)})

        # Display results
        if output_format == "json":
            console.print(format_json(checks))
        elif output_format == "yaml":
            console.print(format_yaml(checks))
        else:
            table = Table(title="Knowledge Worker Framework Check")
            table.add_column("Component", style="cyan")
            table.add_column("Status")
            table.add_column("Details", max_width=50)

            for check in checks:
                status_style = "green" if check["status"] == "OK" else "red"
                table.add_row(
                    check["name"],
                    f"[{status_style}]{check['status']}[/{status_style}]",
                    check["details"],
                )

            console.print(table)

            # Summary
            ok_count = sum(1 for c in checks if c["status"] == "OK")
            fail_count = sum(1 for c in checks if c["status"] == "FAIL")
            console.print(f"\n[cyan]Summary:[/cyan] {ok_count} OK, {fail_count} FAIL")

            if fail_count > 0:
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        sys.exit(1)


def _check_framework_status() -> dict[str, Any]:
    """Check KW framework status and return details."""
    status = {
        "framework_available": False,
        "modules": {},
        "configuration": {},
    }

    try:
        from azure_haymaker.knowledge_worker import (
            KnowledgeWorkerAgent,
            KnowledgeWorkerConfig,
        )
        status["framework_available"] = True
        status["modules"]["agent"] = True
        status["modules"]["config"] = True
    except ImportError:
        status["modules"]["agent"] = False
        status["modules"]["config"] = False

    try:
        from azure_haymaker.knowledge_worker.models import WorkerPersona
        status["modules"]["models"] = True
        status["persona_count"] = len(list(WorkerPersona))
    except ImportError:
        status["modules"]["models"] = False

    try:
        from azure_haymaker.knowledge_worker.operations import EmailOperations
        status["modules"]["operations"] = True
    except ImportError:
        status["modules"]["operations"] = False

    try:
        from azure_haymaker.knowledge_worker.operations.validators import CommunicationValidator
        status["modules"]["validators"] = True
    except ImportError:
        status["modules"]["validators"] = False

    return status


def _display_status_table(status: dict[str, Any]) -> None:
    """Display status as a formatted table."""
    console.print("[cyan]Knowledge Worker Framework Status[/cyan]\n")

    # Framework status
    if status["framework_available"]:
        console.print("[green]Framework Available[/green]")
    else:
        console.print("[red]Framework Not Available[/red]")

    console.print()

    # Modules table
    table = Table(title="Module Status")
    table.add_column("Module", style="cyan")
    table.add_column("Status")

    for module, available in status.get("modules", {}).items():
        status_str = "[green]Available[/green]" if available else "[red]Missing[/red]"
        table.add_row(module.title(), status_str)

    console.print(table)

    if "persona_count" in status:
        console.print(f"\n[dim]Personas available: {status['persona_count']}[/dim]")


@kw.command()
@click.option(
    "--name",
    default="test-deployment",
    help="Deployment name",
)
@click.option(
    "--workers",
    default=5,
    type=int,
    help="Number of workers to deploy",
)
@click.option(
    "--department",
    type=click.Choice(
        ["executive", "legal", "engineering", "hr", "finance", "sales", "operations", "marketing"],
        case_sensitive=False,
    ),
    default="engineering",
    help="Department for workers",
)
@click.option(
    "--tenant-domain",
    default="test.onmicrosoft.com",
    help="M365 tenant domain",
)
@click.option(
    "--duration",
    default=1,
    type=int,
    help="Duration in hours to run activities",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deployed without executing",
)
@click.pass_context
def deploy(
    ctx: click.Context,
    name: str,
    workers: int,
    department: str,
    tenant_domain: str,
    duration: int,
    dry_run: bool,
):
    """Deploy a knowledge worker simulation.

    Creates and starts a KW deployment with the specified configuration.
    Workers will simulate M365 activities for the specified duration.

    Examples:
        haymaker kw deploy --name test --workers 5
        haymaker kw deploy --workers 10 --department sales --duration 4
        haymaker kw deploy --dry-run
    """
    try:
        from azure_haymaker.knowledge_worker import (
            DeploymentConfig,
            KnowledgeWorkerOrchestrator,
        )

        console.print(f"[cyan]Preparing KW deployment...[/cyan]")
        console.print(f"  Name: {name}")
        console.print(f"  Workers: {workers}")
        console.print(f"  Department: {department}")
        console.print(f"  Tenant Domain: {tenant_domain}")
        console.print(f"  Duration: {duration}h")
        console.print()

        # Create deployment config
        config = DeploymentConfig(
            name=name,
            total_workers=workers,
            departments={
                department: {
                    "count": workers,
                    "endpoint_type": "cli_container",
                    "activity": {
                        "email_per_hour": 4,
                        "teams_messages_per_hour": 10,
                        "documents_per_day": 3,
                        "meetings_per_day": 4,
                    },
                }
            },
            duration_hours=duration,
            tenant_domain=tenant_domain,
        )

        if dry_run:
            console.print("[yellow]Dry run - deployment not started[/yellow]")
            console.print(f"\n[cyan]Would create:[/cyan]")
            console.print(f"  - {workers} {department} workers")
            console.print(f"  - Security groups for workers")
            console.print(f"  - Transport rules (external email blocking)")
            console.print(f"  - CLI containers for each worker")
            return

        # Create orchestrator and start deployment
        orchestrator = KnowledgeWorkerOrchestrator()
        run_id = orchestrator.create_deployment(config)

        console.print(f"[green]Deployment created: {run_id}[/green]")
        console.print(f"Starting deployment...")

        # Run deployment (sync wrapper around async)
        import asyncio
        asyncio.run(orchestrator.start_deployment(run_id))

        # Get final state
        state = orchestrator.get_deployment(run_id)
        if state:
            console.print(f"\n[green]Deployment started successfully![/green]")
            console.print(f"  Run ID: {state.run_id}")
            console.print(f"  Phase: {state.phase.value}")
            console.print(f"  Workers: {len(state.workers)}")
        else:
            console.print("[red]Deployment state not found[/red]")
            sys.exit(1)

    except ImportError as e:
        console.print(f"[red]KW framework not available:[/red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


__all__ = ["kw"]
