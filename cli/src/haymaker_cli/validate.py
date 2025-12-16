"""Validate command for HayMaker CLI."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.text import Text

from haymaker_cli.auth import AzureADAuthProvider, create_auth_provider
from haymaker_cli.config import load_cli_config

console = Console()


class CheckStatus(Enum):
    """Status of a validation check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    status: CheckStatus
    message: str
    details: str | None = None


def format_status(status: CheckStatus) -> Text:
    """Format check status with color.

    Args:
        status: Check status

    Returns:
        Rich Text with appropriate color and symbol
    """
    styles = {
        CheckStatus.PASS: ("green", "[OK]"),
        CheckStatus.FAIL: ("red", "[FAIL]"),
        CheckStatus.WARN: ("yellow", "[WARN]"),
        CheckStatus.SKIP: ("dim", "[SKIP]"),
    }
    color, symbol = styles[status]
    return Text(symbol, style=color)


def check_config() -> CheckResult:
    """Check CLI configuration.

    Returns:
        CheckResult with configuration status
    """
    try:
        config = load_cli_config()
        return CheckResult(
            name="CLI Configuration",
            status=CheckStatus.PASS,
            message="Configuration loaded successfully",
            details=f"Endpoint: {config.endpoint}",
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return CheckResult(
                name="CLI Configuration",
                status=CheckStatus.FAIL,
                message="Configuration file not found",
                details="Run 'haymaker config set endpoint <url>' to configure",
            )
        return CheckResult(
            name="CLI Configuration",
            status=CheckStatus.FAIL,
            message="Configuration error",
            details=error_msg,
        )
    except Exception as e:
        return CheckResult(
            name="CLI Configuration",
            status=CheckStatus.FAIL,
            message="Unexpected configuration error",
            details=str(e),
        )


def check_api_connectivity() -> CheckResult:
    """Check API connectivity.

    Makes a GET request to the API root endpoint to verify connectivity.

    Returns:
        CheckResult with API connectivity status
    """
    try:
        config = load_cli_config()
        auth = create_auth_provider(config.auth.model_dump())

        headers = {
            "User-Agent": "haymaker-cli/0.1.0",
            "Accept": "application/json",
        }
        headers.update(auth.get_auth_header())

        # Make request to API root or health endpoint
        with httpx.Client(timeout=10.0) as client:
            # Try health endpoint first, fall back to root
            response = None
            for endpoint in ["/api/health", "/api/status", "/"]:
                try:
                    response = client.get(
                        f"{config.endpoint}{endpoint}",
                        headers=headers,
                    )
                    if response.status_code < 500:
                        break
                except httpx.RequestError:
                    continue

            # Handle case where all endpoints failed
            if response is None:
                return CheckResult(
                    name="API Connectivity",
                    status=CheckStatus.FAIL,
                    message="All API endpoints unreachable",
                    details="Could not connect to any health endpoint",
                )

            if response.status_code == 200:
                return CheckResult(
                    name="API Connectivity",
                    status=CheckStatus.PASS,
                    message="API is reachable and responding",
                    details=f"Status: {response.status_code}",
                )
            elif response.status_code == 401:
                return CheckResult(
                    name="API Connectivity",
                    status=CheckStatus.FAIL,
                    message="Authentication failed",
                    details="Check your API key or Azure AD credentials",
                )
            elif response.status_code == 403:
                return CheckResult(
                    name="API Connectivity",
                    status=CheckStatus.WARN,
                    message="API reachable but access denied",
                    details="Check your permissions",
                )
            else:
                return CheckResult(
                    name="API Connectivity",
                    status=CheckStatus.WARN,
                    message=f"API responded with status {response.status_code}",
                    details=response.text[:100] if response.text else None,
                )

    except ValueError as e:
        # Config not available
        return CheckResult(
            name="API Connectivity",
            status=CheckStatus.SKIP,
            message="Skipped - configuration not available",
            details=str(e),
        )
    except httpx.TimeoutException:
        return CheckResult(
            name="API Connectivity",
            status=CheckStatus.FAIL,
            message="Connection timeout",
            details="The API did not respond within 10 seconds",
        )
    except httpx.NetworkError as e:
        return CheckResult(
            name="API Connectivity",
            status=CheckStatus.FAIL,
            message="Network error",
            details=str(e),
        )
    except Exception as e:
        return CheckResult(
            name="API Connectivity",
            status=CheckStatus.FAIL,
            message="Unexpected error",
            details=str(e),
        )


def check_azure_cli() -> CheckResult:
    """Check Azure CLI installation and login status.

    Returns:
        CheckResult with Azure CLI status
    """
    try:
        # Check if Azure CLI is installed
        result = subprocess.run(
            ["az", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return CheckResult(
                name="Azure CLI",
                status=CheckStatus.FAIL,
                message="Azure CLI not working properly",
                details=result.stderr[:200] if result.stderr else None,
            )

        # Extract version from output
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"

        # Check if logged in
        account_result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if account_result.returncode != 0:
            return CheckResult(
                name="Azure CLI",
                status=CheckStatus.WARN,
                message="Azure CLI installed but not logged in",
                details=f"{version_line}\nRun 'az login' to authenticate",
            )

        # Parse account info
        try:
            account = json.loads(account_result.stdout)
            subscription = account.get("name", "unknown")
            user = account.get("user", {}).get("name", "unknown")
        except json.JSONDecodeError:
            subscription = "unknown"
            user = "unknown"

        return CheckResult(
            name="Azure CLI",
            status=CheckStatus.PASS,
            message="Azure CLI installed and authenticated",
            details=f"{version_line}\nSubscription: {subscription}\nUser: {user}",
        )

    except FileNotFoundError:
        return CheckResult(
            name="Azure CLI",
            status=CheckStatus.FAIL,
            message="Azure CLI not installed",
            details="Install from https://docs.microsoft.com/cli/azure/install-azure-cli",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="Azure CLI",
            status=CheckStatus.FAIL,
            message="Azure CLI command timeout",
            details="The command did not complete within 10 seconds",
        )
    except Exception as e:
        return CheckResult(
            name="Azure CLI",
            status=CheckStatus.FAIL,
            message="Error checking Azure CLI",
            details=str(e),
        )


def check_azure_auth() -> CheckResult:
    """Check Azure authentication using Azure AD credentials.

    Returns:
        CheckResult with Azure authentication status
    """
    try:
        # Try to get a token using Azure AD auth provider
        auth_provider = AzureADAuthProvider()
        header = auth_provider.get_auth_header()

        if "Authorization" in header and header["Authorization"].startswith("Bearer "):
            return CheckResult(
                name="Azure Authentication",
                status=CheckStatus.PASS,
                message="Azure AD authentication successful",
                details="Token acquired successfully",
            )
        else:
            return CheckResult(
                name="Azure Authentication",
                status=CheckStatus.FAIL,
                message="Failed to acquire Azure AD token",
                details="Unexpected authentication header format",
            )

    except Exception as e:
        error_msg = str(e)
        if "az login" in error_msg.lower() or "credential" in error_msg.lower():
            return CheckResult(
                name="Azure Authentication",
                status=CheckStatus.WARN,
                message="Azure AD authentication not available",
                details="Run 'az login' to enable Azure AD authentication",
            )
        return CheckResult(
            name="Azure Authentication",
            status=CheckStatus.FAIL,
            message="Azure AD authentication failed",
            details=error_msg[:200],
        )


def check_environment_variables() -> CheckResult:
    """Check relevant environment variables.

    Returns:
        CheckResult with environment variable status
    """
    env_vars = {
        "HAYMAKER_ENDPOINT": os.getenv("HAYMAKER_ENDPOINT"),
        "HAYMAKER_API_KEY": "****" if os.getenv("HAYMAKER_API_KEY") else None,
        "HAYMAKER_TENANT_ID": os.getenv("HAYMAKER_TENANT_ID"),
        "HAYMAKER_PROFILE": os.getenv("HAYMAKER_PROFILE"),
    }

    set_vars = {k: v for k, v in env_vars.items() if v is not None}

    if not set_vars:
        return CheckResult(
            name="Environment Variables",
            status=CheckStatus.SKIP,
            message="No HayMaker environment variables set",
            details="Using configuration file instead",
        )

    details_lines = [f"{k}={v}" for k, v in set_vars.items()]
    return CheckResult(
        name="Environment Variables",
        status=CheckStatus.PASS,
        message=f"{len(set_vars)} environment variable(s) configured",
        details="\n".join(details_lines),
    )


def check_scenarios_directory() -> CheckResult:
    """Check scenarios documentation directory.

    Returns:
        CheckResult with scenarios directory status
    """
    from haymaker_cli.scenarios import get_scenarios_dir, list_scenarios

    try:
        scenarios_dir = get_scenarios_dir()
        scenarios = list_scenarios()

        if not scenarios:
            return CheckResult(
                name="Scenarios Directory",
                status=CheckStatus.WARN,
                message="Scenarios directory found but empty",
                details=str(scenarios_dir),
            )

        return CheckResult(
            name="Scenarios Directory",
            status=CheckStatus.PASS,
            message=f"Found {len(scenarios)} scenario(s)",
            details=str(scenarios_dir),
        )

    except click.ClickException as e:
        return CheckResult(
            name="Scenarios Directory",
            status=CheckStatus.WARN,
            message="Scenarios directory not found",
            details=str(e),
        )
    except Exception as e:
        return CheckResult(
            name="Scenarios Directory",
            status=CheckStatus.FAIL,
            message="Error checking scenarios directory",
            details=str(e),
        )


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output for each check")
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON")
@click.pass_context
def validate(ctx: click.Context, verbose: bool, output_json: bool):
    """Validate environment configuration and connectivity.

    Performs a series of checks to verify that the HayMaker CLI
    is properly configured and can connect to required services.

    Checks performed:
    - CLI configuration (config file or environment variables)
    - API connectivity (can reach the HayMaker API)
    - Azure CLI installation and login status
    - Azure AD authentication
    - Scenarios documentation directory

    Examples:
        haymaker validate
        haymaker validate --verbose
        haymaker validate --json
    """
    checks = [
        check_config,
        check_environment_variables,
        check_api_connectivity,
        check_azure_cli,
        check_azure_auth,
        check_scenarios_directory,
    ]

    results: list[CheckResult] = []

    if not output_json:
        console.print("[bold]Validating HayMaker CLI environment...[/bold]\n")

    for check_func in checks:
        if not output_json:
            doc = getattr(check_func, "__doc__", None)
            check_name = doc.split(".")[0].strip() if doc else "unknown"
            console.print(f"  Checking {check_name}...", end="")
        result = check_func()
        results.append(result)
        if not output_json:
            console.print(f" {format_status(result.status)}")

    if output_json:
        output = {
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == CheckStatus.PASS),
                "failed": sum(1 for r in results if r.status == CheckStatus.FAIL),
                "warnings": sum(1 for r in results if r.status == CheckStatus.WARN),
                "skipped": sum(1 for r in results if r.status == CheckStatus.SKIP),
            },
        }
        click.echo(json.dumps(output, indent=2))
        return

    # Display results table
    console.print()
    table = Table(title="Validation Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    if verbose:
        table.add_column("Details", max_width=50)

    for result in results:
        row = [result.name, format_status(result.status), result.message]
        if verbose:
            row.append(result.details or "")
        table.add_row(*row)

    console.print(table)

    # Summary
    passed = sum(1 for r in results if r.status == CheckStatus.PASS)
    failed = sum(1 for r in results if r.status == CheckStatus.FAIL)
    warnings = sum(1 for r in results if r.status == CheckStatus.WARN)

    console.print()
    if failed > 0:
        console.print(f"[red]Validation failed: {failed} check(s) failed[/red]")
        if not verbose:
            console.print("[dim]Run with --verbose for more details[/dim]")
        sys.exit(1)
    elif warnings > 0:
        console.print(f"[yellow]Validation passed with {warnings} warning(s)[/yellow]")
    else:
        console.print(f"[green]All {passed} check(s) passed[/green]")
