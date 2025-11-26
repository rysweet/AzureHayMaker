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
        haymaker kw init
        haymaker kw status
        haymaker kw test --persona engineering
        haymaker kw list-personas
    """


@kw.command()
@click.option(
    "--tenant-id",
    help="Azure tenant ID (auto-detected if not provided)",
)
@click.option(
    "--app-name",
    default="haymaker-knowledge-worker",
    help="Display name for the app registration",
)
@click.option(
    "--reuse-existing/--no-reuse-existing",
    default=True,
    help="Reuse existing app registration if found",
)
@click.option(
    "--save-config",
    type=click.Path(),
    help="Save configuration to file",
)
@click.pass_context
def init(
    ctx: click.Context,
    tenant_id: str | None,
    app_name: str,
    reuse_existing: bool,
    save_config: str | None,
):
    """Initialize Knowledge Worker infrastructure.

    Creates and configures the Azure Entra app registration required
    for Knowledge Worker operations (M365 email, Teams, documents, etc.).

    Requires Azure CLI to be logged in with appropriate permissions
    (Application Administrator or Global Administrator).

    After running this command, you must grant admin consent using the
    provided URL.

    Examples:
        haymaker kw init
        haymaker kw init --tenant-id abc123-...
        haymaker kw init --save-config kw_config.env
    """
    try:
        from azure_haymaker.knowledge_worker.infrastructure import setup_kw_app

        console.print("[cyan]Setting up Knowledge Worker infrastructure...[/cyan]")

        config = setup_kw_app(
            tenant_id=tenant_id,
            app_name=app_name,
            reuse_existing=reuse_existing,
        )

        console.print("\n[green]App registration created successfully![/green]")
        console.print(f"  App ID: {config.app_id}")
        console.print(f"  Tenant ID: {config.tenant_id}")
        console.print(f"  Service Principal: {config.sp_id}")

        console.print("\n[yellow]IMPORTANT: Admin consent required![/yellow]")
        console.print("Open this URL in a browser and sign in as tenant admin:")
        console.print(f"\n  {config.admin_consent_url}\n")

        # Security warning
        console.print("\n[yellow]⚠️  SECURITY WARNING:[/yellow]")
        console.print("[yellow]The client secret is sensitive. Store it securely:[/yellow]")
        console.print("[dim]  - Use Azure Key Vault in production[/dim]")
        console.print("[dim]  - Never commit secrets to source control[/dim]")
        console.print("[dim]  - Rotate secrets regularly[/dim]")

        if save_config:
            import os

            with open(save_config, "w") as f:
                f.write(config.to_env_string())
            # Set restrictive permissions on config file
            os.chmod(save_config, 0o600)
            console.print(f"\n[green]Configuration saved to: {save_config}[/green]")
            console.print("[dim]File permissions set to owner-only (600)[/dim]")
        else:
            console.print("\n[cyan]Configuration (add to .env file):[/cyan]")
            console.print(config.to_env_string())

    except ImportError as e:
        console.print(f"[red]KW infrastructure module not available:[/red] {e}")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]Setup failed:[/red] {e}")
        console.print("[dim]Make sure you're logged in to Azure CLI with 'az login'[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
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
            personas.append(
                {
                    "name": persona.value,
                    "display_name": persona.value.title(),
                    "email_per_hour": config.get("email_per_hour", 5),
                    "teams_per_hour": config.get("teams_per_hour", 5),
                    "meetings_per_day": config.get("meetings_per_day", 4),
                }
            )

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

        console.print("[cyan]Creating test KW agent...[/cyan]")
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

        console.print("[green]Config created successfully![/green]")
        console.print(f"  name: {config.name}")
        console.print(f"  goal: {config.goal}")

        if dry_run:
            console.print("\n[yellow]Dry run - not creating agent[/yellow]")
            return

        # Create agent
        agent = KnowledgeWorkerAgent(worker_config=config)

        console.print("\n[green]Agent created successfully![/green]")
        console.print(f"  Worker Identity: {agent.worker_identity.worker_id}")
        console.print(f"  Persona: {agent.worker_identity.persona.value}")
        console.print(f"  Endpoint Type: {agent.worker_identity.endpoint_type.value}")

        # Get stats (without starting - no M365 connection)
        stats = agent.get_worker_stats()
        console.print("\n[cyan]Agent Stats:[/cyan]")
        for key, value in stats.items():
            console.print(f"  {key}: {value}")

        console.print("\n[green]KW framework test passed![/green]")

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

        # Check core imports - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker import (  # noqa: F401
                KnowledgeWorkerAgent,
                KnowledgeWorkerConfig,
            )

            checks.append({"name": "KW Agent", "status": "OK", "details": "Import successful"})
        except ImportError as e:
            checks.append({"name": "KW Agent", "status": "FAIL", "details": str(e)})

        # Check models - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.models import (  # noqa: F401
                EndpointType,
                Team,
                TeamConfig,
                WorkerConfig,
                WorkerIdentity,
                WorkerPersona,
            )

            checks.append({"name": "KW Models", "status": "OK", "details": "All models available"})
        except ImportError as e:
            checks.append({"name": "KW Models", "status": "FAIL", "details": str(e)})

        # Check operations - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.operations import (  # noqa: F401
                CalendarOperations,
                DocumentOperations,
                EmailOperations,
                TeamsOperations,
            )

            checks.append(
                {"name": "KW Operations", "status": "OK", "details": "All operations available"}
            )
        except ImportError as e:
            checks.append({"name": "KW Operations", "status": "FAIL", "details": str(e)})

        # Check validators - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.operations.validators import (  # noqa: F401
                CommunicationValidator,
                ExternalRecipientError,
            )

            checks.append(
                {"name": "KW Validators", "status": "OK", "details": "Validators available"}
            )
        except ImportError as e:
            checks.append({"name": "KW Validators", "status": "FAIL", "details": str(e)})

        # Check identity modules - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.identity import (  # noqa: F401
                EntraGroupManager,
                EntraUserManager,
                TransportRuleManager,
            )

            checks.append(
                {"name": "KW Identity", "status": "OK", "details": "Identity modules available"}
            )
        except ImportError as e:
            checks.append({"name": "KW Identity", "status": "FAIL", "details": str(e)})

        # Check endpoints - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.endpoints import (  # noqa: F401
                EndpointManager,
                M365CLIContainerManager,
                Windows365CloudPCManager,
            )

            checks.append(
                {"name": "KW Endpoints", "status": "OK", "details": "Endpoint managers available"}
            )
        except ImportError as e:
            checks.append({"name": "KW Endpoints", "status": "FAIL", "details": str(e)})

        # Check cleanup - imports are the test, not the usage
        try:
            from azure_haymaker.knowledge_worker.cleanup import (  # noqa: F401
                KnowledgeWorkerCleanupManager,
                KnowledgeWorkerResourceInventory,
            )

            checks.append(
                {"name": "KW Cleanup", "status": "OK", "details": "Cleanup manager available"}
            )
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

    # Import checks - imports test availability, not usage
    try:
        from azure_haymaker.knowledge_worker import (  # noqa: F401
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
        from azure_haymaker.knowledge_worker.operations import EmailOperations  # noqa: F401

        status["modules"]["operations"] = True
    except ImportError:
        status["modules"]["operations"] = False

    try:
        from azure_haymaker.knowledge_worker.operations.validators import (
            CommunicationValidator,  # noqa: F401
        )

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

        console.print("[cyan]Preparing KW deployment...[/cyan]")
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
            console.print("\n[cyan]Would create:[/cyan]")
            console.print(f"  - {workers} {department} workers")
            console.print("  - Security groups for workers")
            console.print("  - Transport rules (external email blocking)")
            console.print("  - CLI containers for each worker")
            return

        # Get credentials from environment
        import os

        tenant_id = os.getenv("KW_TENANT_ID")
        app_id = os.getenv("KW_APP_ID")
        client_secret = os.getenv("KW_CLIENT_SECRET")

        if not all([tenant_id, app_id, client_secret]):
            console.print("[red]Error: Missing M365 credentials[/red]")
            console.print("Set KW_APP_ID, KW_CLIENT_SECRET, and KW_TENANT_ID environment variables")
            sys.exit(1)

        # Create Graph API client
        from azure.identity import ClientSecretCredential
        from msgraph.graph_service_client import GraphServiceClient

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=app_id,
            client_secret=client_secret,
        )
        graph_client = GraphServiceClient(credential)

        # Create orchestrator and start deployment
        orchestrator = KnowledgeWorkerOrchestrator(graph_client)
        run_id = orchestrator.create_deployment(config)

        console.print(f"[green]Deployment created: {run_id}[/green]")
        console.print("Starting deployment...")

        # Run deployment (sync wrapper around async)
        import asyncio

        asyncio.run(orchestrator.start_deployment(run_id))

        # Get final state
        state = orchestrator.get_deployment(run_id)
        if state:
            console.print("\n[green]Deployment started successfully![/green]")
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


@kw.command("e2e-test")
@click.option(
    "--app-id",
    envvar="KW_APP_ID",
    help="Azure app (client) ID (or KW_APP_ID env var)",
)
@click.option(
    "--client-secret",
    envvar="KW_CLIENT_SECRET",
    help="Client secret (or KW_CLIENT_SECRET env var)",
)
@click.option(
    "--tenant-id",
    envvar="KW_TENANT_ID",
    help="Azure tenant ID (or KW_TENANT_ID env var)",
)
@click.option(
    "--sender",
    help="Email sender (user with mailbox)",
)
@click.option(
    "--recipient",
    help="Email recipient (user with mailbox)",
)
@click.option(
    "--test-email/--no-test-email",
    default=True,
    help="Test email operations",
)
@click.option(
    "--test-calendar/--no-test-calendar",
    default=True,
    help="Test calendar operations",
)
@click.option(
    "--test-groups/--no-test-groups",
    default=True,
    help="Test groups operations",
)
@click.pass_context
def e2e_test(
    ctx: click.Context,
    app_id: str | None,
    client_secret: str | None,
    tenant_id: str | None,
    sender: str | None,
    recipient: str | None,
    test_email: bool,
    test_calendar: bool,
    test_groups: bool,
):
    """Run E2E tests against real Azure tenant.

    Validates actual Graph API operations using the configured
    KW app registration credentials.

    Requires KW_APP_ID, KW_CLIENT_SECRET, and KW_TENANT_ID
    environment variables or command-line options.

    Examples:
        haymaker kw e2e-test
        haymaker kw e2e-test --sender user1@tenant.com --recipient user2@tenant.com
        haymaker kw e2e-test --no-test-email  # Skip email test
    """
    import asyncio

    if not app_id or not client_secret or not tenant_id:
        console.print("[red]Error:[/red] Missing credentials")
        console.print("Set KW_APP_ID, KW_CLIENT_SECRET, and KW_TENANT_ID environment variables")
        console.print("Or provide --app-id, --client-secret, and --tenant-id options")
        sys.exit(1)

    async def run_tests():
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient

        results = []

        console.print("[cyan]Running E2E tests against Azure tenant...[/cyan]")
        console.print(f"  Tenant ID: {tenant_id}")
        console.print(f"  App ID: {app_id}")
        console.print()

        # Create credential and client
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=app_id,
            client_secret=client_secret,
        )
        client = GraphServiceClient(credential)

        # Test 1: List users
        console.print("[cyan]Test 1:[/cyan] List tenant users...")
        try:
            users = await client.users.get()
            user_count = len(users.value) if users and users.value else 0
            console.print(f"  [green]PASS[/green] - Found {user_count} users")
            results.append(
                {"test": "List Users", "status": "PASS", "details": f"{user_count} users"}
            )
        except Exception as e:
            console.print(f"  [red]FAIL[/red] - {e}")
            results.append({"test": "List Users", "status": "FAIL", "details": str(e)})

        # Test 2: Email operations
        if test_email:
            console.print("[cyan]Test 2:[/cyan] Email operations...")
            if sender and recipient:
                try:
                    from datetime import UTC, datetime

                    from msgraph.generated.models.body_type import BodyType
                    from msgraph.generated.models.email_address import EmailAddress
                    from msgraph.generated.models.item_body import ItemBody
                    from msgraph.generated.models.message import Message
                    from msgraph.generated.models.recipient import Recipient
                    from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
                        SendMailPostRequestBody,
                    )

                    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
                    message = Message(
                        subject=f"[HayMaker E2E Test] {timestamp}",
                        body=ItemBody(
                            content_type=BodyType.Text,
                            content=f"Automated E2E test email - {timestamp}",
                        ),
                        to_recipients=[Recipient(email_address=EmailAddress(address=recipient))],
                    )
                    request = SendMailPostRequestBody(message=message, save_to_sent_items=True)
                    await client.users.by_user_id(sender).send_mail.post(request)
                    console.print(
                        f"  [green]PASS[/green] - Email sent from {sender} to {recipient}"
                    )
                    results.append(
                        {
                            "test": "Send Email",
                            "status": "PASS",
                            "details": f"{sender} -> {recipient}",
                        }
                    )
                except Exception as e:
                    console.print(f"  [red]FAIL[/red] - {e}")
                    results.append({"test": "Send Email", "status": "FAIL", "details": str(e)})
            else:
                # Find users with mailboxes
                console.print("  Finding users with mailboxes...")
                mailbox_users = []
                if users and users.value:
                    for user in users.value[:10]:
                        try:
                            msgs = await client.users.by_user_id(
                                user.user_principal_name
                            ).messages.get()
                            if msgs is not None:
                                mailbox_users.append(user.user_principal_name)
                                if len(mailbox_users) >= 2:
                                    break
                        except Exception as e:
                            # Expected: MailboxNotEnabledForRESTAPI for users without Exchange license
                            # Skip users without mailboxes silently
                            if "MailboxNotEnabledForRESTAPI" not in str(e):
                                # Log unexpected errors for debugging
                                console.print(
                                    f"  [dim]Warning: {user.user_principal_name}: {str(e)[:50]}[/dim]"
                                )

                if len(mailbox_users) >= 2:
                    console.print(f"  [green]PASS[/green] - Found mailbox users: {mailbox_users}")
                    results.append(
                        {
                            "test": "Email Access",
                            "status": "PASS",
                            "details": f"Found {len(mailbox_users)} mailbox users",
                        }
                    )
                else:
                    console.print(
                        "  [yellow]SKIP[/yellow] - Insufficient mailbox users (need --sender and --recipient)"
                    )
                    results.append(
                        {
                            "test": "Email Access",
                            "status": "SKIP",
                            "details": "No mailbox users found",
                        }
                    )

        # Test 3: Calendar operations
        if test_calendar and sender:
            console.print("[cyan]Test 3:[/cyan] Calendar operations...")
            try:
                from datetime import UTC, datetime, timedelta

                from msgraph.generated.models.body_type import BodyType
                from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
                from msgraph.generated.models.event import Event
                from msgraph.generated.models.item_body import ItemBody

                now = datetime.now(UTC)
                start = now + timedelta(days=1)
                end = start + timedelta(hours=1)

                event = Event(
                    subject=f"[HayMaker E2E Test] {now.strftime('%H:%M')}",
                    body=ItemBody(content_type=BodyType.Text, content="E2E test event"),
                    start=DateTimeTimeZone(
                        date_time=start.strftime("%Y-%m-%dT%H:%M:%S"), time_zone="UTC"
                    ),
                    end=DateTimeTimeZone(
                        date_time=end.strftime("%Y-%m-%dT%H:%M:%S"), time_zone="UTC"
                    ),
                )
                result = await client.users.by_user_id(sender).calendar.events.post(event)
                console.print(f"  [green]PASS[/green] - Created calendar event: {result.subject}")
                results.append(
                    {"test": "Create Calendar Event", "status": "PASS", "details": result.id}
                )
            except Exception as e:
                console.print(f"  [red]FAIL[/red] - {e}")
                results.append(
                    {"test": "Create Calendar Event", "status": "FAIL", "details": str(e)}
                )
        elif test_calendar:
            console.print("[cyan]Test 3:[/cyan] Calendar operations...")
            console.print("  [yellow]SKIP[/yellow] - Need --sender to test calendar")
            results.append({"test": "Calendar", "status": "SKIP", "details": "No sender specified"})

        # Test 4: Groups operations
        if test_groups:
            console.print("[cyan]Test 4:[/cyan] Groups operations...")
            try:
                groups = await client.groups.get()
                group_count = len(groups.value) if groups and groups.value else 0
                console.print(f"  [green]PASS[/green] - Found {group_count} groups")
                results.append(
                    {"test": "List Groups", "status": "PASS", "details": f"{group_count} groups"}
                )
            except Exception as e:
                console.print(f"  [red]FAIL[/red] - {e}")
                results.append({"test": "List Groups", "status": "FAIL", "details": str(e)})

        # Summary
        console.print()
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = sum(1 for r in results if r["status"] == "FAIL")
        skip_count = sum(1 for r in results if r["status"] == "SKIP")

        table = Table(title="E2E Test Results")
        table.add_column("Test", style="cyan")
        table.add_column("Status")
        table.add_column("Details", max_width=50)

        for r in results:
            status_style = {"PASS": "green", "FAIL": "red", "SKIP": "yellow"}.get(
                r["status"], "white"
            )
            table.add_row(
                r["test"], f"[{status_style}]{r['status']}[/{status_style}]", r["details"][:50]
            )

        console.print(table)
        console.print(
            f"\n[cyan]Summary:[/cyan] {pass_count} PASS, {fail_count} FAIL, {skip_count} SKIP"
        )

        if fail_count > 0:
            sys.exit(1)

    try:
        asyncio.run(run_tests())
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@kw.command()
@click.option("--run-id", required=True, help="Deployment run ID")
@click.option("--format", type=click.Choice(["table", "json", "yaml"]), default="table", help="Output format")
@click.option("--output", type=click.Path(), help="Output file path")
def telemetry_report(run_id: str, format: str, output: str | None):
    """Generate telemetry report for a KW deployment.

    Collects M365 activity data (emails, calendar, Teams) and generates report.

    Examples:
        haymaker kw telemetry-report --run-id kw-abc12345
        haymaker kw telemetry-report --run-id kw-abc12345 --format json --output report.json
    """
    import os
    import asyncio
    from azure.identity import ClientSecretCredential
    from msgraph.graph_service_client import GraphServiceClient
    from azure_haymaker.knowledge_worker.telemetry.m365_telemetry import M365TelemetryCollector

    tenant_id = os.getenv("KW_TENANT_ID")
    app_id = os.getenv("KW_APP_ID")
    client_secret = os.getenv("KW_CLIENT_SECRET")

    if not all([tenant_id, app_id, client_secret]):
        console.print("[red]Error: Missing M365 credentials[/red]")
        return

    async def collect():
        cred = ClientSecretCredential(tenant_id, app_id, client_secret)
        graph_client = GraphServiceClient(cred)
        collector = M365TelemetryCollector(graph_client, run_id)

        console.print(f"\n[cyan]Collecting telemetry for: {run_id}[/cyan]\n")
        summary = await collector.get_run_summary(hours_back=48)

        if format == "table":
            console.print("[bold]Activity Summary[/bold]\n")
            console.print(f"Workers: {summary.get('worker_count', 0)}")
            console.print(f"Emails: {summary.get('total_emails', 0)}")
            console.print(f"Calendar Events: {summary.get('total_calendar_events', 0)}")
            console.print(f"Teams Messages: {summary.get('total_teams_messages', 0)}")
        elif format == "json":
            import json
            output_str = json.dumps(summary, indent=2, default=str)
            if output:
                with open(output, "w") as f:
                    f.write(output_str)
                console.print(f"✓ Saved to {output}")
            else:
                console.print(output_str)

    asyncio.run(collect())


__all__ = ["kw"]
