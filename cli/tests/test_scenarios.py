"""Tests for haymaker_cli.scenarios module."""

import json

import pytest
from click.testing import CliRunner

from haymaker_cli.scenarios import (
    ScenarioInfo,
    get_scenario_content,
    get_scenarios_dir,
    list_scenarios,
    parse_scenario_frontmatter,
    scenarios,
)


class TestParseFrontmatter:
    """Tests for parse_scenario_frontmatter function."""

    def test_valid_frontmatter(self, tmp_path):
        """Test parsing valid YAML frontmatter."""
        content = '''---
title: "Test Scenario"
category: "compute"
description: "A test scenario"
---

# Test Scenario

Content here.
'''
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = parse_scenario_frontmatter(test_file)

        assert result["title"] == "Test Scenario"
        assert result["category"] == "compute"
        assert result["description"] == "A test scenario"

    def test_frontmatter_without_quotes(self, tmp_path):
        """Test parsing frontmatter without quotes."""
        content = '''---
title: Test Scenario
parent: Compute
---

Content.
'''
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = parse_scenario_frontmatter(test_file)

        assert result["title"] == "Test Scenario"
        assert result["parent"] == "Compute"

    def test_no_frontmatter(self, tmp_path):
        """Test file without frontmatter returns empty dict."""
        content = "# Just a heading\n\nSome content."
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = parse_scenario_frontmatter(test_file)

        assert result == {}

    def test_empty_frontmatter(self, tmp_path):
        """Test empty frontmatter section."""
        content = '''---
---

Content.
'''
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = parse_scenario_frontmatter(test_file)

        assert result == {}

    def test_multiline_values_ignored(self, tmp_path):
        """Test that simple parsing handles multiline gracefully."""
        content = '''---
title: Test
description: First line only
  second line ignored
---

Content.
'''
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = parse_scenario_frontmatter(test_file)

        assert result["title"] == "Test"
        assert result["description"] == "First line only"


class TestScenarioInfo:
    """Tests for ScenarioInfo named tuple."""

    def test_create_scenario_info(self, tmp_path):
        """Test creating ScenarioInfo."""
        info = ScenarioInfo(
            name="compute-01-test",
            title="Test Compute",
            category="Compute",
            description="A test scenario",
            file_path=tmp_path / "test.md",
        )

        assert info.name == "compute-01-test"
        assert info.title == "Test Compute"
        assert info.category == "Compute"
        assert info.description == "A test scenario"


class TestGetScenariosDir:
    """Tests for get_scenarios_dir function."""

    def test_scenarios_dir_not_found(self, tmp_path, monkeypatch):
        """Test exception when scenarios directory not found."""
        # Change to a temp directory without scenarios
        monkeypatch.chdir(tmp_path)

        with pytest.raises(Exception) as exc_info:
            get_scenarios_dir()

        assert "not found" in str(exc_info.value).lower()

    def test_scenarios_dir_from_cwd(self, tmp_path, monkeypatch):
        """Test finding scenarios directory from current working directory."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        result = get_scenarios_dir()

        assert result == scenarios_dir


class TestListScenarios:
    """Tests for list_scenarios function."""

    def test_list_scenarios_empty(self, tmp_path, monkeypatch):
        """Test listing scenarios from empty directory."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        result = list_scenarios()

        assert result == []

    def test_list_scenarios_with_files(self, tmp_path, monkeypatch):
        """Test listing scenarios from directory with markdown files."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        # Create scenario files
        (scenarios_dir / "compute-01-linux-vm.md").write_text('''---
title: "Linux VM"
description: "Deploy Linux VM"
---

Content.
''')
        (scenarios_dir / "networking-01-vnet.md").write_text('''---
title: "Virtual Network"
description: "Create VNet"
---

Content.
''')

        monkeypatch.chdir(tmp_path)

        result = list_scenarios()

        assert len(result) == 2
        names = [s.name for s in result]
        assert "compute-01-linux-vm" in names
        assert "networking-01-vnet" in names

    def test_list_scenarios_excludes_templates(self, tmp_path, monkeypatch):
        """Test that template files are excluded."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        # Create scenario and template files
        (scenarios_dir / "compute-01-linux-vm.md").write_text('''---
title: "Linux VM"
---

Content.
''')
        (scenarios_dir / "SCENARIO_TEMPLATE.md").write_text("Template content")
        (scenarios_dir / "_draft.md").write_text("Draft content")
        (scenarios_dir / "SCALING_PLAN.md").write_text("Scaling plan")

        monkeypatch.chdir(tmp_path)

        result = list_scenarios()

        assert len(result) == 1
        assert result[0].name == "compute-01-linux-vm"

    def test_category_from_filename(self, tmp_path, monkeypatch):
        """Test category extraction from filename prefix."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        (scenarios_dir / "compute-01-test.md").write_text('''---
title: "Test"
---

Content.
''')

        monkeypatch.chdir(tmp_path)

        result = list_scenarios()

        assert len(result) == 1
        assert result[0].category == "Compute"


class TestGetScenarioContent:
    """Tests for get_scenario_content function."""

    def test_exact_match(self, tmp_path, monkeypatch):
        """Test getting content with exact scenario name."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        expected_content = "# Test Scenario\n\nContent here."
        (scenarios_dir / "compute-01-test.md").write_text(expected_content)

        monkeypatch.chdir(tmp_path)

        result = get_scenario_content("compute-01-test")

        assert result == expected_content

    def test_partial_match(self, tmp_path, monkeypatch):
        """Test getting content with partial scenario name."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        expected_content = "# Linux VM\n\nDeploy a Linux VM."
        (scenarios_dir / "compute-01-linux-vm-web-server.md").write_text(expected_content)

        monkeypatch.chdir(tmp_path)

        result = get_scenario_content("compute-01")

        assert result == expected_content

    def test_ambiguous_match(self, tmp_path, monkeypatch):
        """Test error on ambiguous partial match."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        (scenarios_dir / "compute-01-linux.md").write_text("Linux")
        (scenarios_dir / "compute-01-windows.md").write_text("Windows")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(Exception) as exc_info:
            get_scenario_content("compute-01")

        assert "ambiguous" in str(exc_info.value).lower()

    def test_not_found(self, tmp_path, monkeypatch):
        """Test error when scenario not found."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        with pytest.raises(Exception) as exc_info:
            get_scenario_content("nonexistent")

        assert "not found" in str(exc_info.value).lower()


class TestScenariosCLI:
    """Tests for scenarios CLI commands."""

    def test_list_command_json_output(self, tmp_path, monkeypatch):
        """Test scenarios list command with JSON output."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        (scenarios_dir / "compute-01-test.md").write_text('''---
title: "Test Scenario"
description: "A test"
---

Content.
''')

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            scenarios,
            ["list"],
            obj={"format": "json"},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "compute-01-test"
        assert data[0]["title"] == "Test Scenario"

    def test_list_command_with_category_filter(self, tmp_path, monkeypatch):
        """Test scenarios list command with category filter."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        (scenarios_dir / "compute-01-vm.md").write_text('''---
title: "VM"
---
''')
        (scenarios_dir / "networking-01-vnet.md").write_text('''---
title: "VNet"
---
''')

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            scenarios,
            ["list", "--category", "compute"],
            obj={"format": "json"},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "compute-01-vm"

    def test_describe_command(self, tmp_path, monkeypatch):
        """Test scenarios describe command."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        content = "# Test Scenario\n\nThis is the content."
        (scenarios_dir / "compute-01-test.md").write_text(content)

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            scenarios,
            ["describe", "compute-01-test", "--raw"],
        )

        assert result.exit_code == 0
        assert "Test Scenario" in result.output

    def test_categories_command(self, tmp_path, monkeypatch):
        """Test scenarios categories command."""
        scenarios_dir = tmp_path / "docs" / "scenarios"
        scenarios_dir.mkdir(parents=True)

        (scenarios_dir / "compute-01-vm.md").write_text("---\ntitle: VM\n---\n")
        (scenarios_dir / "compute-02-scale.md").write_text("---\ntitle: Scale\n---\n")
        (scenarios_dir / "networking-01-vnet.md").write_text("---\ntitle: VNet\n---\n")

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(scenarios, ["categories"])

        assert result.exit_code == 0
        assert "Compute" in result.output
        assert "Networking" in result.output
