"""End-to-end integration test for Azure HayMaker components."""

from pathlib import Path

from azure_haymaker.models import SimulationSize
from azure_haymaker.orchestrator.scenario_selector import (
    list_available_scenarios,
    parse_scenario_metadata,
    select_scenarios,
)


class TestEndToEndIntegration:
    """Integration tests validating complete workflow."""

    def test_scenario_discovery_and_selection(self) -> None:
        """Test complete scenario discovery and selection workflow."""
        # Step 1: List available scenarios
        scenarios = list_available_scenarios()
        assert len(scenarios) >= 49, f"Expected 49+ scenarios, found {len(scenarios)}"
        assert all(s.suffix == ".md" for s in scenarios), "All scenarios should be markdown"

        # Step 2: Parse a scenario
        first_scenario = scenarios[0]
        metadata = parse_scenario_metadata(first_scenario)
        assert metadata.scenario_name
        assert metadata.technology_area
        assert metadata.agent_path.startswith("src/agents/")
        assert metadata.scenario_doc_path

        # Step 3: Select scenarios for small simulation
        selected = select_scenarios(SimulationSize.SMALL)
        assert len(selected) == 5, f"Small simulation should select 5, got {len(selected)}"
        assert all(isinstance(s.scenario_name, str) for s in selected)

        # Step 4: Verify no duplicates
        names = [s.scenario_name for s in selected]
        assert len(names) == len(set(names)), "Should have no duplicate scenarios"

        print("✅ End-to-end scenario workflow validated")

    def test_agent_directory_structure(self) -> None:
        """Verify agent directories match expected structure."""
        agents_dir = Path("src/agents")
        assert agents_dir.exists(), "src/agents directory should exist"

        agent_dirs = list(agents_dir.glob("*-agent"))
        assert len(agent_dirs) >= 45, f"Expected 45+ agent dirs, found {len(agent_dirs)}"

        # Check first agent has proper structure
        first_agent = agent_dirs[0]
        assert first_agent.is_dir()

        # Find the bundle directory within
        bundle_dirs = list(first_agent.glob("*-agent"))
        assert len(bundle_dirs) >= 1, f"Agent {first_agent} should have a bundle directory"

        bundle_dir = bundle_dirs[0]
        main_py = bundle_dir / "main.py"
        assert main_py.exists(), f"Agent bundle should have main.py: {bundle_dir}"

        print(f"✅ Agent structure validated: {len(agent_dirs)} agents with proper structure")

    def test_documentation_completeness(self) -> None:
        """Verify all required documentation exists."""
        required_docs = [
            "specs/requirements.md",
            "specs/initial-prompt.md",
            "specs/architecture.md",
            "specs/api-design.md",
            "docs/architecture/orchestrator.md",
            "docs/scenarios/SCENARIO_TEMPLATE.md",
            "README.md",
        ]

        for doc in required_docs:
            path = Path(doc)
            assert path.exists(), f"Required documentation missing: {doc}"

        print(f"✅ All {len(required_docs)} required docs present")

    def test_package_structure(self) -> None:
        """Verify package structure is correct."""
        required_modules = [
            "src/azure_haymaker/__init__.py",
            "src/azure_haymaker/models/__init__.py",
            "src/azure_haymaker/models/config.py",
            "src/azure_haymaker/models/scenario.py",
            "src/azure_haymaker/models/service_principal.py",
            "src/azure_haymaker/models/resource.py",
            "src/azure_haymaker/models/execution.py",
            "src/azure_haymaker/orchestrator/__init__.py",
            "src/azure_haymaker/orchestrator/config.py",
            "src/azure_haymaker/orchestrator/validation.py",
            "src/azure_haymaker/orchestrator/sp_manager.py",
            "src/azure_haymaker/orchestrator/scenario_selector.py",
            "src/azure_haymaker/orchestrator/container_manager.py",
            "src/azure_haymaker/orchestrator/event_bus.py",
            "src/azure_haymaker/orchestrator/cleanup.py",
            "src/azure_haymaker/orchestrator/monitoring_api.py",
            "src/azure_haymaker/orchestrator/orchestrator.py",
        ]

        for module in required_modules:
            path = Path(module)
            assert path.exists(), f"Required module missing: {module}"

        print(f"✅ All {len(required_modules)} required modules present")
