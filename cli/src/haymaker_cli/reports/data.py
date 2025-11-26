"""Report data processing and KPI calculation for Azure HayMaker CLI."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..telemetry.storage import TelemetryStorage
from .models import ReportFilters


class ReportDataProcessor:
    """Report data processor.

    Calculates KPIs and aggregates data for report generation.
    """

    def __init__(self, storage: TelemetryStorage):
        """Initialize report data processor.

        Args:
            storage: TelemetryStorage instance
        """
        self.storage = storage

    def calculate_kpis(
        self, filters: Optional[ReportFilters] = None
    ) -> Dict[str, Any]:
        """Calculate KPI metrics from telemetry data.

        Args:
            filters: Optional filters to apply

        Returns:
            Dictionary of KPI metrics
        """
        # Convert filters to storage format
        filter_dict = self._convert_filters(filters) if filters else None

        # Load data
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Calculate execution metrics
        total_executions = len(executions)
        successful_executions = sum(1 for e in executions if e.get("status") == "completed")
        failed_executions = sum(1 for e in executions if e.get("status") == "failed")
        running_executions = sum(1 for e in executions if e.get("status") == "running")
        cancelled_executions = sum(1 for e in executions if e.get("status") == "cancelled")

        success_rate = (
            (successful_executions / total_executions * 100.0) if total_executions > 0 else 0.0
        )

        # Calculate duration metrics
        durations = [
            e["duration_seconds"]
            for e in executions
            if e.get("duration_seconds") is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0
        median_duration = (
            sorted(durations)[len(durations) // 2] if durations else 0.0
        )

        # Calculate agent metrics
        total_agents = len(agents)
        successful_agents = sum(1 for a in agents if a.get("status") == "completed")
        failed_agents = sum(1 for a in agents if a.get("status") == "failed")
        agent_success_rate = (
            (successful_agents / total_agents * 100.0) if total_agents > 0 else 0.0
        )
        avg_agents_per_execution = (
            total_agents / total_executions if total_executions > 0 else 0.0
        )

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "running_executions": running_executions,
            "cancelled_executions": cancelled_executions,
            "success_rate": round(success_rate, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "min_duration_seconds": round(min_duration, 2),
            "max_duration_seconds": round(max_duration, 2),
            "median_duration_seconds": round(median_duration, 2),
            "total_agents": total_agents,
            "successful_agents": successful_agents,
            "failed_agents": failed_agents,
            "agent_success_rate": round(agent_success_rate, 2),
            "avg_agents_per_execution": round(avg_agents_per_execution, 2),
        }

    def get_top_regions(
        self, filters: Optional[ReportFilters] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top regions by agent count.

        Args:
            filters: Optional filters to apply
            limit: Maximum number of regions to return

        Returns:
            List of region dictionaries with counts
        """
        filter_dict = self._convert_filters(filters) if filters else None
        agents = self.storage.load_agents(filters=filter_dict)

        # Count by region
        region_counter = Counter(a["region"] for a in agents if "region" in a)

        # Return top N
        return [
            {"region": region, "count": count}
            for region, count in region_counter.most_common(limit)
        ]

    def get_top_scenarios(
        self, filters: Optional[ReportFilters] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top scenarios by execution count.

        Args:
            filters: Optional filters to apply
            limit: Maximum number of scenarios to return

        Returns:
            List of scenario dictionaries with counts and success rates
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Group by scenario
        scenario_data: Dict[str, Dict[str, int]] = {}
        for exec_data in executions:
            scenario_name = exec_data.get("scenario_name", "Unknown")
            if scenario_name not in scenario_data:
                scenario_data[scenario_name] = {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                }

            scenario_data[scenario_name]["count"] += 1
            if exec_data.get("status") == "completed":
                scenario_data[scenario_name]["successful"] += 1
            elif exec_data.get("status") == "failed":
                scenario_data[scenario_name]["failed"] += 1

        # Calculate success rates and sort by count
        scenarios = []
        for scenario_name, data in scenario_data.items():
            success_rate = (
                (data["successful"] / data["count"] * 100.0) if data["count"] > 0 else 0.0
            )
            scenarios.append({
                "scenario": scenario_name,
                "count": data["count"],
                "success_rate": round(success_rate, 2),
            })

        scenarios.sort(key=lambda x: x["count"], reverse=True)
        return scenarios[:limit]

    def get_error_distribution(
        self, filters: Optional[ReportFilters] = None
    ) -> List[Dict[str, Any]]:
        """Get distribution of error messages.

        Args:
            filters: Optional filters to apply

        Returns:
            List of error dictionaries with counts
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Collect all error messages
        error_messages = []
        for exec_data in executions:
            if exec_data.get("error_message"):
                error_messages.append(exec_data["error_message"])

        for agent_data in agents:
            if agent_data.get("error_message"):
                error_messages.append(agent_data["error_message"])

        # Count errors
        error_counter = Counter(error_messages)

        # Return sorted by count
        return [
            {"error": error, "count": count}
            for error, count in error_counter.most_common()
        ]

    def get_timeline_data(
        self, filters: Optional[ReportFilters] = None, granularity: str = "day"
    ) -> Dict[str, List[Any]]:
        """Get timeline data for charts.

        Args:
            filters: Optional filters to apply
            granularity: Time granularity: hour, day, week

        Returns:
            Dictionary with x (timestamps) and y (counts) lists
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Group by time period
        timeline: Dict[str, int] = {}
        for exec_data in executions:
            started_at = exec_data.get("started_at")
            if not started_at:
                continue

            # Parse timestamp
            if isinstance(started_at, str):
                try:
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                except Exception:
                    continue
            else:
                dt = started_at

            # Round to granularity
            if granularity == "hour":
                key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
            elif granularity == "day":
                key = dt.date().isoformat()
            elif granularity == "week":
                # Get start of week
                start_of_week = dt - timedelta(days=dt.weekday())
                key = start_of_week.date().isoformat()
            else:
                key = dt.date().isoformat()

            timeline[key] = timeline.get(key, 0) + 1

        # Sort by timestamp
        sorted_timeline = sorted(timeline.items())

        return {
            "x": [item[0] for item in sorted_timeline],
            "y": [item[1] for item in sorted_timeline],
        }

    def get_duration_distribution(
        self, filters: Optional[ReportFilters] = None, bins: int = 10
    ) -> Dict[str, List[Any]]:
        """Get duration distribution for histograms.

        Args:
            filters: Optional filters to apply
            bins: Number of bins for histogram

        Returns:
            Dictionary with bins and counts
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Collect durations
        durations = [
            e["duration_seconds"]
            for e in executions
            if e.get("duration_seconds") is not None
        ]

        if not durations:
            return {"bins": [], "counts": []}

        # Create bins
        min_duration = min(durations)
        max_duration = max(durations)
        bin_size = (max_duration - min_duration) / bins if bins > 0 else 1

        # Initialize bins
        bin_edges = [min_duration + i * bin_size for i in range(bins + 1)]
        bin_counts = [0] * bins

        # Count durations in each bin
        for duration in durations:
            for i in range(bins):
                if i == bins - 1:  # Last bin includes max
                    if bin_edges[i] <= duration <= bin_edges[i + 1]:
                        bin_counts[i] += 1
                        break
                else:
                    if bin_edges[i] <= duration < bin_edges[i + 1]:
                        bin_counts[i] += 1
                        break

        return {
            "bins": [round(edge, 2) for edge in bin_edges[:-1]],
            "counts": bin_counts,
        }

    def get_status_distribution(
        self, filters: Optional[ReportFilters] = None
    ) -> Dict[str, Any]:
        """Get execution status distribution.

        Args:
            filters: Optional filters to apply

        Returns:
            Dictionary with labels and values
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Count by status
        status_counter = Counter(e.get("status", "unknown") for e in executions)

        return {
            "labels": list(status_counter.keys()),
            "values": list(status_counter.values()),
        }


    def get_region_distribution(
        self, filters: Optional[ReportFilters] = None
    ) -> Dict[str, Any]:
        """Get agent distribution by region.

        Args:
            filters: Optional filters to apply

        Returns:
            Dictionary with labels and values
        """
        filter_dict = self._convert_filters(filters) if filters else None
        agents = self.storage.load_agents(filters=filter_dict)

        # Count by region
        region_counter = Counter(a.get("region", "unknown") for a in agents)

        return {
            "labels": list(region_counter.keys()),
            "values": list(region_counter.values()),
        }

    def calculate_percentiles(
        self, percentiles: List[int], filters: Optional[ReportFilters] = None
    ) -> Dict[str, float]:
        """Calculate duration percentiles.

        Args:
            percentiles: List of percentile values to calculate (e.g., [50, 90, 95, 99])
            filters: Optional filters to apply

        Returns:
            Dictionary mapping percentile names to values
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Collect durations
        durations = sorted([
            e["duration_seconds"]
            for e in executions
            if e.get("duration_seconds") is not None
        ])

        if not durations:
            return {f"p{p}": 0.0 for p in percentiles}

        # Calculate percentiles
        result = {}
        for p in percentiles:
            # Calculate index
            index = int(len(durations) * p / 100.0)
            if index >= len(durations):
                index = len(durations) - 1
            result[f"p{p}"] = round(durations[index], 2)

        return result

    def get_scenario_comparison(
        self, filters: Optional[ReportFilters] = None
    ) -> List[Dict[str, Any]]:
        """Get scenario comparison data.

        Args:
            filters: Optional filters to apply

        Returns:
            List of scenario dictionaries with detailed metrics
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Group by scenario
        scenario_data: Dict[str, Dict[str, Any]] = {}
        for exec_data in executions:
            scenario_id = exec_data.get("scenario_id", "unknown")
            scenario_name = exec_data.get("scenario_name", "Unknown")

            if scenario_id not in scenario_data:
                scenario_data[scenario_id] = {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "total_executions": 0,
                    "successful": 0,
                    "failed": 0,
                    "running": 0,
                    "durations": [],
                }

            data = scenario_data[scenario_id]
            data["total_executions"] += 1

            status = exec_data.get("status", "")
            if status == "completed":
                data["successful"] += 1
            elif status == "failed":
                data["failed"] += 1
            elif status == "running":
                data["running"] += 1

            if exec_data.get("duration_seconds") is not None:
                data["durations"].append(exec_data["duration_seconds"])

        # Calculate metrics for each scenario
        result = []
        for scenario_id, data in scenario_data.items():
            durations = data["durations"]
            success_rate = (
                (data["successful"] / data["total_executions"] * 100.0)
                if data["total_executions"] > 0
                else 0.0
            )

            result.append({
                "scenario_id": scenario_id,
                "scenario_name": data["scenario_name"],
                "total_executions": data["total_executions"],
                "successful_executions": data["successful"],
                "failed_executions": data["failed"],
                "running_executions": data["running"],
                "success_rate": round(success_rate, 2),
                "avg_duration_seconds": (
                    round(sum(durations) / len(durations), 2) if durations else 0.0
                ),
                "min_duration_seconds": round(min(durations), 2) if durations else 0.0,
                "max_duration_seconds": round(max(durations), 2) if durations else 0.0,
            })

        # Sort by total executions descending
        result.sort(key=lambda x: x["total_executions"], reverse=True)
        return result

    def get_failure_analysis(
        self, filters: Optional[ReportFilters] = None
    ) -> Dict[str, Any]:
        """Get detailed failure analysis.

        Args:
            filters: Optional filters to apply

        Returns:
            Dictionary with failure analysis data
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)
        agents = self.storage.load_agents(filters=filter_dict)

        # Count failures
        failed_executions = [e for e in executions if e.get("status") == "failed"]
        total_executions = len(executions)
        total_failures = len(failed_executions)
        failure_rate = (
            (total_failures / total_executions * 100.0) if total_executions > 0 else 0.0
        )

        # Get top errors
        error_messages = []
        for exec_data in failed_executions:
            if exec_data.get("error_message"):
                error_messages.append(exec_data["error_message"])
        for agent_data in agents:
            if agent_data.get("status") == "failed" and agent_data.get("error_message"):
                error_messages.append(agent_data["error_message"])

        error_counter = Counter(error_messages)
        top_errors = [
            {"error": error, "count": count}
            for error, count in error_counter.most_common(10)
        ]

        # Failures by region
        region_counter = Counter(
            a.get("region", "unknown")
            for a in agents
            if a.get("status") == "failed"
        )
        failure_by_region = [
            {"region": region, "count": count}
            for region, count in region_counter.most_common()
        ]

        return {
            "total_failures": total_failures,
            "failure_rate": round(failure_rate, 2),
            "top_errors": top_errors,
            "failure_by_region": failure_by_region,
        }

    def export_to_csv_format(
        self, filters: Optional[ReportFilters] = None
    ) -> List[List[str]]:
        """Export data to CSV format.

        Args:
            filters: Optional filters to apply

        Returns:
            List of rows, where each row is a list of string values
        """
        filter_dict = self._convert_filters(filters) if filters else None
        executions = self.storage.load_executions(filters=filter_dict)

        # Headers
        headers = [
            "Execution ID",
            "Scenario ID",
            "Scenario Name",
            "Status",
            "Started At",
            "Completed At",
            "Duration (seconds)",
            "Total Agents",
            "Successful Agents",
            "Failed Agents",
            "Error Message",
        ]

        rows = [headers]

        # Data rows
        for exec_data in executions:
            row = [
                str(exec_data.get("execution_id", "")),
                str(exec_data.get("scenario_id", "")),
                str(exec_data.get("scenario_name", "")),
                str(exec_data.get("status", "")),
                str(exec_data.get("started_at", "")),
                str(exec_data.get("completed_at", "")),
                str(exec_data.get("duration_seconds", "")),
                str(exec_data.get("total_agents", "")),
                str(exec_data.get("successful_agents", "")),
                str(exec_data.get("failed_agents", "")),
                str(exec_data.get("error_message", "")),
            ]
            rows.append(row)

        return rows

    def _convert_filters(self, filters: ReportFilters) -> Dict[str, Any]:
        """Convert ReportFilters to storage filter format.

        Args:
            filters: ReportFilters instance

        Returns:
            Dictionary for storage filtering
        """
        filter_dict: Dict[str, Any] = {}

        if filters.start_date:
            filter_dict["start_date"] = filters.start_date.isoformat()
        if filters.end_date:
            filter_dict["end_date"] = filters.end_date.isoformat()
        if filters.scenario_ids:
            # Storage expects single scenario_id, use first one
            if len(filters.scenario_ids) > 0:
                filter_dict["scenario_id"] = filters.scenario_ids[0]
        if filters.status:
            # Storage expects single status, use first one
            if len(filters.status) > 0:
                filter_dict["status"] = filters.status[0]

        return filter_dict
