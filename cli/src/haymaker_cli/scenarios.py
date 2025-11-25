"""Scenarios command group for HayMaker CLI."""

import re
from pathlib import Path
from typing import NamedTuple

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

console = Console()


class ScenarioInfo(NamedTuple):
    """Scenario information extracted from markdown file."""

    name: str
    title: str
    category: str
    description: str
    file_path: Path


def get_scenarios_dir() -> Path:
    """Get path to scenarios documentation directory.

    Looks for docs/scenarios relative to the package location,
    falling back to common locations.

    Returns:
        Path to scenarios directory

    Raises:
        click.ClickException: If scenarios directory not found
    """
    # Try relative to this file (development setup)
    package_dir = Path(__file__).parent

    # Walk up to find project root (contains docs/scenarios)
    for parent in [package_dir] + list(package_dir.parents):
        scenarios_path = parent / "docs" / "scenarios"
        if scenarios_path.is_dir():
            return scenarios_path

    # Try current working directory
    cwd_scenarios = Path.cwd() / "docs" / "scenarios"
    if cwd_scenarios.is_dir():
        return cwd_scenarios

    raise click.ClickException(
        "Scenarios directory not found.\n"
        "Expected location: docs/scenarios/\n"
        "Ensure you are running from the project root or the package is properly installed."
    )


def parse_scenario_frontmatter(file_path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from scenario markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary of frontmatter key-value pairs
    """
    content = file_path.read_text()

    # Match YAML frontmatter between --- delimiters
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

    if not frontmatter_match:
        return {}

    frontmatter = {}
    for line in frontmatter_match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip().strip('"')

    return frontmatter


def list_scenarios() -> list[ScenarioInfo]:
    """List all available scenarios from documentation.

    Returns:
        List of ScenarioInfo objects
    """
    scenarios_dir = get_scenarios_dir()
    scenarios = []

    # Find all markdown files (excluding templates and special files)
    for md_file in sorted(scenarios_dir.glob("*.md")):
        # Skip template and special files
        if md_file.name.startswith(("SCENARIO_TEMPLATE", "SCALING_PLAN", "_")):
            continue

        frontmatter = parse_scenario_frontmatter(md_file)

        # Extract scenario name from filename (e.g., compute-01-linux-vm-web-server)
        name = md_file.stem

        # Parse category from parent or filename prefix
        category = frontmatter.get("parent", "")
        if not category:
            # Extract category from filename prefix (e.g., "compute" from "compute-01-...")
            category = name.split("-")[0].title() if "-" in name else "General"

        scenarios.append(
            ScenarioInfo(
                name=name,
                title=frontmatter.get("title", name),
                category=category,
                description=frontmatter.get("description", ""),
                file_path=md_file,
            )
        )

    return scenarios


def get_scenario_content(scenario_name: str) -> str:
    """Get full markdown content for a scenario.

    Args:
        scenario_name: Name of the scenario (without .md extension)

    Returns:
        Full markdown content

    Raises:
        click.ClickException: If scenario not found
    """
    scenarios_dir = get_scenarios_dir()

    # Try exact match first
    scenario_path = scenarios_dir / f"{scenario_name}.md"
    if scenario_path.is_file():
        return scenario_path.read_text()

    # Try partial match (e.g., "compute-01" matches "compute-01-linux-vm-web-server")
    matches = list(scenarios_dir.glob(f"{scenario_name}*.md"))
    if len(matches) == 1:
        return matches[0].read_text()
    elif len(matches) > 1:
        names = [m.stem for m in matches]
        raise click.ClickException(
            f"Ambiguous scenario name '{scenario_name}'. Multiple matches:\n"
            + "\n".join(f"  - {n}" for n in names)
        )

    raise click.ClickException(
        f"Scenario not found: {scenario_name}\n"
        "Use 'haymaker scenarios list' to see available scenarios."
    )


@click.group()
def scenarios():
    """Manage HayMaker scenarios.

    Scenarios define Azure resource deployments for testing and validation.
    Use these commands to discover available scenarios and view their details.

    Examples:
        haymaker scenarios list
        haymaker scenarios list --category compute
        haymaker scenarios describe compute-01-linux-vm-web-server
    """
    pass


@scenarios.command("list")
@click.option(
    "--category",
    help="Filter by category (e.g., compute, networking, security)",
)
@click.pass_context
def scenarios_list(ctx: click.Context, category: str | None):
    """List all available scenarios.

    Displays scenarios from the docs/scenarios directory with their
    titles, categories, and descriptions.

    Examples:
        haymaker scenarios list
        haymaker scenarios list --category compute
        haymaker scenarios list --format json
    """
    try:
        all_scenarios = list_scenarios()

        # Filter by category if specified
        if category:
            category_lower = category.lower()
            all_scenarios = [
                s for s in all_scenarios
                if s.category.lower() == category_lower
            ]

        if not all_scenarios:
            if category:
                console.print(f"[yellow]No scenarios found in category: {category}[/yellow]")
            else:
                console.print("[yellow]No scenarios found[/yellow]")
            return

        # Check output format from context
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        if output_format == "json":
            import json
            data = [
                {
                    "name": s.name,
                    "title": s.title,
                    "category": s.category,
                    "description": s.description,
                }
                for s in all_scenarios
            ]
            click.echo(json.dumps(data, indent=2))
        elif output_format == "yaml":
            import yaml
            data = [
                {
                    "name": s.name,
                    "title": s.title,
                    "category": s.category,
                    "description": s.description,
                }
                for s in all_scenarios
            ]
            click.echo(yaml.dump(data, default_flow_style=False))
        else:
            # Table format (default)
            table = Table(title=f"Available Scenarios ({len(all_scenarios)} total)")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Category", style="magenta")
            table.add_column("Title")
            table.add_column("Description", max_width=50)

            for scenario in all_scenarios:
                table.add_row(
                    scenario.name,
                    scenario.category,
                    scenario.title,
                    scenario.description[:47] + "..." if len(scenario.description) > 50 else scenario.description,
                )

            console.print(table)

            # Show available categories
            categories = sorted(set(s.category for s in all_scenarios))
            console.print(f"\n[dim]Categories: {', '.join(categories)}[/dim]")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to list scenarios: {e}") from e


@scenarios.command("describe")
@click.argument("scenario_name")
@click.option("--raw", is_flag=True, help="Output raw markdown without rendering")
@click.pass_context
def scenarios_describe(ctx: click.Context, scenario_name: str, raw: bool):
    """Show details for a specific scenario.

    Displays the full scenario documentation including deployment steps,
    prerequisites, and validation criteria.

    Arguments:
        SCENARIO_NAME: Name of the scenario (e.g., compute-01-linux-vm-web-server)
                       Partial names are supported (e.g., compute-01)

    Examples:
        haymaker scenarios describe compute-01-linux-vm-web-server
        haymaker scenarios describe compute-01
        haymaker scenarios describe networking-03 --raw
    """
    try:
        content = get_scenario_content(scenario_name)

        # Check output format from context
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        if raw or output_format in ("json", "yaml"):
            # Output raw markdown
            click.echo(content)
        else:
            # Render markdown with Rich
            console.print(Markdown(content))

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to describe scenario: {e}") from e


@scenarios.command("categories")
def scenarios_categories():
    """List all scenario categories.

    Shows available categories and the number of scenarios in each.

    Example:
        haymaker scenarios categories
    """
    try:
        all_scenarios = list_scenarios()

        # Count scenarios per category
        category_counts: dict[str, int] = {}
        for scenario in all_scenarios:
            category_counts[scenario.category] = category_counts.get(scenario.category, 0) + 1

        if not category_counts:
            console.print("[yellow]No scenarios found[/yellow]")
            return

        table = Table(title="Scenario Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Scenarios", justify="right")

        for category, count in sorted(category_counts.items()):
            table.add_row(category, str(count))

        console.print(table)

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to list categories: {e}") from e
