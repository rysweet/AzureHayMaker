"""Unit tests for interactive dashboard UI."""

import pytest
from unittest.mock import Mock, AsyncMock


class TestHayMakerDashboard:
    """Test HayMakerDashboard Textual app."""

    def test_dashboard_initialization(self, mock_telemetry_storage):
        """Test dashboard initializes correctly."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        assert dashboard.storage == mock_telemetry_storage
        assert dashboard.title == "HayMaker Dashboard"

    def test_dashboard_compose_method(self, mock_telemetry_storage):
        """Test dashboard compose method creates UI widgets."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Compose should return widgets
        widgets = list(dashboard.compose())

        assert len(widgets) > 0
        # Should include header, main content, footer

    def test_dashboard_load_data(self, mock_telemetry_storage):
        """Test dashboard loads telemetry data on startup."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.load_data()

        # Should load executions from storage
        mock_telemetry_storage.load_executions.assert_called()

    def test_dashboard_refresh_data(self, mock_telemetry_storage):
        """Test dashboard refresh functionality."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.refresh_data()

        # Should reload data from storage
        assert mock_telemetry_storage.load_executions.call_count > 0

    @pytest.mark.asyncio
    async def test_dashboard_auto_refresh(self, mock_telemetry_storage):
        """Test dashboard auto-refresh feature."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(
            storage=mock_telemetry_storage,
            auto_refresh_seconds=1
        )

        # Enable auto-refresh
        dashboard.start_auto_refresh()

        # Should have refresh timer active
        assert dashboard.auto_refresh_enabled is True

        dashboard.stop_auto_refresh()

    def test_dashboard_keyboard_shortcuts(self, mock_telemetry_storage):
        """Test dashboard keyboard shortcuts."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Test 'r' for refresh
        bindings = dashboard.BINDINGS
        assert any(b.key == "r" for b in bindings)

        # Test 'q' for quit
        assert any(b.key == "q" for b in bindings)

        # Test 'f' for filter
        assert any(b.key == "f" for b in bindings)

    def test_dashboard_handle_empty_data(self, mock_telemetry_storage_empty):
        """Test dashboard handles empty data gracefully."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage_empty)

        dashboard.load_data()

        # Should show empty state message
        assert dashboard.is_empty is True

    def test_dashboard_error_handling(self, mock_telemetry_storage):
        """Test dashboard error handling."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        # Mock storage that raises error
        mock_telemetry_storage.load_executions.side_effect = Exception("Storage error")

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Should handle error gracefully
        dashboard.load_data()

        assert dashboard.error_message is not None


class TestDashboardScreens:
    """Test dashboard screen navigation."""

    def test_summary_screen(self, mock_telemetry_storage):
        """Test summary screen displays KPIs."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard
        from haymaker_cli.ui.screens import SummaryScreen

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        screen = SummaryScreen()

        # Should display KPI widgets
        widgets = list(screen.compose())
        assert len(widgets) > 0

    def test_executions_screen(self, mock_telemetry_storage):
        """Test executions screen displays execution table."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard
        from haymaker_cli.ui.screens import ExecutionsScreen

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        screen = ExecutionsScreen()

        # Should display executions table
        widgets = list(screen.compose())
        assert len(widgets) > 0

    def test_agents_screen(self, mock_telemetry_storage):
        """Test agents screen displays agent table."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard
        from haymaker_cli.ui.screens import AgentsScreen

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        screen = AgentsScreen()

        # Should display agents table
        widgets = list(screen.compose())
        assert len(widgets) > 0

    def test_errors_screen(self, mock_telemetry_storage):
        """Test errors screen displays error analysis."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard
        from haymaker_cli.ui.screens import ErrorsScreen

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        screen = ErrorsScreen()

        # Should display error summary
        widgets = list(screen.compose())
        assert len(widgets) > 0

    def test_screen_navigation(self, mock_telemetry_storage):
        """Test navigating between screens."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Start on summary screen
        assert dashboard.current_screen == "summary"

        # Navigate to executions
        dashboard.switch_screen("executions")
        assert dashboard.current_screen == "executions"

        # Navigate to agents
        dashboard.switch_screen("agents")
        assert dashboard.current_screen == "agents"

    def test_screen_navigation_shortcuts(self, mock_telemetry_storage):
        """Test keyboard shortcuts for screen navigation."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Test number keys for navigation
        bindings = dashboard.BINDINGS
        assert any(b.key == "1" for b in bindings)  # Summary
        assert any(b.key == "2" for b in bindings)  # Executions
        assert any(b.key == "3" for b in bindings)  # Agents
        assert any(b.key == "4" for b in bindings)  # Errors


class TestDashboardFiltering:
    """Test dashboard filtering functionality."""

    def test_filter_by_status(self, mock_telemetry_storage):
        """Test filtering executions by status."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.apply_filter("status", "completed")

        # Should filter data
        assert dashboard.filters["status"] == "completed"

    def test_filter_by_scenario(self, mock_telemetry_storage):
        """Test filtering executions by scenario."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.apply_filter("scenario_id", "scenario-001")

        assert dashboard.filters["scenario_id"] == "scenario-001"

    def test_filter_by_date_range(self, mock_telemetry_storage):
        """Test filtering executions by date range."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard
        from datetime import datetime, timedelta

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        dashboard.apply_date_filter(start_date, end_date)

        assert dashboard.filters["start_date"] == start_date
        assert dashboard.filters["end_date"] == end_date

    def test_clear_filters(self, mock_telemetry_storage):
        """Test clearing all filters."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Apply some filters
        dashboard.apply_filter("status", "completed")
        dashboard.apply_filter("scenario_id", "scenario-001")

        # Clear filters
        dashboard.clear_filters()

        assert dashboard.filters == {}

    def test_filter_persistence(self, mock_telemetry_storage):
        """Test filters persist across screen navigation."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.apply_filter("status", "completed")

        # Navigate to different screen
        dashboard.switch_screen("agents")

        # Filter should still be applied
        assert dashboard.filters["status"] == "completed"


class TestDashboardExport:
    """Test dashboard export functionality."""

    def test_export_current_view(self, mock_telemetry_storage, tmp_path):
        """Test exporting current view to file."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        export_path = tmp_path / "export.csv"
        dashboard.export_current_view(export_path)

        assert export_path.exists()

    def test_export_html_report(self, mock_telemetry_storage, tmp_path):
        """Test exporting HTML report from dashboard."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        export_path = tmp_path / "report.html"
        dashboard.export_html_report(export_path)

        assert export_path.exists()

    def test_export_with_filters(self, mock_telemetry_storage, tmp_path):
        """Test export respects active filters."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.apply_filter("status", "completed")

        export_path = tmp_path / "filtered_export.csv"
        dashboard.export_current_view(export_path)

        assert export_path.exists()
        # Exported data should only include completed executions


class TestDashboardSorting:
    """Test dashboard table sorting."""

    def test_sort_by_date(self, mock_telemetry_storage):
        """Test sorting executions by date."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.sort_by("started_at", ascending=False)

        # Most recent should be first
        assert dashboard.sort_column == "started_at"
        assert dashboard.sort_ascending is False

    def test_sort_by_duration(self, mock_telemetry_storage):
        """Test sorting executions by duration."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.sort_by("duration_seconds", ascending=False)

        # Longest duration should be first
        assert dashboard.sort_column == "duration_seconds"

    def test_sort_by_status(self, mock_telemetry_storage):
        """Test sorting executions by status."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.sort_by("status", ascending=True)

        assert dashboard.sort_column == "status"

    def test_toggle_sort_direction(self, mock_telemetry_storage):
        """Test toggling sort direction."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # First sort ascending
        dashboard.sort_by("duration_seconds", ascending=True)
        assert dashboard.sort_ascending is True

        # Toggle to descending
        dashboard.sort_by("duration_seconds", ascending=False)
        assert dashboard.sort_ascending is False


class TestDashboardDetails:
    """Test dashboard detail views."""

    def test_view_execution_details(self, mock_telemetry_storage):
        """Test viewing detailed execution information."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        # Select an execution
        dashboard.show_execution_details("exec-001")

        assert dashboard.detail_view_visible is True
        assert dashboard.selected_execution_id == "exec-001"

    def test_close_detail_view(self, mock_telemetry_storage):
        """Test closing detail view."""
        from haymaker_cli.ui.dashboard import HayMakerDashboard

        dashboard = HayMakerDashboard(storage=mock_telemetry_storage)

        dashboard.show_execution_details("exec-001")
        dashboard.close_detail_view()

        assert dashboard.detail_view_visible is False
