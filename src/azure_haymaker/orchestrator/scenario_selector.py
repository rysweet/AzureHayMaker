"""Scenario selector for orchestration - lists, parses, and selects scenarios for execution."""

import random
import re
from pathlib import Path
from typing import List

from azure_haymaker.models import ScenarioMetadata, SimulationSize


def list_available_scenarios() -> List[Path]:
    """List all available scenario files from docs/scenarios directory.

    Excludes SCENARIO_TEMPLATE.md and SCALING_PLAN.md files.

    Returns:
        List of Path objects pointing to scenario markdown files.

    Raises:
        FileNotFoundError: If scenarios directory doesn't exist.

    Example:
        >>> scenarios = list_available_scenarios()
        >>> print(f"Found {len(scenarios)} scenarios")
        >>> for scenario in scenarios[:3]:
        ...     print(scenario.name)
    """
    scenarios_dir = Path(__file__).parent.parent.parent.parent / "docs" / "scenarios"

    if not scenarios_dir.exists():
        raise FileNotFoundError(f"Scenarios directory not found: {scenarios_dir}")

    # Get all markdown files
    all_md_files = sorted(scenarios_dir.glob("*.md"))

    # Filter out excluded files
    excluded = {"SCENARIO_TEMPLATE.md", "SCALING_PLAN.md"}
    available = [f for f in all_md_files if f.name not in excluded]

    return available


def parse_scenario_metadata(file_path: Path) -> ScenarioMetadata:
    """Parse scenario metadata from a markdown file.

    Extracts scenario name from filename, technology area from markdown content,
    and constructs appropriate agent path.

    Args:
        file_path: Path to scenario markdown file.

    Returns:
        ScenarioMetadata object with extracted information.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If required metadata cannot be extracted.

    Example:
        >>> from pathlib import Path
        >>> path = Path("docs/scenarios/ai-ml-01-cognitive-services-vision.md")
        >>> metadata = parse_scenario_metadata(path)
        >>> print(metadata.scenario_name)
        ai-ml-01-cognitive-services-vision
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {file_path}")

    # Extract scenario name from filename
    scenario_name = file_path.stem

    # Read file content
    content = file_path.read_text(encoding="utf-8")

    # Extract technology area from markdown
    # Look for "## Technology Area" section
    tech_area_match = re.search(r"##\s+Technology Area\s*\n\s*(.+?)(?:\n|$)", content)
    if tech_area_match:
        technology_area = tech_area_match.group(1).strip()
    else:
        # Fallback: try to extract from first heading or use default
        technology_area = "General"

    # Construct agent path based on scenario name
    # Convert scenario name to module path format
    # e.g., "ai-ml-01-cognitive-services-vision" -> "agents/ai_ml_cognitive_services_vision.py"
    agent_module_name = scenario_name.replace("-", "_")
    agent_path = f"agents/{agent_module_name}.py"

    # Create metadata object
    metadata = ScenarioMetadata(
        scenario_name=scenario_name,
        scenario_doc_path=str(file_path),
        agent_path=agent_path,
        technology_area=technology_area,
    )

    return metadata


def select_scenarios(size: SimulationSize) -> List[ScenarioMetadata]:
    """Select random scenarios based on simulation size.

    Selection is random and ensures no duplicates.

    Args:
        size: SimulationSize enum value (SMALL=5, MEDIUM=15, LARGE=30)

    Returns:
        List of randomly selected ScenarioMetadata objects.

    Raises:
        ValueError: If not enough scenarios available for requested size.

    Example:
        >>> from azure_haymaker.models import SimulationSize
        >>> scenarios = select_scenarios(SimulationSize.SMALL)
        >>> print(len(scenarios))
        5
    """
    # Get number of scenarios to select
    scenario_count = size.scenario_count()

    # Get all available scenarios
    available = list_available_scenarios()

    if len(available) < scenario_count:
        raise ValueError(
            f"Not enough scenarios available. "
            f"Requested: {scenario_count}, Available: {len(available)}"
        )

    # Randomly select without replacement
    selected_paths = random.sample(available, scenario_count)

    # Parse metadata for selected scenarios
    selected_metadata = [parse_scenario_metadata(path) for path in selected_paths]

    return selected_metadata


__all__ = ["list_available_scenarios", "parse_scenario_metadata", "select_scenarios"]
