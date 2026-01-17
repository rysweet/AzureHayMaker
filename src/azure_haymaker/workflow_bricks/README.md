# Workflow Bricks - Software Engineering Team Simulation

Self-contained, composable components for simulating realistic software engineering team activities.

## Overview

Workflow Bricks implements **Proposal D: Compositional Workflow Engine** from Issue #145, providing atomic "brick" components that compose into larger workflows for simulating software development team telemetry.

Each brick is:
- **Self-contained**: All logic, models, and tests in one place
- **Single responsibility**: ONE clear action per brick
- **Composable**: Bricks connect via standard interfaces (studs)
- **Regeneratable**: Can be rebuilt from this specification

## Architecture

```
workflow_bricks/
    __init__.py          # Public API via __all__
    README.md            # This specification
    base.py              # BrickBase, BrickContext, BrickResult
    models.py            # Shared Pydantic models
    clients/
        __init__.py
        github_client.py # GitHub API operations
    bricks/
        __init__.py
        commit.py        # CommitBrick
        pull_request.py  # PullRequestBrick
        code_review.py   # CodeReviewBrick
        ci_pipeline.py   # CIPipelineBrick
        merge.py         # MergeBrick
    composers/
        __init__.py
        workflow.py      # Workflow composition engine
```

## Public API (The "Studs")

```python
from azure_haymaker.workflow_bricks import (
    # Base classes
    BrickBase,
    BrickContext,
    BrickResult,
    BrickStatus,

    # Core bricks
    CommitBrick,
    PullRequestBrick,
    CodeReviewBrick,
    CIPipelineBrick,
    MergeBrick,

    # Client
    GitHubClient,

    # Composer
    Workflow,
)
```

## Core Concepts

### BrickContext

Context passed to each brick during execution:

```python
@dataclass
class BrickContext:
    """Execution context for a brick.

    Attributes:
        tenant_id: Azure tenant for telemetry isolation
        team_id: Engineering team identifier
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        branch_name: Target branch for operations
        actor: Person/identity performing the action
        github_token: GitHub authentication token
        dry_run: If True, simulate without actual API calls
        metadata: Additional context passed between bricks
    """
```

### BrickResult

Standard result from brick execution:

```python
@dataclass
class BrickResult:
    """Result from brick execution.

    Attributes:
        status: BrickStatus (SUCCESS, FAILED, SKIPPED)
        brick_name: Name of the brick that executed
        started_at: Execution start time
        ended_at: Execution end time
        outputs: Dictionary of outputs (IDs, URLs, etc.)
        error: Error message if failed
        telemetry: Generated telemetry events
    """
```

### BrickBase

Abstract base class for all bricks:

```python
class BrickBase(ABC):
    """Base class for workflow bricks.

    Lifecycle:
        1. validate(context) - Check preconditions
        2. execute(context) - Perform the action
        3. cleanup(context, result) - Post-execution cleanup
    """

    @abstractmethod
    async def validate(self, context: BrickContext) -> bool:
        """Validate preconditions for execution."""

    @abstractmethod
    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute the brick's action."""

    async def cleanup(self, context: BrickContext, result: BrickResult) -> None:
        """Optional cleanup after execution."""
```

## Core Bricks

### CommitBrick

Simulates a git commit to a repository.

```python
brick = CommitBrick(
    message="feat: Add user authentication",
    files=["src/auth.py", "tests/test_auth.py"],
    author_name="Alice Developer",
    author_email="alice@example.com",
)
result = await brick.execute(context)
# result.outputs["commit_sha"] -> "abc123..."
```

**Telemetry Generated:**
- Commit event in GitHub
- Author activity metrics

### PullRequestBrick

Creates a pull request.

```python
brick = PullRequestBrick(
    title="feat: Add user authentication",
    body="Implements user login and registration",
    base_branch="main",
    head_branch="feat/auth",
    labels=["enhancement", "feature"],
    reviewers=["bob", "carol"],
)
result = await brick.execute(context)
# result.outputs["pr_number"] -> 42
# result.outputs["pr_url"] -> "https://github.com/..."
```

**Telemetry Generated:**
- Pull request created event
- Reviewer assignment events

### CodeReviewBrick

Simulates a code review with comments and approval.

```python
brick = CodeReviewBrick(
    pr_number=42,
    reviewer="bob",
    action="approve",  # "approve", "request_changes", "comment"
    comments=[
        {"path": "src/auth.py", "line": 15, "body": "Consider using bcrypt"},
    ],
    body="LGTM! Minor suggestion for password hashing.",
)
result = await brick.execute(context)
# result.outputs["review_id"] -> 123
```

**Telemetry Generated:**
- Review submitted event
- Comment events
- Status check updates

### CIPipelineBrick

Triggers or simulates a CI pipeline run.

```python
brick = CIPipelineBrick(
    workflow_name="ci.yml",
    trigger_ref="refs/heads/feat/auth",
    inputs={"run_integration_tests": "true"},
    expected_status="success",  # For simulation
    duration_seconds=120,
)
result = await brick.execute(context)
# result.outputs["run_id"] -> 456
# result.outputs["status"] -> "success"
```

**Telemetry Generated:**
- Workflow run started event
- Job status events
- Workflow completed event

### MergeBrick

Merges a pull request.

```python
brick = MergeBrick(
    pr_number=42,
    merge_method="squash",  # "merge", "squash", "rebase"
    delete_branch=True,
)
result = await brick.execute(context)
# result.outputs["merge_sha"] -> "def456..."
```

**Telemetry Generated:**
- PR merged event
- Branch deleted event (if delete_branch=True)

## Workflow Composition

Compose bricks into workflows:

```python
from azure_haymaker.workflow_bricks import Workflow

# Define a feature workflow
feature_workflow = Workflow(
    name="feature-development",
    steps=[
        CommitBrick(message="feat: Initial implementation", files=["src/feature.py"]),
        PullRequestBrick(title="feat: New feature", base_branch="main"),
        CodeReviewBrick(pr_number="${pr_number}", reviewer="reviewer1", action="comment"),
        CommitBrick(message="fix: Address review feedback", files=["src/feature.py"]),
        CodeReviewBrick(pr_number="${pr_number}", reviewer="reviewer1", action="approve"),
        CIPipelineBrick(workflow_name="ci.yml"),
        MergeBrick(pr_number="${pr_number}", merge_method="squash"),
    ],
)

# Execute the workflow
results = await feature_workflow.execute(context)
```

## Telemetry Integration

All bricks automatically generate telemetry via OpenTelemetry:

```python
from azure_haymaker.telemetry import create_tenant_span

async def execute(self, context: BrickContext) -> BrickResult:
    with create_tenant_span(context.tenant_id, f"brick.{self.name}") as span:
        span.set_attribute("team_id", context.team_id)
        span.set_attribute("repo", f"{context.repo_owner}/{context.repo_name}")
        # ... brick execution ...
```

## Configuration

Configure via environment variables or context:

```bash
# GitHub authentication
GITHUB_TOKEN=ghp_...

# Telemetry
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# Dry run mode (no actual API calls)
WORKFLOW_BRICKS_DRY_RUN=true
```

## Error Handling

Bricks use explicit error handling:

```python
try:
    result = await brick.execute(context)
except BrickValidationError as e:
    # Precondition failed
except BrickExecutionError as e:
    # Execution failed
except BrickTimeoutError as e:
    # Operation timed out
```

## Testing

Each brick includes comprehensive tests:

```bash
# Run all brick tests
uv run pytest tests/unit/test_workflow_bricks.py -v

# Run specific brick tests
uv run pytest tests/unit/test_workflow_bricks.py::TestCommitBrick -v
```

## Philosophy Alignment

- **Ruthless Simplicity**: Each brick does ONE thing
- **Bricks & Studs**: Self-contained modules with clear interfaces
- **Zero-BS**: Working code only, no stubs or placeholders
- **Regeneratable**: This README is the specification

## Future Enhancements (Not in Phase 1-2)

- Azure DevOps API client
- FSM orchestration (Proposal B elements)
- LLM-generated variety (Proposal C elements)
- Sprint simulation patterns
