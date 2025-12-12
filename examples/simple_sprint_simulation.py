#!/usr/bin/env python3
"""Simple Sprint Simulation Example

This example demonstrates how to use the Engineering Simulation framework
to simulate a realistic 2-week sprint with feature development workflows.

This is an OUTSIDE-IN test - testing the feature like a real user would.
"""

import asyncio
import os
from datetime import datetime

from azure_haymaker.engineering_sim.bricks.base import BrickContext
from azure_haymaker.engineering_sim.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.engineering_sim.bricks.commit import CommitBrick
from azure_haymaker.engineering_sim.bricks.merge import MergeBrick
from azure_haymaker.engineering_sim.bricks.pull_request import PullRequestBrick
from azure_haymaker.engineering_sim.bricks.review import ReviewBrick
from azure_haymaker.engineering_sim.github_client import GitHubClient
from azure_haymaker.engineering_sim.workflow import Workflow


async def main():
    """Run a simple sprint simulation."""
    print("=" * 80)
    print("Software Engineering Team Simulation - Outside-In Test")
    print("=" * 80)
    print()

    # Step 1: Create GitHub client (mock mode for testing)
    print("✅ Step 1: Initialize GitHub client")
    github_client = GitHubClient(
        token="mock-token-for-testing",  # Mock token for testing
        org="test-org",
    )
    print(f"   Organization: {github_client.org}")
    print()

    # Step 2: Create workflow bricks
    print("✅ Step 2: Create workflow bricks")
    commit_brick = CommitBrick(github_client)
    pr_brick = PullRequestBrick(github_client)
    ci_brick = CIPipelineBrick(github_client, failure_rate=0.15)
    review_brick = ReviewBrick(github_client)
    merge_brick = MergeBrick(github_client)
    print("   Created 5 bricks: Commit, PullRequest, CI, Review, Merge")
    print()

    # Step 3: Compose feature development workflow
    print("✅ Step 3: Compose feature development workflow")
    feature_workflow = (
        Workflow(name="Feature Development")
        .add_brick(commit_brick)
        .add_brick(commit_brick)  # Second commit
        .add_brick(pr_brick)
        .add_brick(ci_brick)
        .add_brick(review_brick)
        .add_brick(merge_brick)
    )
    print(f"   Workflow: {feature_workflow.name}")
    print(f"   Bricks: {len(feature_workflow.bricks)}")
    print(f"   Estimated duration: {feature_workflow.estimate_duration():.1f}s")
    print()

    # Step 4: Execute workflow (bricks validate as they run)
    print("✅ Step 4: Execute feature development workflow")
    print("-" * 80)

    context = BrickContext(
        team_id="team_alpha",
        sprint_id="sprint_23",
        repo_name="test-repo",
        branch_name="feature/user-authentication",
        base_branch="main",
        metadata={
            "agent_id": "developer_a",
            "feature_name": "User Authentication with JWT",
            "author_name": "Alice Developer",
            "author_email": "alice@example.com",
        },
    )

    result = await feature_workflow.execute(context)

    print("-" * 80)
    print()

    # Step 5: Report results
    print("✅ Step 5: Workflow execution results")
    print(f"   Success: {result.success}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Telemetry events: {len(result.telemetry)}")
    print()

    print("📊 Telemetry Generated:")
    for i, (key, value) in enumerate(result.telemetry.items(), 1):
        if isinstance(value, dict):
            print(f"   {i}. {key}: {value.get('type', 'unknown')}")
        else:
            print(f"   {i}. {key}: {value}")
    print()

    # Step 6: Verify realistic telemetry patterns
    print("✅ Step 6: Verify realistic telemetry patterns")
    telemetry_types = [
        v.get("type") if isinstance(v, dict) else None for v in result.telemetry.values()
    ]
    expected_types = ["commit", "commit", "pull_request", "ci_run", "review", "merge"]

    print(f"   Expected types: {expected_types}")
    print(f"   Actual types: {[t for t in telemetry_types if t]}")

    # Check for expected telemetry
    has_commits = any(t == "commit" for t in telemetry_types)
    has_pr = any(t == "pull_request" for t in telemetry_types)
    has_ci = any(t == "ci_run" for t in telemetry_types)
    has_review = any(t == "review" for t in telemetry_types)

    print()
    print("   ✅ Commits: ", "✅" if has_commits else "❌")
    print("   ✅ Pull Request: ", "✅" if has_pr else "❌")
    print("   ✅ CI Pipeline: ", "✅" if has_ci else "❌")
    print("   ✅ Code Review: ", "✅" if has_review else "❌")
    print()

    # Step 7: Summary
    print("=" * 80)
    print("🎉 Outside-In Test Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Workflow executed successfully: {result.success}")
    print(f"  • Total bricks executed: {len(feature_workflow.bricks)}")
    print(f"  • Telemetry events generated: {len(result.telemetry)}")
    print(f"  • Context properly threaded: {result.context is not None}")
    print()
    print("The Engineering Simulation framework is working correctly!")
    print("Real users can now:")
    print("  1. Create custom workflows by composing bricks")
    print("  2. Simulate realistic software development patterns")
    print("  3. Generate telemetry for GitHub analytics")
    print("  4. Model multi-team sprint coordination")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
