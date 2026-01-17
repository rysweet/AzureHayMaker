"""Core workflow bricks for software engineering team simulation.

Each brick is a self-contained component with ONE clear responsibility:
- CommitBrick: Creates git commits
- PullRequestBrick: Creates pull requests
- CodeReviewBrick: Submits code reviews
- CIPipelineBrick: Triggers CI pipelines
- MergeBrick: Merges pull requests
"""

from azure_haymaker.workflow_bricks.bricks.ci_pipeline import CIPipelineBrick
from azure_haymaker.workflow_bricks.bricks.code_review import CodeReviewBrick
from azure_haymaker.workflow_bricks.bricks.commit import CommitBrick
from azure_haymaker.workflow_bricks.bricks.merge import MergeBrick
from azure_haymaker.workflow_bricks.bricks.pull_request import PullRequestBrick

__all__ = [
    "CommitBrick",
    "PullRequestBrick",
    "CodeReviewBrick",
    "CIPipelineBrick",
    "MergeBrick",
]
