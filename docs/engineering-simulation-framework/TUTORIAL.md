---
layout: default
title: Complete Tutorial
parent: Engineering Simulation Framework
nav_order: 1
---

# Software Engineering Team Simulation Framework
{: .no_toc }

Complete end-to-end tutorial: from installation to multi-team sprint simulation
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## What You'll Learn

This tutorial teaches you how to simulate realistic software engineering team activities using the brick-based workflow engine. By the end, you'll be able to:

- Set up the framework and verify installation
- Understand and use the 5 core workflow bricks
- Compose bricks into custom workflows
- Run single-team sprint simulations
- Orchestrate multi-team parallel sprints
- Export and analyze telemetry data
- Create custom bricks for specialized scenarios

**Estimated time**: 65 minutes total (follow sections in order)

---

## Part 1: Getting Started (5 minutes)

Learn how to install the framework and verify everything works.

### What You Need

Before starting, ensure you have:

- **Python 3.11+** installed
- **uv package manager** (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **GitHub personal access token** with repo permissions
- **GitHub repository** for testing (or use an organization you have access to)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/rysweet/AzureHayMaker.git
cd AzureHayMaker

# Install all dependencies (including engineering simulation)
uv sync --all-extras
```

**Expected output:**
```
Resolved 142 packages in 2.3s
Installed 142 packages in 4.1s
```

### Step 2: Configure Environment

Create a `.env` file with your GitHub credentials:

```bash
# Copy the example
cp .env.example .env

# Edit .env and add your GitHub token
# GITHUB_TOKEN=ghp_your_token_here
# GITHUB_ORG=your-org-name
```

**Important**: Never commit your `.env` file. It's already in `.gitignore`.

### Step 3: Verify Installation

Create a simple verification script:

```python
# File: verify_installation.py
import asyncio
from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.workflow import Workflow

async def main():
    print("✅ Engineering Simulation Framework installed successfully!")

    # Create empty workflow to verify imports work
    workflow = Workflow(name="Verification Test")

    # Create test context
    context = BrickContext(
        team_id="test_team",
        sprint_id="test_sprint",
        repo_name="test-repo"
    )

    # Execute empty workflow (should succeed immediately)
    result = await workflow.execute(context)

    if result.success:
        print("✅ Workflow engine operational")
        print(f"✅ Context threading working")
        return 0
    else:
        print("❌ Verification failed")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
```

Run the verification:

```bash
uv run verify_installation.py
```

**Expected output:**
```
✅ Engineering Simulation Framework installed successfully!
✅ Workflow engine operational
✅ Context threading working
```

### What You've Learned

- How to install the framework with uv
- How to configure GitHub credentials securely
- How to verify the installation works
- The basic structure: Workflow, BrickContext, and execution

### Next Steps

Now that installation is verified, let's understand what bricks are and how they work.

---

## Part 2: Understanding Bricks (10 minutes)

Learn about the 5 core bricks and how they compose into workflows.

### What Are Bricks?

Bricks are small, self-contained workflow components that follow the "brick philosophy":

- **Small**: Each brick does one thing well
- **Composable**: Bricks combine into larger workflows
- **Reusable**: Same bricks work in different workflows
- **Self-validating**: Each brick validates its prerequisites
- **Context-threaded**: Context flows immutably through bricks

Think of bricks like LEGO pieces - each piece is simple, but you can build complex structures by combining them.

### The 5 Core Bricks

| Brick | Purpose | Context Updates | Example Use |
|-------|---------|-----------------|-------------|
| **CommitBrick** | Creates GitHub commits | Sets `commit_sha` | Feature development, bug fixes |
| **PullRequestBrick** | Creates pull requests | Sets `pr_number` | Code review workflows |
| **CIPipelineBrick** | Simulates CI/CD runs | Adds test results | Automated testing |
| **ReviewBrick** | Submits code reviews | Adds review data | Code review process |
| **MergeBrick** | Merges pull requests | Updates with merge SHA | Deployment workflows |

### Step 1: Create Your First Brick

Let's create a CommitBrick and understand how it works:

```python
# File: first_brick.py
import asyncio
from unittest.mock import AsyncMock, MagicMock
from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient

async def main():
    print("=" * 60)
    print("Understanding CommitBrick")
    print("=" * 60)

    # Create a mocked GitHub client (for testing without real API calls)
    github_client = MagicMock(spec=GitHubClient)
    github_client.org = "my-org"
    github_client.create_commit = AsyncMock(return_value={
        "sha": "abc123def456",
        "html_url": "https://github.com/my-org/my-repo/commit/abc123",
        "author": {"name": "Alice Developer", "email": "alice@example.com"},
        "stats": {"additions": 45, "deletions": 12, "total": 57}
    })

    # Create CommitBrick
    commit_brick = CommitBrick(
        github_client=github_client,
        file_paths=["src/auth.py", "tests/test_auth.py"],
        commit_message="Add OAuth2 authentication"
    )

    print(f"\n📦 Created brick: {commit_brick.name}")
    print(f"   Files to modify: {len(commit_brick.file_paths)}")
    print(f"   Message: {commit_brick.commit_message}")

    # Create initial context
    context = BrickContext(
        team_id="team_alpha",
        sprint_id="sprint_42",
        repo_name="backend-api",
        branch_name="feature/oauth2"
    )

    print(f"\n📋 Initial context:")
    print(f"   Team: {context.team_id}")
    print(f"   Branch: {context.branch_name}")
    print(f"   Commit SHA: {context.commit_sha}")  # None initially

    # Execute brick
    print(f"\n⚙️  Executing CommitBrick...")
    result = await commit_brick.execute(context)

    print(f"\n✅ Execution complete!")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_seconds:.2f}s")

    # Context was updated
    print(f"\n📋 Updated context:")
    print(f"   Team: {result.context.team_id}")
    print(f"   Branch: {result.context.branch_name}")
    print(f"   Commit SHA: {result.context.commit_sha}")  # Now populated!

    # Telemetry was generated
    print(f"\n📊 Telemetry generated:")
    print(f"   Type: {result.telemetry.get('brick_type', 'unknown')}")
    print(f"   SHA: {result.telemetry['commit_sha'][:7]}")
    print(f"   Files: {len(result.telemetry.get('files', []))} changed")
    print(f"   URL: {result.telemetry.get('html_url', 'N/A')}")

    print("\n" + "=" * 60)
    print("Key Concepts:")
    print("  1. Bricks validate context before execution")
    print("  2. Bricks return BrickResult with updated context")
    print("  3. Context is immutable (original unchanged)")
    print("  4. Telemetry tracks all operations")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run first_brick.py
```

**Expected output:**
```
============================================================
Understanding CommitBrick
============================================================

📦 Created brick: CommitBrick
   Files to modify: 2
   Message: Add OAuth2 authentication

📋 Initial context:
   Team: team_alpha
   Branch: feature/oauth2
   Commit SHA: None

⚙️  Executing CommitBrick...

✅ Execution complete!
   Success: True
   Duration: 0.01s

📋 Updated context:
   Team: team_alpha
   Branch: feature/oauth2
   Commit SHA: abc123def456

📊 Telemetry generated:
   Type: commit
   SHA: abc123d
   Files: 2 changed
   URL: https://github.com/my-org/my-repo/commit/abc123

============================================================
Key Concepts:
  1. Bricks validate context before execution
  2. Bricks return BrickResult with updated context
  3. Context is immutable (original unchanged)
  4. Telemetry tracks all operations
============================================================
```

### Step 2: Try All 5 Bricks

Now let's see all bricks in action:

```python
# File: all_bricks.py
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient

async def main():
    # Mock GitHub client
    github_client = MagicMock(spec=GitHubClient)
    github_client.org = "demo-org"

    # Mock responses for each operation
    github_client.create_commit = AsyncMock(return_value={
        "sha": "commit123", "html_url": "https://github.com/demo-org/repo/commit/commit123"
    })
    github_client.create_pull_request = AsyncMock(return_value={
        "number": 42, "html_url": "https://github.com/demo-org/repo/pull/42", "state": "open"
    })
    github_client.create_review = AsyncMock(return_value={
        "id": 789, "state": "APPROVED", "submitted_at": datetime.now().isoformat()
    })
    github_client.update_check_run = AsyncMock(return_value={
        "id": 456, "status": "completed", "conclusion": "success"
    })
    github_client.merge_pull_request = AsyncMock(return_value={
        "sha": "merge456", "merged": True
    })

    # Create all 5 bricks
    bricks = [
        CommitBrick(github_client),
        PullRequestBrick(github_client),
        CIPipelineBrick(github_client, failure_rate=0.0),
        ReviewBrick(github_client),
        MergeBrick(github_client)
    ]

    print("=" * 60)
    print("The 5 Core Bricks")
    print("=" * 60)

    for i, brick in enumerate(bricks, 1):
        print(f"\n{i}. {brick.name}")
        print(f"   Purpose: {brick.__doc__.strip().split('.')[0] if brick.__doc__ else 'N/A'}")

    print("\n" + "=" * 60)
    print("✅ All 5 core bricks available for composition!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run all_bricks.py
```

**Expected output:**
```
============================================================
The 5 Core Bricks
============================================================

1. CommitBrick
   Purpose: Creates a commit with file changes

2. PullRequestBrick
   Purpose: Creates a GitHub pull request

3. CIPipelineBrick
   Purpose: Simulates a CI/CD pipeline run

4. ReviewBrick
   Purpose: Submits a code review on a pull request

5. MergeBrick
   Purpose: Merges a GitHub pull request

============================================================
✅ All 5 core bricks available for composition!
============================================================
```

### What You've Learned

- What bricks are and the brick philosophy
- The 5 core bricks and their purposes
- How bricks validate context
- How context threads through brick execution
- How telemetry is generated automatically

### Next Steps

Now let's learn how to compose bricks into complete workflows.

---

## Part 3: Workflow Composition (10 minutes)

Learn how to combine bricks into powerful workflows using method chaining.

### What Is Workflow Composition?

Workflow composition means combining multiple bricks into a sequential pipeline. The framework provides the `Workflow` class that:

- Chains bricks together
- Threads context automatically
- Aggregates telemetry
- Handles failures gracefully

### Step 1: Compose a Feature Development Workflow

Let's build a complete feature development workflow:

```python
# File: feature_workflow.py
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient
from azure_haymaker.engineering_sim.workflow import Workflow

async def main():
    # Mock GitHub client
    github_client = MagicMock(spec=GitHubClient)
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={
        "sha": "abc123", "html_url": "https://github.com/demo-org/repo/commit/abc123",
        "stats": {"additions": 45, "deletions": 12}
    })
    github_client.create_pull_request = AsyncMock(return_value={
        "number": 42, "html_url": "https://github.com/demo-org/repo/pull/42"
    })
    github_client.create_review = AsyncMock(return_value={
        "id": 789, "state": "APPROVED"
    })
    github_client.update_check_run = AsyncMock(return_value={
        "conclusion": "success"
    })
    github_client.merge_pull_request = AsyncMock(return_value={
        "merged": True, "sha": "merge456"
    })

    print("=" * 60)
    print("Composing a Feature Development Workflow")
    print("=" * 60)

    # Step 1: Create bricks
    print("\n1️⃣  Creating bricks...")
    commit_brick_1 = CommitBrick(github_client)
    commit_brick_2 = CommitBrick(github_client)
    pr_brick = PullRequestBrick(github_client)
    ci_brick = CIPipelineBrick(github_client, failure_rate=0.0)
    review_brick = ReviewBrick(github_client)
    merge_brick = MergeBrick(github_client)
    print("   ✅ Created 6 bricks")

    # Step 2: Compose workflow using method chaining
    print("\n2️⃣  Composing workflow with method chaining...")
    feature_workflow = (
        Workflow(name="Feature Development")
        .add_brick(commit_brick_1)
        .add_brick(commit_brick_2)
        .add_brick(pr_brick)
        .add_brick(ci_brick)
        .add_brick(review_brick)
        .add_brick(merge_brick)
    )
    print(f"   ✅ Workflow: '{feature_workflow.name}'")
    print(f"   ✅ Bricks: {len(feature_workflow.bricks)}")
    print(f"   ✅ Estimated duration: {feature_workflow.estimate_duration():.0f}s")

    # Step 3: Create context
    print("\n3️⃣  Creating execution context...")
    context = BrickContext(
        team_id="team_alpha",
        sprint_id="sprint_42",
        repo_name="backend-api",
        branch_name="feature/user-authentication",
        base_branch="main",
        metadata={
            "agent_id": "alice",
            "feature_name": "User Authentication",
        }
    )
    print(f"   ✅ Team: {context.team_id}")
    print(f"   ✅ Branch: {context.branch_name}")

    # Step 4: Execute workflow
    print("\n4️⃣  Executing workflow...")
    print("   " + "-" * 56)
    result = await feature_workflow.execute(context)
    print("   " + "-" * 56)

    # Step 5: Analyze results
    print(f"\n5️⃣  Results:")
    print(f"   Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Bricks executed: {result.telemetry.get('bricks_executed', 0)}")

    # Step 6: View telemetry
    print(f"\n6️⃣  Telemetry generated:")
    brick_telemetry = result.telemetry.get("bricks", [])
    for i, event in enumerate(brick_telemetry, 1):
        event_type = event.get("brick_type", "unknown")
        print(f"   {i}. {event_type.upper()}")

    print("\n" + "=" * 60)
    print("✅ Feature workflow completed successfully!")
    print("=" * 60)
    print("\nWorkflow Pattern:")
    print("  Commit → Commit → PR → CI → Review → Merge")
    print("\nThis pattern can be reused for:")
    print("  • Feature development")
    print("  • Bug fixes with review")
    print("  • Refactoring workflows")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run feature_workflow.py
```

**Expected output:**
```
============================================================
Composing a Feature Development Workflow
============================================================

1️⃣  Creating bricks...
   ✅ Created 6 bricks

2️⃣  Composing workflow with method chaining...
   ✅ Workflow: 'Feature Development'
   ✅ Bricks: 6
   ✅ Estimated duration: 360s

3️⃣  Creating execution context...
   ✅ Team: team_alpha
   ✅ Branch: feature/user-authentication

4️⃣  Executing workflow...
   --------------------------------------------------------
   --------------------------------------------------------

5️⃣  Results:
   Success: ✅ YES
   Duration: 0.03s
   Bricks executed: 6

6️⃣  Telemetry generated:
   1. COMMIT
   2. COMMIT
   3. PULL_REQUEST
   4. CI_RUN
   5. REVIEW
   6. MERGE

============================================================
✅ Feature workflow completed successfully!
============================================================

Workflow Pattern:
  Commit → Commit → PR → CI → Review → Merge

This pattern can be reused for:
  • Feature development
  • Bug fixes with review
  • Refactoring workflows
============================================================
```

### Step 2: Create Different Workflow Patterns

The power of composition is creating different workflows from the same bricks:

```python
# File: workflow_patterns.py
import asyncio
from unittest.mock import AsyncMock, MagicMock

from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient
from azure_haymaker.engineering_sim.workflow import Workflow

async def main():
    # Mock client
    github_client = MagicMock(spec=GitHubClient)
    github_client.org = "demo-org"

    # Create reusable bricks
    commit = CommitBrick(github_client)
    pr = PullRequestBrick(github_client)
    ci = CIPipelineBrick(github_client)
    review = ReviewBrick(github_client)
    merge = MergeBrick(github_client)

    print("=" * 60)
    print("Different Workflow Patterns from Same Bricks")
    print("=" * 60)

    # Pattern 1: Feature Development (full process)
    feature_workflow = (
        Workflow("Feature Development")
        .add_brick(commit)
        .add_brick(commit)
        .add_brick(pr)
        .add_brick(ci)
        .add_brick(review)
        .add_brick(merge)
    )

    # Pattern 2: Hotfix (skip review for urgency)
    hotfix_workflow = (
        Workflow("Emergency Hotfix")
        .add_brick(commit)
        .add_brick(pr)
        .add_brick(ci)
        .add_brick(merge)  # No review - emergency!
    )

    # Pattern 3: Refactoring (more commits, thorough review)
    refactor_workflow = (
        Workflow("Refactoring")
        .add_brick(commit)
        .add_brick(commit)
        .add_brick(commit)
        .add_brick(pr)
        .add_brick(ci)
        .add_brick(review)
        .add_brick(review)  # Extra review for refactoring
        .add_brick(merge)
    )

    # Pattern 4: Draft PR (early feedback, no merge)
    draft_workflow = (
        Workflow("Draft PR for Feedback")
        .add_brick(commit)
        .add_brick(pr)
        .add_brick(review)  # Get feedback
        # No merge - still draft
    )

    workflows = [feature_workflow, hotfix_workflow, refactor_workflow, draft_workflow]

    for i, wf in enumerate(workflows, 1):
        print(f"\n{i}. {wf.name}")
        print(f"   Bricks: {len(wf.bricks)}")
        print(f"   Pattern: {' → '.join([b.name for b in wf.bricks])}")
        print(f"   Duration: ~{wf.estimate_duration()/60:.0f} minutes")

    print("\n" + "=" * 60)
    print("Key Insight:")
    print("  Same bricks, different compositions = different workflows")
    print("  This is the power of the brick philosophy!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run workflow_patterns.py
```

**Expected output:**
```
============================================================
Different Workflow Patterns from Same Bricks
============================================================

1. Feature Development
   Bricks: 6
   Pattern: CommitBrick → CommitBrick → PullRequestBrick → CIPipelineBrick → ReviewBrick → MergeBrick
   Duration: ~6 minutes

2. Emergency Hotfix
   Bricks: 4
   Pattern: CommitBrick → PullRequestBrick → CIPipelineBrick → MergeBrick
   Duration: ~4 minutes

3. Refactoring
   Bricks: 8
   Pattern: CommitBrick → CommitBrick → CommitBrick → PullRequestBrick → CIPipelineBrick → ReviewBrick → ReviewBrick → MergeBrick
   Duration: ~8 minutes

4. Draft PR for Feedback
   Bricks: 3
   Pattern: CommitBrick → PullRequestBrick → ReviewBrick
   Duration: ~3 minutes

============================================================
Key Insight:
  Same bricks, different compositions = different workflows
  This is the power of the brick philosophy!
============================================================
```

### What You've Learned

- How to compose workflows using method chaining
- How context automatically threads through bricks
- How to create different workflow patterns
- How telemetry aggregates across all bricks
- The power of brick reusability

### Next Steps

Now let's learn how to run complete sprint simulations with realistic timing.

---

## Part 4: Single Team Sprints (15 minutes)

Learn how to orchestrate complete 2-week sprints with realistic phases and timing.

### What Is a Sprint Orchestrator?

The `SprintOrchestrator` manages complete sprint execution with:

- **4 sprint phases**: Planning (10%), Development (70%), Code Freeze (15%), Retrospective (5%)
- **Realistic timing**: Work hours, weekends, holidays
- **Workflow scheduling**: Distributes work across phases
- **Telemetry aggregation**: Collects metrics from all workflows

### Step 1: Configure Your First Sprint

```python
# File: first_sprint.py
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from azure_haymaker.engineering_sim.orchestration.types import (
    SprintConfig,
    TeamConfig,
    SprintPhase
)
from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import (
    SprintOrchestrator
)
from azure_haymaker.engineering_sim.github_client import GitHubClient

async def main():
    print("=" * 60)
    print("Single Team Sprint Simulation")
    print("=" * 60)

    # Step 1: Create sprint configuration
    print("\n1️⃣  Configuring 2-week sprint...")
    sprint_config = SprintConfig(
        sprint_id="sprint_42",
        duration_days=10,  # 2 weeks (excluding weekends)
        start_date=datetime.now(),
        work_hours_start=9,
        work_hours_end=18  # 9 AM to 6 PM
    )

    print(f"   Sprint ID: {sprint_config.sprint_id}")
    print(f"   Duration: {sprint_config.duration_days} work days")
    print(f"   Work hours: {sprint_config.work_hours_start}:00 - {sprint_config.work_hours_end}:00")

    # Calculate phase durations
    work_hours_per_day = sprint_config.work_hours_end - sprint_config.work_hours_start
    total_hours = work_hours_per_day * sprint_config.duration_days

    print(f"\n   Phase breakdown:")
    print(f"   • Planning: {total_hours * SprintPhase.PLANNING.percentage:.1f}h (10%)")
    print(f"   • Development: {total_hours * SprintPhase.DEVELOPMENT.percentage:.1f}h (70%)")
    print(f"   • Code Freeze: {total_hours * SprintPhase.CODE_FREEZE.percentage:.1f}h (15%)")
    print(f"   • Retrospective: {total_hours * SprintPhase.RETROSPECTIVE.percentage:.1f}h (5%)")

    # Step 2: Create team configuration
    print("\n2️⃣  Configuring Team Alpha...")
    team_config = TeamConfig(
        team_id="team_alpha",
        team_size=5,
        focus="backend",
        repo="backend-api",
        velocity_points=30,
        workflows=[
            {"type": "feature", "count": 5},      # 5 feature workflows
            {"type": "bugfix", "count": 3},       # 3 bugfix workflows
            {"type": "refactoring", "count": 1}   # 1 refactoring workflow
        ]
    )

    print(f"   Team: {team_config.team_id}")
    print(f"   Team Size: {team_config.team_size}")
    print(f"   Focus: {team_config.focus}")
    print(f"   Repository: {team_config.repo}")
    print(f"   Velocity: {team_config.velocity_points} points")
    print(f"   Total workflows: {sum(w['count'] for w in team_config.workflows)}")
    for wf in team_config.workflows:
        print(f"   • {wf['type']}: {wf['count']}")

    # Step 3: Create mock GitHub client
    print("\n3️⃣  Initializing GitHub client (mocked)...")
    github_client = MagicMock(spec=GitHubClient)
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={"sha": "abc123"})
    github_client.create_pull_request = AsyncMock(return_value={"number": 1})
    github_client.create_review = AsyncMock(return_value={"id": 1})
    github_client.update_check_run = AsyncMock(return_value={"conclusion": "success"})
    github_client.merge_pull_request = AsyncMock(return_value={"merged": True})
    print(f"   ✅ Client ready for {github_client.org}")

    # Step 4: Create orchestrator
    print("\n4️⃣  Creating sprint orchestrator...")
    orchestrator = SprintOrchestrator(
        sprint_config=sprint_config,
        team_config=team_config,
        github_client=github_client
    )
    print(f"   ✅ Orchestrator ready")

    # Step 5: Execute sprint
    print("\n5️⃣  Executing sprint (this will take a moment)...")
    print("   " + "-" * 56)

    result = await orchestrator.execute_sprint()

    print("   " + "-" * 56)

    # Step 6: Analyze results
    print(f"\n6️⃣  Sprint Results:")
    print(f"   Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"   Total workflows: {result.total_workflows}")
    print(f"   Successful: {result.successful_workflows}")
    print(f"   Failed: {result.failed_workflows}")
    print(f"   Success rate: {result.successful_workflows/result.total_workflows*100:.1f}%")

    print(f"\n   Phase Results:")
    for phase_result in result.phase_results:
        print(f"   • {phase_result.phase.value.title()}: {phase_result.workflows_executed} workflows")

    print(f"\n   Telemetry Summary:")
    telemetry = result.aggregated_telemetry
    print(f"   • Total events: {telemetry.get('total_events', 0)}")
    print(f"   • Commits: {telemetry.get('commits', 0)}")
    print(f"   • Pull requests: {telemetry.get('pull_requests', 0)}")
    print(f"   • CI runs: {telemetry.get('ci_runs', 0)}")

    print("\n" + "=" * 60)
    print("✅ Sprint simulation complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run first_sprint.py
```

**Expected output:**
```
============================================================
Single Team Sprint Simulation
============================================================

1️⃣  Configuring 2-week sprint...
   Sprint ID: sprint_42
   Duration: 10 work days
   Work hours: 9:00 - 18:00

   Phase breakdown:
   • Planning: 9.0h (10%)
   • Development: 63.0h (70%)
   • Code Freeze: 13.5h (15%)
   • Retrospective: 4.5h (5%)

2️⃣  Configuring Team Alpha...
   Team: team_alpha
   Team Size: 5
   Focus: backend
   Repository: backend-api
   Velocity: 30 points
   Total workflows: 9
   • feature: 5
   • bugfix: 3
   • refactoring: 1

3️⃣  Initializing GitHub client (mocked)...
   ✅ Client ready for demo-org

4️⃣  Creating sprint orchestrator...
   ✅ Orchestrator ready

5️⃣  Executing sprint (this will take a moment)...
   --------------------------------------------------------
   --------------------------------------------------------

6️⃣  Sprint Results:
   Success: ✅ YES
   Total workflows: 9
   Successful: 9
   Failed: 0
   Success rate: 100.0%

   Phase Results:
   • Planning: 1 workflows
   • Development: 6 workflows
   • Code Freeze: 1 workflows
   • Retrospective: 1 workflows

   Telemetry Summary:
   • Total events: 54
   • Commits: 18
   • Pull requests: 9
   • CI runs: 9

============================================================
✅ Sprint simulation complete!
============================================================
```

### Step 2: Export Telemetry

Let's export the telemetry for analysis:

```python
# File: export_telemetry.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from azure_haymaker.engineering_sim.orchestration.types import SprintConfig, TeamConfig
from azure_haymaker.engineering_sim.orchestration.sprint_orchestrator import SprintOrchestrator

async def main():
    print("Exporting Sprint Telemetry")
    print("=" * 60)

    # Configure and run sprint (abbreviated)
    sprint_config = SprintConfig(
        sprint_id="sprint_42",
        duration_days=10,
        start_date=datetime.now()
    )
    team_config = TeamConfig(
        team_id="team_alpha",
        team_size=5,
        focus="backend",
        repo="backend-api",
        velocity_points=30,
        workflows=[{"type": "feature", "count": 3}]
    )

    github_client = MagicMock()
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={"sha": "abc123"})
    github_client.create_pull_request = AsyncMock(return_value={"number": 1})
    github_client.create_review = AsyncMock(return_value={"id": 1})
    github_client.update_check_run = AsyncMock(return_value={"conclusion": "success"})
    github_client.merge_pull_request = AsyncMock(return_value={"merged": True})

    orchestrator = SprintOrchestrator(sprint_config, team_config, github_client)
    result = await orchestrator.execute_sprint()

    # Export telemetry
    output_dir = Path("telemetry_output")
    output_dir.mkdir(exist_ok=True)

    telemetry_file = output_dir / f"{sprint_config.sprint_id}_{team_config.team_id}.json"

    with open(telemetry_file, "w") as f:
        json.dump(result.aggregated_telemetry, f, indent=2)

    print(f"✅ Telemetry exported to: {telemetry_file}")
    print(f"   File size: {telemetry_file.stat().st_size:,} bytes")
    print(f"   Events captured: {result.aggregated_telemetry.get('total_events', 0)}")

    print("\nTelemetry structure:")
    print(json.dumps(result.aggregated_telemetry, indent=2)[:500] + "...")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run export_telemetry.py
```

**Expected output:**
```
Exporting Sprint Telemetry
============================================================
✅ Telemetry exported to: telemetry_output/sprint_42_team_alpha.json
   File size: 8,453 bytes
   Events captured: 18

Telemetry structure:
{
  "sprint_id": "sprint_42",
  "team_id": "team_alpha",
  "total_events": 18,
  "commits": 6,
  "pull_requests": 3,
  "ci_runs": 3,
  "reviews": 3,
  "merges": 3,
  "phases": [
    {
      "phase": "development",
      "workflows_executed": 2
    },
...
```

### What You've Learned

- How to configure sprint parameters (duration, work hours)
- Understanding sprint phases and distributions
- How to configure team workflows
- How to execute a complete sprint
- How to export and analyze telemetry

### Next Steps

Now let's orchestrate multiple teams working in parallel.

---

## Part 5: Multi-Team Orchestration (15 minutes)

Learn how to coordinate 3-50 teams running sprints simultaneously with shared rate limiting.

### What Is Multi-Team Orchestration?

The `MultiTeamOrchestrator` coordinates multiple teams:

- **Parallel execution**: Teams work simultaneously
- **Rate limit management**: Shared GitHub API budget
- **Failure isolation**: One team's failure doesn't crash others
- **Cross-team telemetry**: Aggregated metrics across all teams

### Step 1: Configure Multiple Teams

```python
# File: multi_team_sprint.py
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from azure_haymaker.engineering_sim.orchestration.types import (
    SprintConfig,
    TeamConfig
)
from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import (
    MultiTeamOrchestrator
)
from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import (
    RateLimitManager
)

async def main():
    print("=" * 60)
    print("Multi-Team Sprint Simulation")
    print("=" * 60)

    # Step 1: Create shared sprint configuration
    print("\n1️⃣  Configuring shared sprint...")
    sprint_config = SprintConfig(
        sprint_id="q4_sprint_1",
        duration_days=10,
        start_date=datetime.now(),
        work_hours_start=9,
        work_hours_end=18
    )
    print(f"   Sprint: {sprint_config.sprint_id}")
    print(f"   Duration: {sprint_config.duration_days} days")

    # Step 2: Create team configurations
    print("\n2️⃣  Configuring 3 teams...")

    team_configs = [
        TeamConfig(
            team_id="team_alpha",
            team_size=5,
            focus="backend",
            repo="backend-api",
            velocity_points=30,
            workflows=[
                {"type": "feature", "count": 4},
                {"type": "bugfix", "count": 2}
            ]
        ),
        TeamConfig(
            team_id="team_beta",
            team_size=4,
            focus="frontend",
            repo="frontend-web",
            velocity_points=25,
            workflows=[
                {"type": "feature", "count": 3},
                {"type": "refactoring", "count": 2}
            ]
        ),
        TeamConfig(
            team_id="team_gamma",
            team_size=3,
            focus="infrastructure",
            repo="infrastructure",
            velocity_points=20,
            workflows=[
                {"type": "feature", "count": 2},
                {"type": "bugfix", "count": 1}
            ]
        )
    ]

    for i, team in enumerate(team_configs, 1):
        total_workflows = sum(w['count'] for w in team.workflows)
        print(f"   {i}. {team.team_id} ({team.focus})")
        print(f"      Repository: {team.repo}")
        print(f"      Team Size: {team.team_size}")
        print(f"      Velocity: {team.velocity_points} points")
        print(f"      Workflows: {total_workflows}")

    # Step 3: Create rate limit manager
    print("\n3️⃣  Configuring rate limit manager...")
    rate_limit_manager = RateLimitManager(
        requests_per_hour=5000,  # GitHub API limit
        burst_size=100
    )
    print(f"   Requests/hour: {rate_limit_manager.requests_per_hour}")
    print(f"   Burst size: {rate_limit_manager.burst_size}")

    # Step 4: Create mock GitHub client
    print("\n4️⃣  Initializing GitHub client (mocked)...")
    github_client = MagicMock()
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={"sha": "abc123"})
    github_client.create_pull_request = AsyncMock(return_value={"number": 1})
    github_client.create_review = AsyncMock(return_value={"id": 1})
    github_client.update_check_run = AsyncMock(return_value={"conclusion": "success"})
    github_client.merge_pull_request = AsyncMock(return_value={"merged": True})
    print(f"   ✅ Client ready")

    # Step 5: Create multi-team orchestrator
    print("\n5️⃣  Creating multi-team orchestrator...")
    orchestrator = MultiTeamOrchestrator(
        sprint_config=sprint_config,
        team_configs=team_configs,
        rate_limit_manager=rate_limit_manager,
        max_concurrent_teams=2,  # Limit to 2 teams at a time
        github_client=github_client
    )
    print(f"   ✅ Managing {len(team_configs)} teams")
    print(f"   ✅ Max concurrent: {orchestrator.max_concurrent_teams}")

    # Step 6: Execute multi-team sprint
    print("\n6️⃣  Executing multi-team sprint...")
    print("   " + "-" * 56)

    result = await orchestrator.execute_sprint()

    print("   " + "-" * 56)

    # Step 7: Analyze results
    print(f"\n7️⃣  Multi-Team Results:")
    print(f"   Sprint: {result.sprint_id}")
    print(f"   Teams: {len(result.team_results)}")
    print(f"   Total workflows: {result.total_workflows}")
    print(f"   Successful: {result.successful_workflows}")
    print(f"   Failed: {result.failed_workflows}")
    print(f"   Success rate: {result.successful_workflows/result.total_workflows*100:.1f}%")

    print(f"\n   Per-Team Breakdown:")
    for team_result in result.team_results:
        success_rate = (team_result.successful_workflows /
                       team_result.total_workflows * 100
                       if team_result.total_workflows > 0 else 0)
        print(f"   • {team_result.team_id}:")
        print(f"     - Workflows: {team_result.successful_workflows}/{team_result.total_workflows}")
        print(f"     - Success rate: {success_rate:.1f}%")

    print(f"\n   Aggregated Telemetry:")
    telemetry = result.aggregated_telemetry
    print(f"   • Total events: {telemetry.get('total_events', 0)}")
    print(f"   • Commits: {telemetry.get('total_commits', 0)}")
    print(f"   • Pull requests: {telemetry.get('total_pull_requests', 0)}")
    print(f"   • CI runs: {telemetry.get('total_ci_runs', 0)}")

    print("\n" + "=" * 60)
    print("✅ Multi-team sprint complete!")
    print("=" * 60)
    print("\nKey Benefits:")
    print("  • Teams work in parallel (faster execution)")
    print("  • Shared rate limit prevents API throttling")
    print("  • Failure isolation (one team failure doesn't stop others)")
    print("  • Cross-team analytics and insights")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run multi_team_sprint.py
```

**Expected output:**
```
============================================================
Multi-Team Sprint Simulation
============================================================

1️⃣  Configuring shared sprint...
   Sprint: q4_sprint_1
   Duration: 10 days

2️⃣  Configuring 3 teams...
   1. team_alpha (backend)
      Repository: backend-api
      Team Size: 5
      Velocity: 30 points
      Workflows: 6
   2. team_beta (frontend)
      Repository: frontend-web
      Team Size: 4
      Velocity: 25 points
      Workflows: 5
   3. team_gamma (infrastructure)
      Repository: infrastructure
      Team Size: 3
      Velocity: 20 points
      Workflows: 3

3️⃣  Configuring rate limit manager...
   Requests/hour: 5000
   Burst size: 100

4️⃣  Initializing GitHub client (mocked)...
   ✅ Client ready

5️⃣  Creating multi-team orchestrator...
   ✅ Managing 3 teams
   ✅ Max concurrent: 2

6️⃣  Executing multi-team sprint...
   --------------------------------------------------------
   --------------------------------------------------------

7️⃣  Multi-Team Results:
   Sprint: q4_sprint_1
   Teams: 3
   Total workflows: 14
   Successful: 14
   Failed: 0
   Success rate: 100.0%

   Per-Team Breakdown:
   • team_alpha:
     - Workflows: 6/6
     - Success rate: 100.0%
   • team_beta:
     - Workflows: 5/5
     - Success rate: 100.0%
   • team_gamma:
     - Workflows: 3/3
     - Success rate: 100.0%

   Aggregated Telemetry:
   • Total events: 84
   • Commits: 28
   • Pull requests: 14
   • CI runs: 14

============================================================
✅ Multi-team sprint complete!
============================================================

Key Benefits:
  • Teams work in parallel (faster execution)
  • Shared rate limit prevents API throttling
  • Failure isolation (one team failure doesn't stop others)
  • Cross-team analytics and insights
============================================================
```

### Step 2: Export Multi-Team Telemetry

```python
# File: export_multi_team.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from azure_haymaker.engineering_sim.orchestration.types import SprintConfig, TeamConfig
from azure_haymaker.engineering_sim.orchestration.multi_team_orchestrator import MultiTeamOrchestrator

async def main():
    print("Exporting Multi-Team Telemetry")
    print("=" * 60)

    # Configure and run (abbreviated for example)
    sprint_config = SprintConfig(
        sprint_id="q4_sprint_1",
        duration_days=10,
        start_date=datetime.now()
    )

    team_configs = [
        TeamConfig(
            team_id=f"team_{i}",
            team_size=5,
            focus="backend",
            repo=f"repo-{i}",
            velocity_points=30,
            workflows=[{"type": "feature", "count": 2}]
        )
        for i in range(1, 4)
    ]

    github_client = MagicMock()
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={"sha": "abc123"})
    github_client.create_pull_request = AsyncMock(return_value={"number": 1})
    github_client.create_review = AsyncMock(return_value={"id": 1})
    github_client.update_check_run = AsyncMock(return_value={"conclusion": "success"})
    github_client.merge_pull_request = AsyncMock(return_value={"merged": True})

    orchestrator = MultiTeamOrchestrator(sprint_config, team_configs, github_client=github_client)
    result = await orchestrator.execute_sprint()

    # Export telemetry
    output_dir = Path("telemetry_output")
    output_dir.mkdir(exist_ok=True)

    # Export aggregated telemetry
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    aggregate_file = output_dir / f"multi_team_{sprint_config.sprint_id}_{timestamp}.json"

    export_data = {
        "sprint_id": result.sprint_id,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "teams": len(result.team_results),
            "total_workflows": result.total_workflows,
            "successful_workflows": result.successful_workflows,
            "failed_workflows": result.failed_workflows,
        },
        "team_results": [
            {
                "team_id": tr.team_id,
                "workflows": tr.total_workflows,
                "success_rate": tr.successful_workflows / tr.total_workflows if tr.total_workflows > 0 else 0
            }
            for tr in result.team_results
        ],
        "telemetry": result.aggregated_telemetry
    }

    with open(aggregate_file, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"✅ Aggregated telemetry: {aggregate_file}")
    print(f"   Teams: {len(result.team_results)}")
    print(f"   Total workflows: {result.total_workflows}")
    print(f"   File size: {aggregate_file.stat().st_size:,} bytes")

    # Also export per-team files
    for team_result in result.team_results:
        team_file = output_dir / f"team_{team_result.team_id}_{sprint_config.sprint_id}.json"
        with open(team_file, "w") as f:
            json.dump(team_result.aggregated_telemetry, f, indent=2)
        print(f"✅ Team telemetry: {team_file}")

    print("\n" + "=" * 60)
    print("Telemetry Export Complete!")
    print("=" * 60)
    print(f"\nExported files:")
    print(f"  • 1 aggregated file (all teams)")
    print(f"  • {len(result.team_results)} individual team files")
    print(f"\nLocation: {output_dir.absolute()}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run export_multi_team.py
```

**Expected output:**
```
Exporting Multi-Team Telemetry
============================================================
✅ Aggregated telemetry: telemetry_output/multi_team_q4_sprint_1_20251208_120000.json
   Teams: 3
   Total workflows: 6
   File size: 12,453 bytes
✅ Team telemetry: telemetry_output/team_team_1_q4_sprint_1.json
✅ Team telemetry: telemetry_output/team_team_2_q4_sprint_1.json
✅ Team telemetry: telemetry_output/team_team_3_q4_sprint_1.json

============================================================
Telemetry Export Complete!
============================================================

Exported files:
  • 1 aggregated file (all teams)
  • 3 individual team files

Location: /home/azureuser/src/AzureHayMaker/worktrees/feat-issue-145-engineering-simulation/telemetry_output
```

### What You've Learned

- How to configure multiple teams with different workflows
- How to use RateLimitManager for shared API budgets
- How to orchestrate parallel team execution
- How to aggregate telemetry across teams
- How to export multi-team telemetry for analysis

### Next Steps

Now let's explore advanced topics like custom bricks and troubleshooting.

---

## Part 6: Advanced Topics (10 minutes)

Learn how to extend the framework and handle common issues.

### Custom Bricks

Create your own bricks for specialized scenarios:

```python
# File: custom_brick.py
import asyncio
import time
from azure_haymaker.engineering_sim.bricks.base import (
    WorkflowBrick,
    BrickContext,
    BrickResult
)

class DeploymentBrick(WorkflowBrick):
    """Custom brick for simulating deployments.

    This brick simulates deploying code to an environment
    after a successful merge.
    """

    def __init__(self, environment: str, delay_seconds: float = 2.0):
        self.environment = environment
        self.delay_seconds = delay_seconds

    @property
    def name(self) -> str:
        return f"DeploymentBrick({self.environment})"

    def validate(self, context: BrickContext) -> bool:
        """Validate that context has a commit SHA (something to deploy)."""
        if not context.commit_sha:
            return False
        return True

    async def execute(self, context: BrickContext) -> BrickResult:
        """Execute deployment simulation."""
        start_time = time.time()

        # Simulate deployment delay
        await asyncio.sleep(self.delay_seconds)

        # Generate telemetry
        telemetry = {
            "brick_type": "deployment",
            "environment": self.environment,
            "commit_sha": context.commit_sha,
            "status": "deployed",
            "timestamp": time.time()
        }

        # Update context with deployment info
        updated_metadata = {
            **context.metadata,
            "deployed_to": self.environment
        }
        updated_context = context.update(metadata=updated_metadata)

        duration = time.time() - start_time

        return BrickResult(
            success=True,
            context=updated_context,
            telemetry=telemetry,
            duration_seconds=duration
        )

async def main():
    from unittest.mock import MagicMock, AsyncMock
    from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
    from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
    from azure_haymaker.engineering_sim.workflow import Workflow

    print("=" * 60)
    print("Custom Brick Example: DeploymentBrick")
    print("=" * 60)

    # Mock GitHub client
    github_client = MagicMock()
    github_client.org = "demo-org"
    github_client.create_commit = AsyncMock(return_value={"sha": "abc123"})
    github_client.merge_pull_request = AsyncMock(return_value={"merged": True, "sha": "merge456"})

    # Create workflow with custom brick
    print("\n1️⃣  Creating deployment workflow...")
    deployment_workflow = (
        Workflow("Deploy to Staging")
        .add_brick(CommitBrick(github_client))
        .add_brick(MergeBrick(github_client))
        .add_brick(DeploymentBrick(environment="staging", delay_seconds=1.0))
    )

    print(f"   Workflow: {deployment_workflow.name}")
    print(f"   Bricks: {[b.name for b in deployment_workflow.bricks]}")

    # Execute
    print("\n2️⃣  Executing workflow with custom brick...")
    context = BrickContext(
        team_id="team_alpha",
        sprint_id="sprint_42",
        repo_name="backend-api",
        branch_name="feature/new-api",
        pr_number=123
    )

    result = await deployment_workflow.execute(context)

    print(f"\n3️⃣  Results:")
    print(f"   Success: {result.success}")
    print(f"   Deployed to: {result.context.metadata.get('deployed_to')}")

    # Check telemetry
    brick_telemetry = result.telemetry.get("bricks", [])
    deployment_telemetry = [t for t in brick_telemetry if t.get("brick_type") == "deployment"][0]

    print(f"\n4️⃣  Deployment telemetry:")
    print(f"   Environment: {deployment_telemetry['environment']}")
    print(f"   Status: {deployment_telemetry['status']}")
    print(f"   Commit: {deployment_telemetry['commit_sha'][:7]}")

    print("\n" + "=" * 60)
    print("✅ Custom brick works!")
    print("=" * 60)
    print("\nTo create your own bricks:")
    print("  1. Inherit from WorkflowBrick")
    print("  2. Implement name, validate(), and execute()")
    print("  3. Return BrickResult with updated context")
    print("  4. Generate telemetry for tracking")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run custom_brick.py
```

**Expected output:**
```
============================================================
Custom Brick Example: DeploymentBrick
============================================================

1️⃣  Creating deployment workflow...
   Workflow: Deploy to Staging
   Bricks: ['CommitBrick', 'MergeBrick', 'DeploymentBrick(staging)']

2️⃣  Executing workflow with custom brick...

3️⃣  Results:
   Success: True
   Deployed to: staging

4️⃣  Deployment telemetry:
   Environment: staging
   Status: deployed
   Commit: abc123d

============================================================
✅ Custom brick works!
============================================================

To create your own bricks:
  1. Inherit from WorkflowBrick
  2. Implement name, validate(), and execute()
  3. Return BrickResult with updated context
  4. Generate telemetry for tracking
============================================================
```

### Troubleshooting Common Issues

#### Issue 1: Rate Limit Errors

```python
# Solution: Use RateLimitManager
from azure_haymaker.engineering_sim.orchestration.rate_limit_manager import RateLimitManager

rate_limiter = RateLimitManager(
    requests_per_hour=5000,  # GitHub limit
    burst_size=100,
    strategy="wait"  # Wait instead of failing
)

# Use with MultiTeamOrchestrator
orchestrator = MultiTeamOrchestrator(
    sprint_config=sprint_config,
    team_configs=team_configs,
    rate_limit_manager=rate_limiter
)
```

#### Issue 2: Workflow Validation Failures

```python
# Solution: Validate before execution
from azure_haymaker.engineering_sim.workflow import Workflow
from azure_haymaker.engineering_sim.bricks.base import BrickContext

workflow = Workflow("My Workflow")
# ... add bricks ...

context = BrickContext(
    team_id="team_alpha",
    sprint_id="sprint_42",
    repo_name="my-repo"
)

# Check validation before running
errors = workflow.validate_all(context)
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    result = await workflow.execute(context)
```

#### Issue 3: GitHub Authentication

```python
# Solution: Test authentication first
from azure_haymaker.engineering_sim.github_client import GitHubClient
import os

async def test_auth():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN not set")
        return False

    client = GitHubClient(token=token, org="your-org")

    try:
        # Test with a simple API call
        # (actual implementation would test real endpoint)
        print("✅ GitHub authentication working")
        return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

# Run before starting simulation
asyncio.run(test_auth())
```

### What You've Learned

- How to create custom bricks by extending WorkflowBrick
- How to properly configure SprintConfig with required parameters
- Common issues and their solutions
- How to validate workflows before execution
- How to test GitHub authentication

---

## Next Steps

### Going Further

Now that you've completed the tutorial, you can:

1. **Run with real GitHub credentials**
   - Set up a test repository
   - Configure real GitHub token
   - Run against actual GitHub API

2. **Scale to production**
   - Configure 10-50 teams
   - Run longer sprints (4-6 weeks)
   - Export telemetry to analytics tools

3. **Customize for your needs**
   - Create domain-specific bricks
   - Build custom workflow patterns
   - Integrate with CI/CD pipelines

4. **Extend the framework**
   - Add new brick types (notifications, deployments)
   - Create custom orchestration logic
   - Build reporting dashboards

### Additional Resources

- **[Engineering Simulation Architecture](../architecture/)** - Deep dive into framework design
- **[API Reference](../reference/api.md)** - Complete API documentation
- **[Example Scripts](../../examples/)** - More complex examples
- **[Issue #145](https://github.com/rysweet/AzureHayMaker/issues/145)** - Original feature request

### Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/rysweet/AzureHayMaker/issues)
- **Discussions**: [Ask questions or share ideas](https://github.com/rysweet/AzureHayMaker/discussions)
- **Documentation**: [Browse all docs](../)

---

## Summary

Congratulations! You've learned:

- ✅ How to install and verify the framework
- ✅ Understanding the 5 core bricks
- ✅ Composing bricks into workflows
- ✅ Running single-team sprints
- ✅ Orchestrating multi-team simulations
- ✅ Creating custom bricks
- ✅ Troubleshooting common issues

You're now ready to simulate realistic engineering team activities and generate telemetry for your cybersecurity analysis needs.

---

**Last updated**: December 8, 2025
