---
layout: default
title: Reporting & Telemetry
nav_order: 7
description: "Comprehensive reporting and telemetry system for Azure HayMaker"
permalink: /reporting-telemetry/
---

# Reporting & Telemetry Guide
{: .no_toc }

Monitor, analyze, and visualize Azure HayMaker execution metrics with comprehensive reporting and interactive dashboards.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Azure HayMaker reporting and telemetry system provides comprehensive monitoring, analysis, and visualization of scenario execution metrics. It collects data asynchronously in the background with zero performance impact and generates rich interactive reports.

### Key Features

- **Async Background Collection**: Telemetry collection runs in the background without impacting scenario execution
- **Rich HTML Reports**: Interactive reports with Plotly charts and KPIs
- **Interactive TUI Dashboard**: Real-time monitoring with Textual-based interface
- **Local Storage**: Data stored locally in `~/.haymaker/telemetry/` with configurable retention
- **Multiple Report Types**: Summary, detailed, scenario-specific, and error analysis reports
- **Export Capabilities**: Export data to CSV for external analysis
- **Zero Configuration**: Works out of the box with sensible defaults

### Architecture Components

The system consists of three core modules:

1. **Telemetry Collection Module** (`cli/src/haymaker_cli/telemetry/`)
   - Collects agent execution data, resource tracking, error logs
   - Stores data in JSON Lines format
   - Automatic pruning based on retention policy

2. **Report Generation Module** (`cli/src/haymaker_cli/reports/`)
   - Generates self-contained HTML reports
   - Creates interactive Plotly visualizations
   - Supports CSV export

3. **Interactive TUI Module** (`cli/src/haymaker_cli/ui/`)
   - Real-time dashboard with auto-refresh
   - Keyboard navigation
   - Filtering and sorting

---

## Quick Start

### Enable Telemetry Collection

Start collecting telemetry data:

```bash
# Start telemetry collection
haymaker telemetry start

# Check collection status
haymaker telemetry status
```

Output:
```
Telemetry Collection Status:
  Status: Running
  Poll Interval: 300 seconds (5 minutes)
  Storage Path: /home/user/.haymaker/telemetry
  Retention Days: 30
  Data Points: 1,247
  Disk Usage: 2.3 MB
  Last Collection: 2025-11-26 14:32:15
```

### Generate Your First Report

Create a summary report:

```bash
# Generate summary report (opens in browser automatically)
haymaker report summary

# Generate report for last 7 days
haymaker report summary --days 7

# Generate report without opening browser
haymaker report summary --no-open
```

Output:
```
Generating summary report...
Report generated: /home/user/.haymaker/reports/summary_2025-11-26_143215.html
Opening in browser...
```

The browser opens with an interactive HTML report showing:
- **Success Rate KPI**: 94.2% (green indicator)
- **Total Executions**: 328 scenarios
- **Average Duration**: 47.3 minutes
- **Active Agents**: 12 currently running
- **Interactive Charts**:
  - Execution timeline (line chart)
  - Success/failure breakdown (pie chart)
  - Scenario performance comparison (bar chart)
  - Resource utilization over time (area chart)

### Launch Interactive Dashboard

View real-time metrics:

```bash
# Launch interactive dashboard
haymaker report dashboard
```

The terminal displays a full-screen TUI with:
- **Header Bar**: Current time, refresh countdown, active scenarios
- **KPI Panel**: Success rate, total executions, average duration, error count
- **Agent Table**: Scrollable list of agents with status, scenario, duration
- **Resource Graph**: ASCII chart showing resource creation/deletion
- **Footer**: Keyboard shortcuts (↑/↓ scroll, f filter, r refresh, q quit)

---

## Telemetry Collection

### Starting and Stopping Collection

Control telemetry collection:

```bash
# Start telemetry collection
haymaker telemetry start

# Start with custom poll interval (seconds)
haymaker telemetry start --interval 600

# Stop telemetry collection
haymaker telemetry stop

# Check current status
haymaker telemetry status
```

### Manual Collection

Collect telemetry data on demand:

```bash
# Collect data immediately
haymaker telemetry collect

# Collect data with verbose output
haymaker telemetry collect --verbose
```

Output:
```
Collecting telemetry data...
Connected to: https://haymaker-fastapi-app.azurewebsites.net
Fetched 45 agent records
Fetched 128 resource records
Fetched 12 error records
Data stored: /home/user/.haymaker/telemetry/2025-11-26.jsonl
Collection complete.
```

### Configuration

Configure telemetry collection in `~/.haymaker/config.yaml`:

```yaml
telemetry:
  # Enable/disable telemetry collection
  enabled: true

  # Automatically start collection on CLI startup
  auto_start: false

  # Polling interval in seconds (default: 300 = 5 minutes)
  poll_interval_seconds: 300

  # Data retention in days (default: 30)
  retention_days: 30

  # Storage path for telemetry data
  storage_path: ~/.haymaker/telemetry

  # Collect specific data types
  collect_agents: true
  collect_resources: true
  collect_errors: true
  collect_metrics: true
```

Update configuration via CLI:

```bash
# Set poll interval to 10 minutes
haymaker telemetry config --interval 600

# Set retention to 60 days
haymaker telemetry config --retention 60

# Enable auto-start
haymaker telemetry config --auto-start true

# Set custom storage path
haymaker telemetry config --storage-path /custom/path/telemetry
```

### Data Storage Format

Telemetry data is stored in JSON Lines format for efficient streaming and parsing:

**File Structure:**
```
~/.haymaker/telemetry/
├── 2025-11-26.jsonl    # Today's data
├── 2025-11-25.jsonl    # Yesterday
├── 2025-11-24.jsonl
└── ...                  # Older data (auto-pruned after retention period)
```

**Record Format:**
```json
{"timestamp": "2025-11-26T14:32:15Z", "type": "agent", "agent_id": "agent-123", "scenario": "compute-01", "status": "running", "duration_seconds": 2847}
{"timestamp": "2025-11-26T14:32:15Z", "type": "resource", "resource_id": "vm-456", "resource_type": "Microsoft.Compute/virtualMachines", "status": "created", "execution_id": "exec-789"}
{"timestamp": "2025-11-26T14:32:16Z", "type": "error", "agent_id": "agent-124", "error_type": "DeploymentError", "message": "Resource quota exceeded"}
```

### Data Retention

Manage data retention automatically or manually:

```bash
# Prune old data based on retention policy (automatic)
haymaker telemetry prune

# Prune data with verbose output
haymaker telemetry prune --verbose

# Prune data older than specific date
haymaker telemetry prune --before 2025-10-01

# Dry run (show what would be deleted)
haymaker telemetry prune --dry-run
```

Output:
```
Pruning telemetry data...
Retention policy: 30 days
Cutoff date: 2025-10-27
Files to delete: 5 (12.4 MB)
  - 2025-10-26.jsonl (2.3 MB)
  - 2025-10-25.jsonl (2.5 MB)
  - 2025-10-24.jsonl (2.1 MB)
  - 2025-10-23.jsonl (2.8 MB)
  - 2025-10-22.jsonl (2.7 MB)
Deleted 5 files, freed 12.4 MB
```

### Troubleshooting Collection

#### Collection Not Starting

**Problem:** `haymaker telemetry start` returns error

**Solutions:**
1. Check orchestrator endpoint is configured:
```bash
haymaker config get endpoint
```

2. Verify authentication:
```bash
haymaker status
```

3. Check disk space:
```bash
df -h ~/.haymaker/telemetry
```

#### High Disk Usage

**Problem:** Telemetry data consuming too much disk space

**Solutions:**
1. Reduce retention period:
```bash
haymaker telemetry config --retention 14
```

2. Manually prune old data:
```bash
haymaker telemetry prune --before 2025-11-01
```

3. Disable collection temporarily:
```bash
haymaker telemetry stop
```

#### Missing Data

**Problem:** Reports show incomplete or missing data

**Solutions:**
1. Check collection status:
```bash
haymaker telemetry status
```

2. Manually collect data:
```bash
haymaker telemetry collect --verbose
```

3. Verify storage path permissions:
```bash
ls -la ~/.haymaker/telemetry/
```

---

## Report Generation

### Summary Report

Generate high-level overview reports:

```bash
# Generate summary report for last 7 days
haymaker report summary --days 7

# Generate summary for specific date range
haymaker report summary --start 2025-11-01 --end 2025-11-26

# Generate without opening browser
haymaker report summary --no-open

# Specify output location
haymaker report summary --output /custom/path/report.html
```

**Summary Report Contents:**
- **Executive KPIs**: Success rate, total executions, average duration, error count
- **Execution Timeline**: Line chart showing executions over time with success/failure indicators
- **Scenario Performance**: Bar chart comparing scenario success rates
- **Resource Utilization**: Area chart showing resource creation and deletion patterns
- **Top Errors**: Table listing most common errors with frequency
- **Agent Statistics**: Table showing agent execution metrics

### Detailed Report

Generate comprehensive reports with all metrics:

```bash
# Generate detailed report
haymaker report detailed --days 30

# Include full agent logs
haymaker report detailed --include-logs

# Filter by scenario
haymaker report detailed --scenario compute-01

# Group by execution
haymaker report detailed --group-by execution
```

**Detailed Report Contents:**
- All summary report elements
- **Agent Execution Details**: Complete timeline of agent lifecycle
- **Resource Breakdown**: Detailed resource creation/deletion table
- **Error Analysis**: Full error logs with stack traces
- **Performance Metrics**: P50, P95, P99 latency metrics
- **Cost Estimates**: Estimated Azure costs per scenario
- **Execution Timeline**: Gantt chart showing agent execution overlap

### Scenario-Specific Report

Generate reports for specific scenarios:

```bash
# Report for single scenario
haymaker report scenario compute-01-linux-vm-web-server

# Report for scenario pattern
haymaker report scenario compute-*

# Include resource details
haymaker report scenario compute-01 --include-resources

# Compare scenario performance over time
haymaker report scenario compute-01 --compare-periods
```

**Scenario Report Contents:**
- **Scenario Overview**: Description, resource types, typical duration
- **Execution History**: Timeline of all executions for this scenario
- **Success Rate Trend**: Line chart showing success rate over time
- **Duration Analysis**: Box plot showing duration distribution
- **Resource Patterns**: Bar chart showing resource types created
- **Common Errors**: Table of errors specific to this scenario
- **Recommendations**: Automated suggestions for optimization

### Error Analysis Report

Generate reports focused on errors and failures:

```bash
# Generate error report
haymaker report errors --days 7

# Filter by error type
haymaker report errors --type DeploymentError

# Group by scenario
haymaker report errors --group-by scenario

# Include resolution suggestions
haymaker report errors --suggest-fixes
```

**Error Report Contents:**
- **Error Summary**: Total errors, error rate, most common types
- **Error Timeline**: Line chart showing error frequency over time
- **Error Distribution**: Pie chart showing error types
- **Top Failing Scenarios**: Table of scenarios with highest error rates
- **Error Details**: Expandable table with full error messages and context
- **Resolution Suggestions**: Automated recommendations for each error type

### Export Data

Export telemetry data for external analysis:

```bash
# Export to CSV
haymaker report export csv --output metrics.csv

# Export specific data types
haymaker report export csv --type agents --output agents.csv
haymaker report export csv --type resources --output resources.csv
haymaker report export csv --type errors --output errors.csv

# Export with filtering
haymaker report export csv --days 30 --scenario compute-01 --output compute_metrics.csv

# Export to JSON
haymaker report export json --output metrics.json
```

**CSV Export Format:**

agents.csv:
```csv
timestamp,agent_id,scenario,status,duration_seconds,error_count,success
2025-11-26T14:32:15Z,agent-123,compute-01,completed,2847,0,true
2025-11-26T14:35:22Z,agent-124,database-01,failed,1245,2,false
```

resources.csv:
```csv
timestamp,resource_id,resource_type,scenario,execution_id,status,region
2025-11-26T14:32:15Z,vm-456,Microsoft.Compute/virtualMachines,compute-01,exec-789,created,eastus
2025-11-26T14:35:22Z,vm-456,Microsoft.Compute/virtualMachines,compute-01,exec-789,deleted,eastus
```

### Report Configuration

Configure report generation in `~/.haymaker/config.yaml`:

```yaml
reports:
  # Default output format (html, csv, json)
  default_format: html

  # Output directory for generated reports
  output_path: ~/.haymaker/reports

  # Automatically open reports in browser
  auto_open: true

  # Chart theme (plotly, plotly_white, plotly_dark, ggplot2, seaborn)
  chart_theme: plotly_white

  # Chart colors
  colors:
    success: '#10b981'     # Green
    failure: '#ef4444'     # Red
    running: '#3b82f6'     # Blue
    pending: '#6b7280'     # Gray

  # Include sections in reports
  include:
    kpis: true
    charts: true
    tables: true
    logs: false            # Large, disabled by default
    recommendations: true
```

Update configuration via CLI:

```bash
# Set chart theme
haymaker report config --theme plotly_dark

# Disable auto-open
haymaker report config --auto-open false

# Set output directory
haymaker report config --output-path /custom/reports
```

### Opening Reports

Reports are saved as self-contained HTML files:

```bash
# Open most recent report
haymaker report open

# Open specific report
haymaker report open summary_2025-11-26_143215.html

# List available reports
haymaker report list

# Delete old reports
haymaker report clean --days 30
```

---

## Interactive Dashboard

### Launching the Dashboard

Start the interactive TUI dashboard:

```bash
# Launch dashboard with defaults
haymaker report dashboard

# Launch with custom refresh interval (seconds)
haymaker report dashboard --refresh 10

# Launch with specific theme
haymaker report dashboard --theme dark

# Launch with initial filter
haymaker report dashboard --filter running
```

### Dashboard Layout

The dashboard displays:

**Header Bar:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Azure HayMaker Dashboard     2025-11-26 14:32:15     Refresh in: 5s    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**KPI Panel:**
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Success Rate ┃   Executions ┃ Avg Duration ┃       Errors ┃
┃              ┃              ┃              ┃              ┃
┃    94.2% ✓   ┃      328     ┃   47.3 min   ┃      19      ┃
┗━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━┛
```

**Agent Table:**
```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Agent ID   ┃ Scenario               ┃ Status   ┃ Duration ┃ Errors ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ agent-123  │ compute-01-linux-vm    │ Running  │ 47m 23s  │ 0      │
│ agent-124  │ database-01-cosmosdb   │ Running  │ 32m 18s  │ 0      │
│ agent-125  │ container-01-aks       │ Complete │ 1h 15m   │ 0      │
│ agent-126  │ ai-01-openai-chat      │ Failed   │ 5m 42s   │ 2      │
└────────────┴────────────────────────┴──────────┴──────────┴────────┘
```

**Resource Graph:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Resource Activity (Last 24 Hours)                                     ┃
┃                                                                        ┃
┃  50 │                        ▄▄▄                                      ┃
┃  40 │                  ▄▄▄▄▄▄███▄▄▄▄                                  ┃
┃  30 │            ▄▄▄▄▄▄█████████████▄▄▄▄                              ┃
┃  20 │      ▄▄▄▄▄▄█████████████████████▄▄▄▄▄                          ┃
┃  10 │▄▄▄▄▄▄███████████████████████████████▄▄▄▄▄                      ┃
┃   0 │────────────────────────────────────────────────────────────    ┃
┃       0h    4h    8h    12h   16h   20h   24h                         ┃
┃                                                                        ┃
┃       ■ Created    ■ Active    ■ Deleted                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Footer:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ↑/↓: Navigate  f: Filter  s: Sort  r: Refresh  e: Export  q: Quit    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Keyboard Shortcuts

Navigate and interact with the dashboard using keyboard shortcuts:

| Key       | Action                          |
|:----------|:--------------------------------|
| `↑`/`k`   | Scroll up in agent table        |
| `↓`/`j`   | Scroll down in agent table      |
| `PgUp`    | Page up                         |
| `PgDn`    | Page down                       |
| `Home`    | Jump to top                     |
| `End`     | Jump to bottom                  |
| `f`       | Open filter dialog              |
| `s`       | Cycle sort order                |
| `r`       | Refresh immediately             |
| `e`       | Export current view to CSV      |
| `d`       | Toggle details pane             |
| `t`       | Cycle theme (dark/light)        |
| `q`       | Quit dashboard                  |
| `?`       | Show help                       |

### Filtering and Sorting

Filter agents by criteria:

**Filter Dialog (press `f`):**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Filter Agents                   ┃
┃                                 ┃
┃ Status: [All ▼]                 ┃
┃   • All                         ┃
┃   • Running                     ┃
┃   • Completed                   ┃
┃   • Failed                      ┃
┃                                 ┃
┃ Scenario: [All ▼]               ┃
┃   • All                         ┃
┃   • compute-*                   ┃
┃   • database-*                  ┃
┃   • container-*                 ┃
┃                                 ┃
┃ Time Range: [24h ▼]             ┃
┃   • Last Hour                   ┃
┃   • Last 24 Hours               ┃
┃   • Last 7 Days                 ┃
┃   • Last 30 Days                ┃
┃                                 ┃
┃     [Apply]      [Cancel]       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Sort Options (press `s`):**
- **Status**: Running → Failed → Completed
- **Duration**: Longest to shortest
- **Scenario**: Alphabetical
- **Agent ID**: Alphabetical
- **Error Count**: Highest to lowest

### Exporting from Dashboard

Export current dashboard view:

**Export Dialog (press `e`):**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Export Dashboard View           ┃
┃                                 ┃
┃ Format: [CSV ▼]                 ┃
┃   • CSV                         ┃
┃   • JSON                        ┃
┃   • HTML                        ┃
┃                                 ┃
┃ Include: [✓] KPIs               ┃
┃          [✓] Agent Table        ┃
┃          [✓] Resource Graph     ┃
┃          [ ] Full Logs          ┃
┃                                 ┃
┃ Output: dashboard_export.csv    ┃
┃                                 ┃
┃     [Export]     [Cancel]       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

After export:
```
Export complete: /home/user/.haymaker/reports/dashboard_export_2025-11-26_143215.csv
```

### Dashboard Configuration

Configure dashboard appearance in `~/.haymaker/config.yaml`:

```yaml
ui:
  # Auto-refresh interval in seconds
  refresh_interval_seconds: 5

  # Color theme (dark, light, auto)
  theme: dark

  # Number of rows per page in tables
  page_size: 50

  # Show resource graph
  show_resource_graph: true

  # Graph height in lines
  graph_height: 10

  # Date/time format
  datetime_format: '%Y-%m-%d %H:%M:%S'

  # KPI thresholds
  thresholds:
    success_rate_warning: 90.0    # Yellow below this
    success_rate_critical: 80.0   # Red below this
    error_count_warning: 10
    error_count_critical: 50
```

Update configuration via CLI:

```bash
# Set refresh interval to 10 seconds
haymaker report dashboard-config --refresh 10

# Set theme
haymaker report dashboard-config --theme light

# Set page size
haymaker report dashboard-config --page-size 100
```

### Dashboard Troubleshooting

#### Dashboard Not Rendering

**Problem:** Dashboard displays garbled characters or crashes

**Solutions:**
1. Check terminal supports UTF-8:
```bash
echo $LANG
export LANG=en_US.UTF-8
```

2. Check terminal size:
```bash
# Minimum 80x24, recommended 120x40
tput cols
tput lines
```

3. Use simpler theme:
```bash
haymaker report dashboard --theme simple
```

#### High CPU Usage

**Problem:** Dashboard consumes excessive CPU

**Solutions:**
1. Increase refresh interval:
```bash
haymaker report dashboard --refresh 30
```

2. Reduce page size:
```bash
haymaker report dashboard-config --page-size 25
```

3. Disable resource graph:
```bash
haymaker report dashboard-config --show-resource-graph false
```

#### Data Not Updating

**Problem:** Dashboard shows stale data

**Solutions:**
1. Check telemetry collection is running:
```bash
haymaker telemetry status
```

2. Manually refresh (press `r` in dashboard)

3. Check network connectivity:
```bash
haymaker status
```

---

## Configuration Reference

Complete configuration reference for `~/.haymaker/config.yaml`:

```yaml
# Telemetry Collection Configuration
telemetry:
  # Enable telemetry collection
  enabled: true

  # Auto-start collection when CLI starts
  auto_start: false

  # Polling interval in seconds (how often to collect data)
  poll_interval_seconds: 300

  # Data retention period in days
  retention_days: 30

  # Local storage path for telemetry data
  storage_path: ~/.haymaker/telemetry

  # Data types to collect
  collect_agents: true
  collect_resources: true
  collect_errors: true
  collect_metrics: true

  # Collection options
  batch_size: 1000                    # Records per collection batch
  max_file_size_mb: 100               # Max size per JSONL file
  compression: false                  # Compress old files (gzip)

# Report Generation Configuration
reports:
  # Default output format (html, csv, json)
  default_format: html

  # Output directory for reports
  output_path: ~/.haymaker/reports

  # Auto-open reports in browser
  auto_open: true

  # Chart visualization theme
  chart_theme: plotly_white

  # Color scheme for charts
  colors:
    success: '#10b981'
    failure: '#ef4444'
    running: '#3b82f6'
    pending: '#6b7280'
    warning: '#f59e0b'

  # Report sections to include
  include:
    kpis: true
    charts: true
    tables: true
    logs: false                       # Large, disabled by default
    recommendations: true

  # Chart configuration
  charts:
    height: 400                        # Chart height in pixels
    width: 800                         # Chart width in pixels
    dpi: 100                           # Resolution
    show_legend: true
    show_grid: true

  # Table configuration
  tables:
    max_rows: 1000                     # Max rows in HTML tables
    show_index: true
    sortable: true

# Dashboard UI Configuration
ui:
  # Auto-refresh interval in seconds
  refresh_interval_seconds: 5

  # Color theme (dark, light, auto)
  theme: dark

  # Rows per page
  page_size: 50

  # Show resource activity graph
  show_resource_graph: true

  # Graph height in terminal lines
  graph_height: 10

  # Date/time display format
  datetime_format: '%Y-%m-%d %H:%M:%S'

  # KPI warning/critical thresholds
  thresholds:
    success_rate_warning: 90.0
    success_rate_critical: 80.0
    error_count_warning: 10
    error_count_critical: 50
    duration_warning_minutes: 60
    duration_critical_minutes: 120

  # Keyboard shortcuts (customizable)
  shortcuts:
    scroll_up: ['up', 'k']
    scroll_down: ['down', 'j']
    filter: ['f']
    sort: ['s']
    refresh: ['r']
    export: ['e']
    quit: ['q']
    help: ['?']
```

---

## Architecture

### System Architecture

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  Azure HayMaker CLI                     ┃
┗━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                   │
    ┏━━━━━━━━━━━━━━┼━━━━━━━━━━━━━━┓
    │              │               │
┏━━━▼━━━━┓  ┏━━━━━▼━━━━━┓  ┏━━━━━▼━━━━━┓
┃Telemetry┃  ┃  Reports  ┃  ┃    UI     ┃
┃Collection┃  ┃ Generator ┃  ┃ Dashboard ┃
┗━━━┬━━━━┘  ┗━━━━┬━━━━━┘  ┗━━━━┬━━━━━┛
    │            │              │
    │  ┏━━━━━━━━━▼━━━━━━━━━┓   │
    │  ┃ Local Storage     ┃   │
    │  ┃ (~/.haymaker/)    ┃   │
    │  ┗━━━━━━━━━┬━━━━━━━━━┛   │
    │            │              │
    └────────────┴──────────────┘
                 │
         ┏━━━━━━━▼━━━━━━━┓
         ┃  Orchestrator ┃
         ┃      API      ┃
         ┗━━━━━━━━━━━━━━━┛
```

### Data Flow

1. **Collection Phase**:
   - Background process polls orchestrator API every 5 minutes
   - Fetches agent execution data, resource tracking, error logs
   - Stores data in JSON Lines format (one record per line)
   - Automatically prunes data older than retention period

2. **Storage Phase**:
   - Data stored in `~/.haymaker/telemetry/YYYY-MM-DD.jsonl`
   - Each file contains one day's data
   - Efficient streaming format for large datasets
   - Optional compression for archival

3. **Analysis Phase**:
   - Report generator reads JSONL files
   - Aggregates metrics (success rate, duration, error counts)
   - Generates visualizations using Plotly
   - Creates self-contained HTML reports

4. **Visualization Phase**:
   - TUI dashboard reads JSONL files directly
   - Real-time aggregation for current metrics
   - Interactive filtering and sorting
   - Export capabilities

### Module Structure

```
cli/src/haymaker_cli/
├── telemetry/
│   ├── __init__.py
│   ├── collector.py         # Background collection logic
│   ├── storage.py           # JSONL read/write operations
│   ├── pruner.py            # Data retention management
│   └── commands.py          # Telemetry CLI commands
├── reports/
│   ├── __init__.py
│   ├── generator.py         # HTML report generation
│   ├── charts.py            # Plotly chart creation
│   ├── exporters.py         # CSV/JSON export
│   └── commands.py          # Report CLI commands
├── ui/
│   ├── __init__.py
│   ├── dashboard.py         # Textual TUI main app
│   ├── widgets.py           # Custom UI widgets
│   ├── filters.py           # Filtering logic
│   └── commands.py          # Dashboard CLI commands
└── main.py                  # CLI entry point
```

### Dependencies

Core dependencies for reporting and telemetry:

```python
# Report generation
plotly>=5.17.0              # Interactive charts
jinja2>=3.1.2               # HTML templating
pandas>=2.1.0               # Data analysis

# Interactive dashboard
textual>=0.40.0             # TUI framework
rich>=13.6.0                # Terminal formatting

# Data handling
jsonlines>=4.0.0            # JSONL format
pydantic>=2.4.0             # Data validation

# CLI framework
click>=8.1.7                # Command-line interface
```

---

## Usage Examples

### Example 1: Daily Monitoring Workflow

Monitor HayMaker execution daily:

```bash
# Start telemetry collection (once)
haymaker telemetry start

# Each morning: Generate summary report
haymaker report summary --days 1

# Review dashboard for real-time status
haymaker report dashboard
```

### Example 2: Troubleshooting Failed Scenario

Investigate a failing scenario:

```bash
# Generate error report for specific scenario
haymaker report errors --scenario database-01-cosmosdb --days 7

# View detailed scenario report
haymaker report scenario database-01-cosmosdb --include-resources

# Export error data for analysis
haymaker report export csv --type errors --scenario database-01 --output db_errors.csv
```

### Example 3: Performance Analysis

Analyze scenario performance over time:

```bash
# Generate detailed report for last 30 days
haymaker report detailed --days 30

# Compare scenario performance
haymaker report summary --days 30 --group-by scenario

# Export metrics for spreadsheet analysis
haymaker report export csv --output monthly_metrics.csv
```

### Example 4: Weekly Executive Report

Generate weekly summary for stakeholders:

```bash
# Generate comprehensive weekly report
haymaker report summary --days 7 --output weekly_report.html

# Include detailed metrics
haymaker report detailed --days 7 --output weekly_detailed.html

# Export key metrics as CSV
haymaker report export csv --days 7 --output weekly_metrics.csv
```

### Example 5: Real-Time Operations Monitoring

Monitor active operations:

```bash
# Launch dashboard in follow mode
haymaker report dashboard --refresh 10

# In dashboard:
# - Press 'f' to filter for running agents
# - Press 's' to sort by duration
# - Press 'e' to export snapshot
```

### Example 6: Automated Reporting Script

Create automated reporting script:

```bash
#!/bin/bash
# daily_report.sh - Generate daily HayMaker reports

DATE=$(date +%Y-%m-%d)
REPORT_DIR="/reports/haymaker/${DATE}"

# Create report directory
mkdir -p "${REPORT_DIR}"

# Generate summary report
haymaker report summary --days 1 \
  --output "${REPORT_DIR}/summary.html" \
  --no-open

# Generate error report
haymaker report errors --days 1 \
  --output "${REPORT_DIR}/errors.html" \
  --no-open

# Export metrics as CSV
haymaker report export csv --days 1 \
  --output "${REPORT_DIR}/metrics.csv"

# Prune old telemetry data
haymaker telemetry prune --before $(date -d '30 days ago' +%Y-%m-%d)

echo "Reports generated: ${REPORT_DIR}"
```

Run script via cron:

```bash
# Add to crontab: daily at 8 AM
0 8 * * * /path/to/daily_report.sh
```

### Example 7: CI/CD Integration

Integrate reporting into CI/CD pipeline:

```yaml
# .github/workflows/haymaker-report.yml
name: HayMaker Daily Report

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM UTC

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - name: Install HayMaker CLI
        run: pip install haymaker-cli

      - name: Configure CLI
        run: |
          haymaker config set endpoint ${{ secrets.HAYMAKER_ENDPOINT }}
          haymaker config set api-key ${{ secrets.HAYMAKER_API_KEY }}

      - name: Collect telemetry
        run: haymaker telemetry collect

      - name: Generate report
        run: |
          haymaker report summary --days 1 --output summary.html --no-open
          haymaker report export csv --days 1 --output metrics.csv

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: haymaker-reports
          path: |
            summary.html
            metrics.csv
```

---

## Troubleshooting

### General Issues

#### Configuration Not Found

**Problem:** `Configuration file not found: ~/.haymaker/config.yaml`

**Solution:**
```bash
# Create default configuration
haymaker config set endpoint https://haymaker-fastapi-app.azurewebsites.net
haymaker config set api-key your-api-key

# Verify configuration
haymaker config list
```

#### Permission Denied

**Problem:** `Permission denied: ~/.haymaker/telemetry/`

**Solution:**
```bash
# Fix permissions
chmod 755 ~/.haymaker
chmod 755 ~/.haymaker/telemetry
chmod 644 ~/.haymaker/telemetry/*.jsonl

# Or use custom path
haymaker telemetry config --storage-path /custom/path
```

### Collection Issues

#### Collection Failing

**Problem:** Telemetry collection fails with API errors

**Solutions:**
1. Verify endpoint configuration:
```bash
haymaker config get endpoint
```

2. Test orchestrator connectivity:
```bash
curl $(haymaker config get endpoint)/api/status
```

3. Check authentication:
```bash
haymaker status
```

4. Review collection logs:
```bash
tail -f ~/.haymaker/logs/telemetry.log
```

#### Missing Data Points

**Problem:** Telemetry shows gaps in data

**Solutions:**
1. Check collection was running:
```bash
haymaker telemetry status
```

2. Manually collect missing data:
```bash
haymaker telemetry collect --verbose
```

3. Verify orchestrator API was available during gap period

### Report Generation Issues

#### Report Generation Fails

**Problem:** `Failed to generate report: No data available`

**Solutions:**
1. Verify telemetry data exists:
```bash
ls -lh ~/.haymaker/telemetry/
```

2. Check date range:
```bash
# List available data files
ls ~/.haymaker/telemetry/*.jsonl
```

3. Collect data manually:
```bash
haymaker telemetry collect
```

4. Try shorter date range:
```bash
haymaker report summary --days 1
```

#### Charts Not Displaying

**Problem:** HTML reports show blank charts

**Solutions:**
1. Check browser JavaScript is enabled

2. View report in different browser

3. Check file is not corrupted:
```bash
file report.html
# Should show: HTML document
```

4. Regenerate report:
```bash
haymaker report summary --output new_report.html
```

#### Report Too Large

**Problem:** Report file is very large (>100 MB)

**Solutions:**
1. Reduce date range:
```bash
haymaker report summary --days 7  # Instead of 30
```

2. Disable logs:
```bash
haymaker report config --include-logs false
```

3. Use CSV export instead:
```bash
haymaker report export csv --output metrics.csv
```

### Dashboard Issues

#### Dashboard Crashes on Startup

**Problem:** Dashboard exits immediately with error

**Solutions:**
1. Check terminal compatibility:
```bash
echo $TERM
# Should be xterm-256color or similar
export TERM=xterm-256color
```

2. Check terminal size:
```bash
# Minimum 80x24
resize -s 40 120
```

3. Use simple mode:
```bash
haymaker report dashboard --theme simple
```

4. Check Python version:
```bash
python --version
# Required: Python 3.9+
```

#### Slow Dashboard Performance

**Problem:** Dashboard is sluggish or unresponsive

**Solutions:**
1. Increase refresh interval:
```bash
haymaker report dashboard --refresh 30
```

2. Reduce page size:
```bash
haymaker report dashboard-config --page-size 25
```

3. Disable resource graph:
```bash
haymaker report dashboard-config --show-resource-graph false
```

4. Filter to reduce data:
```bash
# Press 'f' in dashboard, filter to last 24 hours
```

#### Dashboard Not Auto-Refreshing

**Problem:** Dashboard shows stale data, not updating

**Solutions:**
1. Check telemetry collection is running:
```bash
haymaker telemetry status
```

2. Manually refresh (press `r` in dashboard)

3. Restart with shorter interval:
```bash
haymaker report dashboard --refresh 5
```

---

## Command Reference

Complete reference of reporting and telemetry commands:

### Telemetry Commands

```bash
# Start/stop collection
haymaker telemetry start [--interval SECONDS]
haymaker telemetry stop

# Check status
haymaker telemetry status [--format FORMAT]

# Collect data manually
haymaker telemetry collect [--verbose]

# Prune old data
haymaker telemetry prune [--before DATE] [--dry-run] [--verbose]

# Configuration
haymaker telemetry config [OPTIONS]
  --interval SECONDS           # Poll interval
  --retention DAYS             # Retention period
  --storage-path PATH          # Storage location
  --auto-start true|false      # Auto-start on CLI startup
```

### Report Commands

```bash
# Summary report
haymaker report summary [OPTIONS]
  --days N                     # Report period (default: 7)
  --start DATE                 # Start date (YYYY-MM-DD)
  --end DATE                   # End date (YYYY-MM-DD)
  --output FILE                # Output file path
  --no-open                    # Don't open in browser
  --format html|pdf            # Output format

# Detailed report
haymaker report detailed [OPTIONS]
  --days N                     # Report period
  --scenario NAME              # Filter by scenario
  --include-logs               # Include full logs
  --group-by execution|scenario|date

# Scenario report
haymaker report scenario SCENARIO [OPTIONS]
  --days N                     # Report period
  --include-resources          # Include resource details
  --compare-periods            # Compare time periods

# Error report
haymaker report errors [OPTIONS]
  --days N                     # Report period
  --type ERROR_TYPE            # Filter by error type
  --scenario NAME              # Filter by scenario
  --group-by type|scenario|date
  --suggest-fixes              # Include fix suggestions

# Export data
haymaker report export FORMAT [OPTIONS]
  --type agents|resources|errors|all
  --output FILE                # Output file path
  --days N                     # Time period
  --scenario NAME              # Filter by scenario

# Report management
haymaker report open [FILE]              # Open report
haymaker report list                     # List reports
haymaker report clean [--days N]         # Delete old reports

# Configuration
haymaker report config [OPTIONS]
  --theme THEME                # Chart theme
  --auto-open true|false       # Auto-open reports
  --output-path PATH           # Report directory
```

### Dashboard Commands

```bash
# Launch dashboard
haymaker report dashboard [OPTIONS]
  --refresh SECONDS            # Refresh interval (default: 5)
  --theme dark|light|auto      # Color theme
  --filter STATUS              # Initial filter (running|completed|failed)

# Dashboard configuration
haymaker report dashboard-config [OPTIONS]
  --refresh SECONDS            # Default refresh interval
  --theme THEME                # Default theme
  --page-size N                # Rows per page
  --show-resource-graph BOOL   # Show/hide graph
```

---

## Related Documentation

For more information on Azure HayMaker CLI:

- [CLI Guide](/AzureHayMaker/cli/) - Complete CLI command reference
- [API Reference](/AzureHayMaker/api/) - Orchestrator API documentation
- [Architecture](/AzureHayMaker/architecture/) - System architecture overview
- [Scenarios](/AzureHayMaker/scenarios/) - Available scenario catalog
- [Troubleshooting](/AzureHayMaker/reference/troubleshooting) - General troubleshooting guide

For telemetry system implementation:

- [Source: telemetry/collector.py](https://github.com/rysweet/AzureHayMaker/blob/main/cli/src/haymaker_cli/telemetry/collector.py)
- [Source: reports/generator.py](https://github.com/rysweet/AzureHayMaker/blob/main/cli/src/haymaker_cli/reports/generator.py)
- [Source: ui/dashboard.py](https://github.com/rysweet/AzureHayMaker/blob/main/cli/src/haymaker_cli/ui/dashboard.py)

---

## Support

For issues and questions about reporting and telemetry:

- **GitHub Issues**: [Report a bug](https://github.com/rysweet/AzureHayMaker/issues/new?labels=reporting,telemetry)
- **Documentation**: [Browse all docs](https://github.com/rysweet/AzureHayMaker/tree/main/docs)
- **Examples**: [View code samples](https://github.com/rysweet/AzureHayMaker/tree/main/examples)

---

**Last Updated:** 2025-11-26
**Feature Version:** 0.2.0
**Tested in:** ATEVET12 tenant
