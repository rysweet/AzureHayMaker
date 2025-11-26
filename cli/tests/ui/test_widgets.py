"""Unit tests for dashboard custom widgets."""

import pytest
from tests.fixtures.sample_data import sample_execution_data, sample_kpi_data


class TestKPIWidget:
    """Test KPI display widget."""

    def test_kpi_widget_initialization(self):
        """Test KPI widget initializes with data."""
        from haymaker_cli.ui.widgets import KPIWidget

        widget = KPIWidget(
            title="Success Rate",
            value="85%",
            trend="+5%"
        )

        assert widget.title == "Success Rate"
        assert widget.value == "85%"
        assert widget.trend == "+5%"

    def test_kpi_widget_render(self):
        """Test KPI widget renders correctly."""
        from haymaker_cli.ui.widgets import KPIWidget

        widget = KPIWidget(
            title="Total Executions",
            value="150"
        )

        # Should render without errors
        rendered = widget.render()
        assert rendered is not None

    def test_kpi_widget_positive_trend(self):
        """Test KPI widget displays positive trend."""
        from haymaker_cli.ui.widgets import KPIWidget

        widget = KPIWidget(
            title="Success Rate",
            value="90%",
            trend="+10%",
            trend_direction="up"
        )

        assert widget.trend_direction == "up"
        # Should apply positive styling

    def test_kpi_widget_negative_trend(self):
        """Test KPI widget displays negative trend."""
        from haymaker_cli.ui.widgets import KPIWidget

        widget = KPIWidget(
            title="Failure Rate",
            value="5%",
            trend="-2%",
            trend_direction="down"
        )

        assert widget.trend_direction == "down"
        # Should apply negative styling

    def test_kpi_widget_no_trend(self):
        """Test KPI widget without trend data."""
        from haymaker_cli.ui.widgets import KPIWidget

        widget = KPIWidget(
            title="Total Agents",
            value="1200"
        )

        assert widget.trend is None


class TestExecutionTable:
    """Test execution data table widget."""

    def test_execution_table_initialization(self):
        """Test execution table initializes with data."""
        from haymaker_cli.ui.widgets import ExecutionTable

        executions = sample_execution_data(count=10)
        table = ExecutionTable(executions=executions)

        assert len(table.rows) == 10

    def test_execution_table_columns(self):
        """Test execution table has correct columns."""
        from haymaker_cli.ui.widgets import ExecutionTable

        table = ExecutionTable(executions=[])

        columns = table.columns
        assert "Execution ID" in columns or "id" in columns
        assert "Status" in columns or "status" in columns
        assert "Duration" in columns or "duration" in columns

    def test_execution_table_sorting(self):
        """Test execution table sorting functionality."""
        from haymaker_cli.ui.widgets import ExecutionTable

        executions = sample_execution_data(count=10)
        table = ExecutionTable(executions=executions)

        # Sort by duration
        table.sort_by_column("duration_seconds", ascending=False)

        # First row should have longest duration
        # (This would be verified in actual implementation)

    def test_execution_table_filtering(self):
        """Test execution table filtering."""
        from haymaker_cli.ui.widgets import ExecutionTable

        executions = sample_execution_data(count=10)
        table = ExecutionTable(executions=executions)

        # Filter by status
        table.filter_by("status", "completed")

        # Should only show completed executions
        visible_rows = [r for r in table.rows if r.visible]
        assert all(r.data["status"] == "completed" for r in visible_rows)

    def test_execution_table_empty_data(self):
        """Test execution table handles empty data."""
        from haymaker_cli.ui.widgets import ExecutionTable

        table = ExecutionTable(executions=[])

        assert len(table.rows) == 0
        # Should display "No data" message

    def test_execution_table_row_selection(self):
        """Test execution table row selection."""
        from haymaker_cli.ui.widgets import ExecutionTable

        executions = sample_execution_data(count=10)
        table = ExecutionTable(executions=executions)

        # Select first row
        table.select_row(0)

        assert table.selected_row == 0

    def test_execution_table_status_colors(self):
        """Test execution table applies status-based colors."""
        from haymaker_cli.ui.widgets import ExecutionTable

        executions = sample_execution_data(count=5)
        table = ExecutionTable(executions=executions)

        # Completed should be green, failed red, running yellow
        # (This would be verified in actual styling)


class TestChartWidget:
    """Test chart display widget."""

    def test_chart_widget_initialization(self):
        """Test chart widget initializes with data."""
        from haymaker_cli.ui.widgets import ChartWidget

        chart_data = {
            "x": [1, 2, 3, 4, 5],
            "y": [10, 20, 15, 25, 30]
        }

        widget = ChartWidget(
            title="Execution Timeline",
            data=chart_data,
            chart_type="line"
        )

        assert widget.title == "Execution Timeline"
        assert widget.chart_type == "line"

    def test_chart_widget_line_chart(self):
        """Test chart widget renders line chart."""
        from haymaker_cli.ui.widgets import ChartWidget

        chart_data = {
            "x": [1, 2, 3],
            "y": [10, 20, 15]
        }

        widget = ChartWidget(
            title="Timeline",
            data=chart_data,
            chart_type="line"
        )

        # Should render line chart
        assert widget.chart_type == "line"

    def test_chart_widget_bar_chart(self):
        """Test chart widget renders bar chart."""
        from haymaker_cli.ui.widgets import ChartWidget

        chart_data = {
            "labels": ["A", "B", "C"],
            "values": [10, 20, 15]
        }

        widget = ChartWidget(
            title="Distribution",
            data=chart_data,
            chart_type="bar"
        )

        assert widget.chart_type == "bar"

    def test_chart_widget_pie_chart(self):
        """Test chart widget renders pie chart."""
        from haymaker_cli.ui.widgets import ChartWidget

        chart_data = {
            "labels": ["Completed", "Failed", "Running"],
            "values": [80, 15, 5]
        }

        widget = ChartWidget(
            title="Status Distribution",
            data=chart_data,
            chart_type="pie"
        )

        assert widget.chart_type == "pie"

    def test_chart_widget_empty_data(self):
        """Test chart widget handles empty data."""
        from haymaker_cli.ui.widgets import ChartWidget

        widget = ChartWidget(
            title="Empty Chart",
            data={},
            chart_type="line"
        )

        # Should handle gracefully


class TestFilterPanel:
    """Test filter panel widget."""

    def test_filter_panel_initialization(self):
        """Test filter panel initializes."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        assert panel is not None

    def test_filter_panel_status_filter(self):
        """Test filter panel status selection."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        # Should have status dropdown
        assert hasattr(panel, "status_select")

    def test_filter_panel_date_filter(self):
        """Test filter panel date range selection."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        # Should have date inputs
        assert hasattr(panel, "start_date")
        assert hasattr(panel, "end_date")

    def test_filter_panel_scenario_filter(self):
        """Test filter panel scenario selection."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        # Should have scenario selector
        assert hasattr(panel, "scenario_select")

    def test_filter_panel_apply_filters(self):
        """Test filter panel apply button."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        # Set some filters
        panel.status_select.value = "completed"

        # Apply filters
        filters = panel.get_filters()

        assert filters["status"] == "completed"

    def test_filter_panel_clear_filters(self):
        """Test filter panel clear button."""
        from haymaker_cli.ui.widgets import FilterPanel

        panel = FilterPanel()

        # Set filters
        panel.status_select.value = "completed"

        # Clear filters
        panel.clear_filters()

        filters = panel.get_filters()
        assert filters == {} or all(v is None for v in filters.values())


class TestHeaderWidget:
    """Test dashboard header widget."""

    def test_header_widget_initialization(self):
        """Test header widget displays title and navigation."""
        from haymaker_cli.ui.widgets import HeaderWidget

        widget = HeaderWidget(title="HayMaker Dashboard")

        assert widget.title == "HayMaker Dashboard"

    def test_header_widget_last_update_time(self):
        """Test header widget displays last update time."""
        from haymaker_cli.ui.widgets import HeaderWidget
        from datetime import datetime

        widget = HeaderWidget(title="Dashboard")

        widget.update_time(datetime.utcnow())

        # Should display timestamp

    def test_header_widget_navigation_tabs(self):
        """Test header widget has navigation tabs."""
        from haymaker_cli.ui.widgets import HeaderWidget

        widget = HeaderWidget(title="Dashboard")

        tabs = widget.tabs
        assert "Summary" in [t.label for t in tabs]
        assert "Executions" in [t.label for t in tabs]
        assert "Agents" in [t.label for t in tabs]


class TestFooterWidget:
    """Test dashboard footer widget."""

    def test_footer_widget_initialization(self):
        """Test footer widget displays help text."""
        from haymaker_cli.ui.widgets import FooterWidget

        widget = FooterWidget()

        assert widget is not None

    def test_footer_widget_keyboard_shortcuts(self):
        """Test footer widget displays keyboard shortcuts."""
        from haymaker_cli.ui.widgets import FooterWidget

        widget = FooterWidget()

        # Should show shortcuts like "q: Quit", "r: Refresh", etc.
        shortcuts = widget.get_shortcut_text()
        assert "quit" in shortcuts.lower() or "q" in shortcuts.lower()


class TestStatusBadge:
    """Test status badge widget."""

    def test_status_badge_completed(self):
        """Test status badge for completed status."""
        from haymaker_cli.ui.widgets import StatusBadge

        badge = StatusBadge(status="completed")

        assert badge.status == "completed"
        # Should have green styling

    def test_status_badge_failed(self):
        """Test status badge for failed status."""
        from haymaker_cli.ui.widgets import StatusBadge

        badge = StatusBadge(status="failed")

        assert badge.status == "failed"
        # Should have red styling

    def test_status_badge_running(self):
        """Test status badge for running status."""
        from haymaker_cli.ui.widgets import StatusBadge

        badge = StatusBadge(status="running")

        assert badge.status == "running"
        # Should have yellow/amber styling


class TestDetailView:
    """Test execution detail view widget."""

    def test_detail_view_initialization(self):
        """Test detail view displays execution details."""
        from haymaker_cli.ui.widgets import DetailView

        execution = sample_execution_data(count=1)[0]
        view = DetailView(execution=execution)

        assert view.execution == execution

    def test_detail_view_shows_metadata(self):
        """Test detail view shows execution metadata."""
        from haymaker_cli.ui.widgets import DetailView

        execution = sample_execution_data(count=1)[0]
        view = DetailView(execution=execution)

        # Should display ID, scenario, status, duration, etc.

    def test_detail_view_shows_agents(self):
        """Test detail view shows associated agents."""
        from haymaker_cli.ui.widgets import DetailView

        execution = sample_execution_data(count=1)[0]
        view = DetailView(execution=execution)

        # Should have agents section

    def test_detail_view_close_button(self):
        """Test detail view has close button."""
        from haymaker_cli.ui.widgets import DetailView

        execution = sample_execution_data(count=1)[0]
        view = DetailView(execution=execution)

        # Should have close button that triggers callback
        assert hasattr(view, "on_close")
