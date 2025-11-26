# Telemetry & Reporting Test Suite Summary

## Overview

This test suite provides comprehensive TDD coverage for the HayMaker telemetry and reporting system. All tests are designed to **FAIL INITIALLY** (since no implementation exists yet) and will guide the implementation process.

**Total Test Files**: 15
**Total Test Methods**: 317
**Test Distribution**: 60% Unit, 30% Integration, 10% E2E (following testing pyramid)

## Test Structure

```
cli/tests/
├── fixtures/
│   └── sample_data.py              # Reusable test data generators
├── telemetry/
│   ├── conftest.py                 # Telemetry test fixtures
│   ├── test_collector.py           # TelemetryCollector tests (30 tests)
│   ├── test_config.py              # TelemetryConfig tests (19 tests)
│   ├── test_models.py              # Data model tests (27 tests)
│   └── test_storage.py             # TelemetryStorage tests (28 tests)
├── reports/
│   ├── conftest.py                 # Report test fixtures
│   ├── test_data.py                # ReportDataProcessor tests (28 tests)
│   ├── test_generator.py           # ReportGenerator tests (30 tests)
│   └── test_models.py              # Report model tests (22 tests)
├── ui/
│   ├── test_dashboard.py           # Dashboard UI tests (26 tests)
│   └── test_widgets.py             # Custom widget tests (24 tests)
└── integration/
    ├── test_cli_commands.py        # CLI integration tests (42 tests)
    ├── test_report_generation.py   # Report workflow tests (21 tests)
    └── test_telemetry_collection.py # Collection workflow tests (20 tests)
```

## Unit Tests (60% - 204 tests)

### Telemetry Module Tests

#### `test_models.py` - Data Model Validation
- **ExecutionRecord**: Valid data, optional fields, validation, serialization
- **AgentRecord**: Valid data, failed status, running status, validation
- **ResourceRecord**: Valid data, percentage bounds, negative values
- **CollectionResult**: Success, failure, partial success

**Key Scenarios**:
- Invalid status values should raise ValidationError
- Negative agent counts should be rejected
- CPU/Memory percentages must be 0-100
- ISO datetime parsing from JSON

#### `test_config.py` - Configuration Management
- Default values, custom values, path expansion
- Validation: intervals, retention, file sizes
- File I/O: load from YAML, save to YAML
- Error handling: missing files, invalid YAML
- Storage path validation

**Key Scenarios**:
- Config file merges with defaults
- Validates writable storage paths
- Returns expected file paths (executions.jsonl, agents.jsonl, etc.)

#### `test_storage.py` - Data Persistence
- Save/load executions, agents, resources
- Filtering by status, scenario, date range, execution ID
- Append mode, corrupted line handling, empty files
- Date range queries, last sync time tracking
- Data pruning, file compression, vacuum operations
- Export/import JSON

**Key Scenarios**:
- Handles corrupted JSON lines gracefully
- Filters data by multiple criteria
- Prunes old data based on retention policy
- Exports/imports data without loss

#### `test_collector.py` - Telemetry Collection
- Initialization, single collection, API errors, empty data
- Incremental sync with last_sync_time
- Batch/paginated collection
- Background collection: start, stop, interval, lock file
- Concurrent prevention, crash recovery
- Timeout handling, partial success, health checks

**Key Scenarios**:
- Lock file prevents concurrent collection
- Can recover from stale lock files
- Respects collection intervals
- Handles API timeouts gracefully
- Health check before collection

### Reports Module Tests

#### `test_models.py` - Report Data Models
- **ReportFilters**: Valid data, date range validation, status validation
- **ReportMetadata**: Valid data, default values, report type validation
- **KPIData**: Valid data, calculated success rate, percentage bounds
- **ReportData**: Complete report structure
- **ScenarioReport**: Scenario-specific reports, comparison
- **ErrorSummary**: Error tracking and sorting

**Key Scenarios**:
- End date must be after start date
- Success rate auto-calculated from counts
- KPI data includes agent and cost metrics
- Error summaries sortable by count

#### `test_data.py` - KPI Calculation & Processing
- Basic KPI calculation, empty data handling
- Success rate, average duration, agent metrics, cost metrics
- Top regions, top scenarios, error distribution
- Timeline data, status distribution, duration histogram
- Filtering by date, scenario, status, duration
- Percentile calculation, scenario comparison
- Resource utilization, failure analysis
- Time-based aggregation, period comparison
- CSV export format

**Key Scenarios**:
- Handles empty datasets without errors
- Filters apply correctly to calculations
- Percentiles are monotonically increasing
- Aggregations respect time intervals

#### `test_generator.py` - Report Generation
- Initialization, summary/detailed/scenario/error reports
- Report filtering, CSV/JSON export
- Chart generation (Plotly JSON)
- Jinja2 template rendering
- Empty data handling, custom filenames, output directory creation
- Multiple reports, timestamp in filename
- Custom CSS, custom logo
- Comparison reports, agent/resource reports
- Report metadata, responsive design, chart inclusion
- Large dataset handling, output format validation

**Key Scenarios**:
- Creates output directory if not exists
- Generates valid HTML/CSV/JSON
- Charts are JSON serializable
- Handles large datasets efficiently (<10s)
- Templates render with proper context

### UI Module Tests

#### `test_dashboard.py` - Interactive Dashboard
- Initialization, compose method, load/refresh data
- Auto-refresh, keyboard shortcuts, empty data handling
- Screen navigation (summary, executions, agents, errors)
- Filtering by status, scenario, date range
- Filter persistence, clear filters
- Export current view, HTML report export
- Sorting by date, duration, status
- Detail views (execution details)

**Key Scenarios**:
- Dashboard loads data on startup
- Auto-refresh respects interval
- Keyboard shortcuts work (r=refresh, q=quit, f=filter)
- Filters persist across screens
- Tables sortable by multiple columns

#### `test_widgets.py` - Custom Widgets
- **KPIWidget**: Initialization, render, positive/negative trends
- **ExecutionTable**: Initialization, columns, sorting, filtering, empty data
- **ChartWidget**: Line/bar/pie charts, empty data
- **FilterPanel**: Status/date/scenario filters, apply/clear
- **HeaderWidget**: Title, last update time, navigation tabs
- **FooterWidget**: Help text, keyboard shortcuts
- **StatusBadge**: Status colors (completed=green, failed=red)
- **DetailView**: Execution details, metadata, agents, close button

**Key Scenarios**:
- Widgets render without errors
- Tables support sorting and filtering
- Charts handle empty data gracefully
- Filter panel collects user input

## Integration Tests (30% - 83 tests)

### `test_telemetry_collection.py` - Collection Workflows
- Full collection cycle (API → Storage)
- Incremental collection with multiple cycles
- Background collection lifecycle
- API failure handling, data pruning
- Concurrent prevention, crash recovery
- Large dataset handling, storage integrity
- File rotation, collection metrics
- Config file workflow, validation workflow
- Export/import workflow, compression workflow

**Key Scenarios**:
- Complete API-to-storage pipeline works
- Incremental sync uses last_sync_time
- Background collection can start/stop cleanly
- Handles intermittent API failures
- Lock file prevents concurrent instances

### `test_report_generation.py` - Report Workflows
- Full report generation cycle (data → HTML)
- Multi-format generation (HTML, CSV, JSON)
- Filtered report generation
- Reports with charts
- Scenario-specific, error analysis, comparison reports
- Template rendering, custom styling, metadata tracking
- Empty data handling
- KPI calculation pipeline
- Aggregation pipeline, chart data generation
- Filtering pipeline, export pipeline
- End-to-end collection-to-report workflow
- Scheduled collection with periodic reporting
- Multi-report generation, archival workflow

**Key Scenarios**:
- Complete data processing pipeline
- All report types generate successfully
- Filters apply correctly throughout pipeline
- Charts integrate into reports
- Telemetry collection feeds report generation

### `test_cli_commands.py` - CLI Integration
- **Telemetry commands**: start, stop, status, start with interval
- **Report commands**: summary, detailed, scenario, errors
- Date/status filtering, CSV/JSON export
- **Dashboard command**: interactive UI, auto-refresh, no data
- Help text, version, verbose/quiet options, config file
- Error handling: invalid commands, missing arguments, API errors
- Command pipelines: collect then report

**Key Scenarios**:
- All CLI commands have help text
- Commands validate required arguments
- Error messages are user-friendly
- Config file overrides defaults
- Pipeline: start collection → generate report

## Test Coverage Goals

### Unit Test Coverage Targets (>80%)
- **Telemetry**: 104 tests covering collector, storage, models, config
- **Reports**: 80 tests covering data processing, generation, models
- **UI**: 50 tests covering dashboard and widgets

### Integration Test Coverage (moderate)
- **Telemetry Collection**: 20 tests covering full workflows
- **Report Generation**: 21 tests covering end-to-end pipelines
- **CLI Commands**: 42 tests covering user interactions

## Running the Tests

### Prerequisites
```bash
cd /home/azureuser/src/AzureHayMaker/worktrees/feat/issue-116-reporting-telemetry/cli
uv pip install -e ".[dev]"  # Install with dev dependencies
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run by Category
```bash
# Unit tests only
pytest tests/telemetry/ tests/reports/ tests/ui/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific module
pytest tests/telemetry/test_collector.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=haymaker_cli --cov-report=html
```

### Expected Results (Before Implementation)
All tests should **FAIL** with `ModuleNotFoundError` or `ImportError` since the implementation doesn't exist yet. This is expected and correct for TDD!

## Test Fixtures & Utilities

### `fixtures/sample_data.py`
- `sample_execution_data(count, offset_minutes)` - Generate test execution records
- `sample_agent_data(execution_id, count)` - Generate test agent records
- `sample_resource_data(execution_id, count)` - Generate test resource records
- `sample_telemetry_config()` - Sample configuration
- `sample_report_filters()` - Sample filter configuration
- `sample_kpi_data()` - Sample KPI data
- `sample_empty_data()` - Empty data for edge cases
- `sample_large_dataset(executions)` - Large dataset for performance testing

### `telemetry/conftest.py`
- `mock_api_client` - Mock API with sample data
- `mock_api_client_error` - Mock API that raises errors
- `mock_api_client_empty` - Mock API with empty responses
- `telemetry_config` - Sample configuration
- `telemetry_storage_dir` - Temporary storage directory
- `sample_telemetry_files` - Pre-populated test files
- `corrupted_telemetry_file` - File with corrupted JSON
- `large_telemetry_dataset` - Large dataset for performance testing

### `reports/conftest.py`
- `mock_telemetry_storage` - Mock storage with sample data
- `mock_telemetry_storage_empty` - Mock storage with no data
- `report_filters` - Sample report filters
- `report_output_dir` - Temporary output directory
- `mock_jinja2_env` - Mock Jinja2 template environment
- `sample_kpis` - Sample KPI data
- `sample_chart_data` - Sample chart data

## Test Naming Convention

All tests follow the pattern: `test_<component>_<scenario>_<expected_result>`

Examples:
- `test_collector_collect_once_success` - Collector collects data successfully
- `test_storage_load_executions_with_filter` - Storage filters executions
- `test_generator_generate_report_empty_data` - Generator handles empty data

## Edge Cases & Error Conditions Tested

1. **Empty Data**: All components handle zero executions/agents gracefully
2. **Invalid Input**: Pydantic models validate and reject bad data
3. **API Failures**: Collection handles timeouts, connection errors
4. **File I/O Errors**: Storage handles corrupted files, permission errors
5. **Concurrent Access**: Lock files prevent concurrent collection
6. **Large Datasets**: Performance tests with 1000+ records
7. **Missing Files**: Graceful handling of missing config/data files
8. **Invalid Dates**: Date range validation (end > start)
9. **Negative Values**: Reject negative durations, counts, percentages
10. **Resource Exhaustion**: File size limits, retention policies

## Next Steps for Implementation

1. **Start with Models** (`test_models.py` should pass first)
2. **Implement Config** (`test_config.py`)
3. **Build Storage** (`test_storage.py`)
4. **Create Collector** (`test_collector.py`)
5. **Report Data Processing** (`test_data.py`)
6. **Report Models** (`test_models.py` in reports)
7. **Report Generator** (`test_generator.py`)
8. **UI Widgets** (`test_widgets.py`)
9. **Dashboard** (`test_dashboard.py`)
10. **CLI Commands** (`test_cli_commands.py`)
11. **Integration Tests** (should pass when components work together)

## Test Maintenance

- **Add tests** when adding new features
- **Update tests** when changing behavior
- **Remove tests** only when removing features
- **Keep fixtures DRY** - reuse sample data generators
- **Mock external dependencies** - API, filesystem, time
- **Use parametrize** for multiple scenarios
- **Fast tests** - unit tests should run in < 1 second total

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [TDD Best Practices](https://testdriven.io/)
- [Pydantic Testing](https://docs.pydantic.dev/latest/usage/validation_errors/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Textual Testing](https://textual.textualize.io/guide/testing/)

---

**Happy TDD! Let the tests guide the implementation!** 🧪
