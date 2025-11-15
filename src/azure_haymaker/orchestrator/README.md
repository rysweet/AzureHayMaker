# Orchestrator Module

The orchestrator module contains core functionality for Azure HayMaker orchestration, including configuration management, validation, service principal management, and scenario selection.

## Submodules

### scenario_selector

Handles listing, parsing, and randomly selecting scenarios for simulation execution.

#### Functions

##### `list_available_scenarios() -> List[Path]`

Lists all available scenario files from `docs/scenarios/*.md` directory.

Excludes special files:
- `SCENARIO_TEMPLATE.md` - Template file for creating new scenarios
- `SCALING_PLAN.md` - Scaling plan documentation

**Returns:** List of Path objects pointing to scenario markdown files

**Raises:** FileNotFoundError if scenarios directory doesn't exist

**Example:**
```python
from azure_haymaker.orchestrator.scenario_selector import list_available_scenarios

scenarios = list_available_scenarios()
print(f"Found {len(scenarios)} available scenarios")
for scenario in scenarios[:5]:
    print(f"  - {scenario.name}")
```

##### `parse_scenario_metadata(file_path: Path) -> ScenarioMetadata`

Parses scenario metadata from a markdown file.

Extracts:
- **scenario_name**: Derived from filename (without .md extension)
- **technology_area**: Extracted from "## Technology Area" markdown section
- **scenario_doc_path**: Full path to the scenario file
- **agent_path**: Constructed from scenario name

**Args:**
- `file_path`: Path to scenario markdown file

**Returns:** ScenarioMetadata object with extracted information

**Raises:**
- FileNotFoundError if file doesn't exist
- ValueError if required metadata cannot be extracted

**Example:**
```python
from pathlib import Path
from azure_haymaker.orchestrator.scenario_selector import parse_scenario_metadata

path = Path("docs/scenarios/ai-ml-01-cognitive-services-vision.md")
metadata = parse_scenario_metadata(path)
print(f"Scenario: {metadata.scenario_name}")
print(f"Area: {metadata.technology_area}")
print(f"Agent: {metadata.agent_path}")
```

##### `select_scenarios(size: SimulationSize) -> List[ScenarioMetadata]`

Randomly selects scenarios for execution based on simulation size.

**Selection Counts:**
- `SimulationSize.SMALL`: 5 scenarios
- `SimulationSize.MEDIUM`: 15 scenarios
- `SimulationSize.LARGE`: 30 scenarios

Ensures:
- No duplicate selections
- Template and scaling plan files are never selected
- All selected scenarios have valid metadata

**Args:**
- `size`: SimulationSize enum value (SMALL, MEDIUM, LARGE)

**Returns:** List of randomly selected ScenarioMetadata objects

**Raises:** ValueError if not enough scenarios are available for requested size

**Example:**
```python
from azure_haymaker.models import SimulationSize
from azure_haymaker.orchestrator.scenario_selector import select_scenarios

# Select scenarios for a medium-size simulation
scenarios = select_scenarios(SimulationSize.MEDIUM)
print(f"Selected {len(scenarios)} scenarios:")

for scenario in scenarios:
    print(f"  - {scenario.scenario_name}")
    print(f"    Area: {scenario.technology_area}")
    print(f"    Agent: {scenario.agent_path}")
```

## Data Models

### ScenarioMetadata

From `azure_haymaker.models.scenario`:

```python
class ScenarioMetadata(BaseModel):
    scenario_name: str  # Unique scenario identifier
    scenario_doc_path: str  # Path to scenario document
    agent_path: str  # Path to goal-seeking agent code
    technology_area: str  # Azure technology area (e.g., AI/ML, Networking)
    status: ScenarioStatus = PENDING  # Current execution status
    ...
```

### SimulationSize

From `azure_haymaker.models.config`:

```python
class SimulationSize(str, Enum):
    SMALL = "small"      # 5 scenarios
    MEDIUM = "medium"    # 15 scenarios
    LARGE = "large"      # 30 scenarios
```

## Workflow

### Basic Scenario Selection Workflow

```python
from azure_haymaker.models import SimulationSize
from azure_haymaker.orchestrator.scenario_selector import (
    list_available_scenarios,
    select_scenarios,
)

# List all available scenarios (excluding templates)
all_scenarios = list_available_scenarios()
print(f"Total available scenarios: {len(all_scenarios)}")

# Select scenarios for execution
selected = select_scenarios(SimulationSize.LARGE)
print(f"Selected {len(selected)} scenarios for LARGE simulation")

# Process selected scenarios
for scenario in selected:
    print(f"Executing: {scenario.scenario_name}")
    print(f"  Technology Area: {scenario.technology_area}")
    print(f"  Document: {scenario.scenario_doc_path}")
    print(f"  Agent: {scenario.agent_path}")
```

## Scenario File Format

Scenario files are markdown files located in `docs/scenarios/` with the following structure:

```markdown
# Scenario: [Descriptive Title]

## Technology Area
[Technology category, e.g., AI & ML, Networking, Compute, etc.]

## Company Profile
- **Company Size**: [Size]
- **Industry**: [Industry]
- **Use Case**: [Use case description]

## Scenario Description
[Detailed description of scenario]

## Azure Services Used
- [Service 1]
- [Service 2]
...

## Prerequisites
[Prerequisites list]

---

## Phase 1: Deployment and Validation

### Environment Setup
[Setup instructions]

### Deployment Steps
[Step-by-step deployment]
...
```

## Special Files

### SCENARIO_TEMPLATE.md
Template file for creating new scenarios. Never selected for execution.

### SCALING_PLAN.md
Scaling plan documentation. Never selected for execution.

## Testing

Unit tests verify:

- Scenario listing correctly excludes template and scaling plan files
- Metadata parsing extracts required fields from valid scenario files
- Random selection respects size constraints
- No duplicate scenarios are selected
- Only valid scenarios are available
- Integration workflows function correctly

Run tests:
```bash
uv run pytest tests/unit/test_scenario_selector.py -v
```

## Error Handling

### Missing Scenarios Directory
```python
FileNotFoundError: Scenarios directory not found: [path]
```
Solution: Ensure `docs/scenarios/` directory exists with markdown files.

### Invalid Scenario File
```python
FileNotFoundError: Scenario file not found: [path]
```
Solution: Verify file path exists and is readable.

### Insufficient Scenarios
```python
ValueError: Not enough scenarios available. Requested: 30, Available: 25
```
Solution: Add more scenario files or select smaller simulation size.

## Module Structure

```
src/azure_haymaker/orchestrator/
├── __init__.py
├── scenario_selector.py       # This module
├── config.py                   # Configuration models
├── validation.py               # Validation utilities
├── sp_manager.py               # Service principal management
└── README.md                   # This file
```

## Dependencies

- `azure_haymaker.models` - ScenarioMetadata, SimulationSize models
- Standard library: pathlib, random, re

## Key Design Decisions

1. **File-based scenario discovery**: Scenarios are discovered from markdown files in `docs/scenarios/` to keep the system flexible and maintainable

2. **Random selection with exclusions**: Uses `random.sample()` for unbiased random selection while automatically excluding template files

3. **Metadata extraction from markdown**: Technology area and other metadata are extracted from the markdown file itself, enabling documentation to be the source of truth

4. **Agent path construction**: Agent paths follow a consistent naming convention derived from scenario filename (kebab-case to snake_case)

5. **TDD approach**: All functionality is thoroughly tested before implementation to ensure correctness

## Future Enhancements

- Add scenario difficulty/complexity scoring
- Implement scenario selection based on technology area diversity
- Add scenario dependency tracking (some scenarios require specific prerequisites)
- Implement scenario caching with invalidation
- Add scenario categorization and filtering by tags
