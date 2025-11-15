"""Unit tests for scenario_selector module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from azure_haymaker.models import ScenarioMetadata, SimulationSize
from azure_haymaker.orchestrator.scenario_selector import (
    list_available_scenarios,
    parse_scenario_metadata,
    select_scenarios,
)


class TestListAvailableScenarios:
    """Tests for list_available_scenarios function."""

    def test_list_available_scenarios_returns_list(self) -> None:
        """Test that function returns a list of Path objects."""
        scenarios = list_available_scenarios()
        assert isinstance(scenarios, list)
        assert all(isinstance(s, Path) for s in scenarios)

    def test_list_available_scenarios_excludes_template(self) -> None:
        """Test that SCENARIO_TEMPLATE.md is excluded."""
        scenarios = list_available_scenarios()
        scenario_names = [s.name for s in scenarios]
        assert "SCENARIO_TEMPLATE.md" not in scenario_names

    def test_list_available_scenarios_excludes_scaling_plan(self) -> None:
        """Test that SCALING_PLAN.md is excluded."""
        scenarios = list_available_scenarios()
        scenario_names = [s.name for s in scenarios]
        assert "SCALING_PLAN.md" not in scenario_names

    def test_list_available_scenarios_includes_valid_scenarios(self) -> None:
        """Test that valid scenario files are included."""
        scenarios = list_available_scenarios()
        scenario_names = [s.name for s in scenarios]

        # Check for known scenarios
        assert "ai-ml-01-cognitive-services-vision.md" in scenario_names
        assert "compute-01-linux-vm-web-server.md" in scenario_names

    def test_list_available_scenarios_all_markdown_files(self) -> None:
        """Test that all returned files are markdown."""
        scenarios = list_available_scenarios()
        assert all(s.suffix == ".md" for s in scenarios)

    def test_list_available_scenarios_directory_exists(self) -> None:
        """Test that the scenarios directory exists."""
        scenarios = list_available_scenarios()
        # If we got here without exception, scenarios were found
        assert len(scenarios) > 0


class TestParseScenarioMetadata:
    """Tests for parse_scenario_metadata function."""

    def test_parse_scenario_metadata_from_real_file(self) -> None:
        """Test parsing metadata from a real scenario file."""
        # Use a known scenario file
        scenarios = list_available_scenarios()
        assert len(scenarios) > 0

        metadata = parse_scenario_metadata(scenarios[0])

        assert isinstance(metadata, ScenarioMetadata)
        assert metadata.scenario_name is not None
        assert metadata.scenario_doc_path is not None
        assert metadata.technology_area is not None

    def test_parse_scenario_metadata_required_fields(self) -> None:
        """Test that parsed metadata has all required fields."""
        scenarios = list_available_scenarios()

        for scenario_path in scenarios[:3]:  # Test first 3
            metadata = parse_scenario_metadata(scenario_path)

            # Required fields
            assert isinstance(metadata.scenario_name, str)
            assert len(metadata.scenario_name) > 0
            assert isinstance(metadata.scenario_doc_path, str)
            assert isinstance(metadata.technology_area, str)

    def test_parse_scenario_metadata_scenario_name_from_filename(self) -> None:
        """Test that scenario_name is derived from filename."""
        scenarios = list_available_scenarios()

        for scenario_path in scenarios[:3]:
            metadata = parse_scenario_metadata(scenario_path)

            # Scenario name should match the filename (without .md)
            expected_name = scenario_path.stem
            assert metadata.scenario_name == expected_name

    def test_parse_scenario_metadata_technology_area_extracted(self) -> None:
        """Test that technology area is extracted from markdown."""
        scenarios = list_available_scenarios()

        for scenario_path in scenarios[:3]:
            metadata = parse_scenario_metadata(scenario_path)

            # Technology area should be populated (extracted from markdown)
            assert metadata.technology_area is not None
            assert len(metadata.technology_area) > 0

    def test_parse_scenario_metadata_agent_path_set(self) -> None:
        """Test that agent_path is constructed."""
        scenarios = list_available_scenarios()

        for scenario_path in scenarios[:3]:
            metadata = parse_scenario_metadata(scenario_path)

            # Agent path should be set
            assert metadata.agent_path is not None
            assert len(metadata.agent_path) > 0

    def test_parse_scenario_metadata_consistent_extraction(self) -> None:
        """Test that parsing same file gives consistent results."""
        scenarios = list_available_scenarios()
        scenario_path = scenarios[0]

        metadata1 = parse_scenario_metadata(scenario_path)
        metadata2 = parse_scenario_metadata(scenario_path)

        assert metadata1.scenario_name == metadata2.scenario_name
        assert metadata1.technology_area == metadata2.technology_area
        assert metadata1.agent_path == metadata2.agent_path


class TestSelectScenarios:
    """Tests for select_scenarios function."""

    def test_select_scenarios_small_returns_five(self) -> None:
        """Test that SMALL size selects 5 scenarios."""
        scenarios = select_scenarios(SimulationSize.SMALL)
        assert len(scenarios) == 5

    def test_select_scenarios_medium_returns_fifteen(self) -> None:
        """Test that MEDIUM size selects 15 scenarios."""
        scenarios = select_scenarios(SimulationSize.MEDIUM)
        assert len(scenarios) == 15

    def test_select_scenarios_large_returns_thirty(self) -> None:
        """Test that LARGE size selects 30 scenarios."""
        scenarios = select_scenarios(SimulationSize.LARGE)
        assert len(scenarios) == 30

    def test_select_scenarios_returns_scenario_metadata(self) -> None:
        """Test that selected items are ScenarioMetadata objects."""
        scenarios = select_scenarios(SimulationSize.SMALL)
        assert all(isinstance(s, ScenarioMetadata) for s in scenarios)

    def test_select_scenarios_random_different_runs(self) -> None:
        """Test that selection is random across different runs."""
        scenarios1 = select_scenarios(SimulationSize.SMALL)
        scenarios2 = select_scenarios(SimulationSize.SMALL)

        # Convert to sets of scenario names for comparison
        names1 = {s.scenario_name for s in scenarios1}
        names2 = {s.scenario_name for s in scenarios2}

        # Selections should be different (with very high probability)
        # This test may occasionally fail, but probability is extremely low
        # We allow some leniency here
        assert names1 != names2 or len(scenarios1) == 1

    def test_select_scenarios_no_template_selected(self) -> None:
        """Test that TEMPLATE scenario is never selected."""
        # Run multiple times to be sure
        for _ in range(5):
            scenarios = select_scenarios(SimulationSize.LARGE)
            scenario_names = [s.scenario_name for s in scenarios]
            assert "SCENARIO_TEMPLATE" not in scenario_names

    def test_select_scenarios_no_scaling_plan_selected(self) -> None:
        """Test that SCALING_PLAN scenario is never selected."""
        # Run multiple times to be sure
        for _ in range(5):
            scenarios = select_scenarios(SimulationSize.LARGE)
            scenario_names = [s.scenario_name for s in scenarios]
            assert "SCALING_PLAN" not in scenario_names

    def test_select_scenarios_no_duplicates(self) -> None:
        """Test that no scenario is selected twice."""
        scenarios = select_scenarios(SimulationSize.LARGE)
        scenario_names = [s.scenario_name for s in scenarios]

        # All names should be unique
        assert len(scenario_names) == len(set(scenario_names))

    def test_select_scenarios_enough_available(self) -> None:
        """Test that enough scenarios are available for LARGE size."""
        scenarios = select_scenarios(SimulationSize.LARGE)
        assert len(scenarios) == 30

    def test_select_scenarios_valid_metadata(self) -> None:
        """Test that selected scenarios have valid metadata."""
        scenarios = select_scenarios(SimulationSize.SMALL)

        for scenario in scenarios:
            assert isinstance(scenario.scenario_name, str)
            assert len(scenario.scenario_name) > 0
            assert isinstance(scenario.technology_area, str)
            assert len(scenario.technology_area) > 0
            assert isinstance(scenario.agent_path, str)

    def test_select_scenarios_returns_list(self) -> None:
        """Test that return value is a list."""
        scenarios = select_scenarios(SimulationSize.SMALL)
        assert isinstance(scenarios, list)


class TestScenarioSelectorIntegration:
    """Integration tests for scenario_selector module."""

    def test_full_workflow_list_and_select(self) -> None:
        """Test complete workflow: list then select."""
        available = list_available_scenarios()
        assert len(available) > 0

        selected = select_scenarios(SimulationSize.SMALL)
        assert len(selected) == 5

        # All selected should have valid metadata
        for scenario in selected:
            assert isinstance(scenario, ScenarioMetadata)
            assert scenario.scenario_name is not None

    def test_full_workflow_parse_multiple(self) -> None:
        """Test parsing multiple scenario files."""
        available = list_available_scenarios()

        for scenario_path in available[:5]:
            metadata = parse_scenario_metadata(scenario_path)
            assert metadata is not None
            assert metadata.scenario_name == scenario_path.stem

    def test_scenario_count_consistency(self) -> None:
        """Test that SimulationSize.scenario_count() matches select_scenarios."""
        for size in [SimulationSize.SMALL, SimulationSize.MEDIUM, SimulationSize.LARGE]:
            expected_count = size.scenario_count()
            selected = select_scenarios(size)
            assert len(selected) == expected_count
