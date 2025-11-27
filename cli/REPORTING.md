# HayMaker CLI Reporting

The HayMaker CLI provides reporting commands to generate HTML reports from orchestrator metrics.

## Features

- **Summary Reports**: Overview of all executions, agents, and resources across all scenarios
- **Scenario Reports**: Detailed reports for specific scenarios with agent and resource breakdowns
- **Uses Orchestrator API**: Fetches aggregated metrics directly from the orchestrator's `/api/metrics` endpoint
- **HTML Output**: Clean, professional HTML reports with CSS styling

## Commands

### Generate Summary Report

Generate an overview report for all scenarios:

```bash
# Basic summary report (30-day period)
haymaker report summary

# Custom time period
haymaker report summary --period 90d

# Filter by scenario
haymaker report summary --scenario compute-01

# Custom output file
haymaker report summary --output my-report.html
```

**Options:**
- `--period [7d|30d|90d]`: Time period for metrics (default: 30d)
- `--scenario TEXT`: Filter by scenario name
- `-o, --output PATH`: Output file path (default: report.html)

**Output includes:**
- Total executions and success rate
- Active agents and resources
- Per-scenario metrics (runs, success/fail counts, average duration)
- Resources grouped by type

### Generate Scenario Report

Generate a detailed report for a specific scenario:

```bash
# Basic scenario report
haymaker report scenario compute-01

# Custom time period
haymaker report scenario compute-01 --period 90d

# Custom output file
haymaker report scenario network-01 --output network-report.html
```

**Arguments:**
- `SCENARIO_NAME`: Name of the scenario to report on (required)

**Options:**
- `--period [7d|30d|90d]`: Time period for metrics (default: 30d)
- `-o, --output PATH`: Output file path (default: {scenario}-report.html)

**Output includes:**
- Scenario-specific metrics (runs, success rate, average duration)
- Active resources for this scenario
- Recent agents (last 20) with status and timestamps
- Resources grouped by type
- Recent resources (last 50) with creation/deletion timestamps

## Implementation Details

### Architecture

The reporting system uses a simple architecture:

1. **report.py**: CLI commands that fetch data from the orchestrator
2. **report_generator.py**: HTML generation using metrics from the orchestrator API
3. **No local storage**: All data comes from the orchestrator's `/api/metrics` endpoint

### Data Sources

Reports query the orchestrator API:

```python
# Fetch aggregated metrics (no raw executions needed!)
metrics = client.get_metrics(period="30d", scenario=None)
# Returns: MetricsSummary with total_executions, success_rate, scenarios[], etc.

# Fetch agent list
agents = client.list_agents(limit=100)

# Fetch resource list
resources = client.list_resources(scenario="compute-01", limit=1000)
```

### Key Classes

#### `ReportGenerator`

Generates HTML reports from orchestrator metrics:

```python
from haymaker_cli.report_generator import ReportGenerator
from haymaker_cli.client import SyncHayMakerClient

client = SyncHayMakerClient(endpoint, auth)
generator = ReportGenerator(client)

# Generate summary report
generator.generate_summary_report(
    metrics=metrics,
    agents=agents,
    resources=resources,
    output_path=Path("report.html")
)

# Generate scenario report
generator.generate_scenario_report(
    scenario_name="compute-01",
    metrics=metrics,
    agents=scenario_agents,
    resources=scenario_resources,
    output_path=Path("compute-01-report.html")
)
```

## Testing

Run report generator tests:

```bash
cd cli
pytest tests/test_report_generator.py -v
```

Tests cover:
- Report generation with sample data
- Statistics calculation
- Resource grouping by type
- Empty data handling
- Missing scenario metrics

## Examples

### Example 1: Weekly Summary Report

Generate a summary report for the last 7 days:

```bash
haymaker report summary --period 7d --output weekly-report.html
```

### Example 2: Scenario Deep Dive

Generate a detailed report for a specific scenario over 90 days:

```bash
haymaker report scenario compute-01-linux-vm-web-server --period 90d
```

### Example 3: Multi-Scenario Comparison

Generate reports for multiple scenarios:

```bash
#!/bin/bash
for scenario in compute-01 network-01 storage-01; do
    haymaker report scenario $scenario --period 30d --output "${scenario}-report.html"
done
```

## Output Format

Reports are generated as standalone HTML files with:

- **Responsive design**: Works on desktop and mobile
- **Clean styling**: Professional gradient headers and card layouts
- **No external dependencies**: All CSS is inline
- **Data tables**: Sortable tables with hover effects
- **KPI cards**: Key metrics displayed prominently
- **Color coding**: Success (green), failure (red), warning (yellow)

## Future Enhancements

Potential improvements:

- [ ] CSV/JSON export options
- [ ] Chart generation (using chart.js or similar)
- [ ] Email report delivery
- [ ] Scheduled report generation
- [ ] Report comparison (period-over-period)
- [ ] Custom report templates
- [ ] Resource cost analysis
