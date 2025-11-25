#!/usr/bin/env python3
"""
Data models for power-steering checker.

Defines all dataclasses used across the power-steering system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class CheckerResult:
    """Result from a single consideration checker."""

    consideration_id: str
    satisfied: bool
    reason: str
    severity: Literal["blocker", "warning"]


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""

    results: Dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: List[CheckerResult] = field(default_factory=list)
    failed_warnings: List[CheckerResult] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """True if any blocker consideration failed."""
        return len(self.failed_blockers) > 0

    def add_result(self, result: CheckerResult) -> None:
        """Add result for a consideration."""
        self.results[result.consideration_id] = result
        if not result.satisfied:
            if result.severity == "blocker":
                self.failed_blockers.append(result)
            else:
                self.failed_warnings.append(result)

    def group_by_category(self) -> Dict[str, List[CheckerResult]]:
        """Group failed considerations by category."""
        grouped: Dict[str, List[CheckerResult]] = {}
        for result in self.failed_blockers + self.failed_warnings:
            # Simple category derivation from ID
            if "workflow" in result.consideration_id or "philosophy" in result.consideration_id:
                category = "Workflow & Philosophy"
            elif "testing" in result.consideration_id or "ci" in result.consideration_id:
                category = "Testing & CI/CD"
            else:
                category = "Completion Checks"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(result)
        return grouped


@dataclass
class PowerSteeringRedirect:
    """Record of a power-steering redirect (blocked session)."""

    redirect_number: int
    timestamp: str  # ISO format
    failed_considerations: List[str]  # IDs of failed checks
    continuation_prompt: str
    work_summary: Optional[str] = None


@dataclass
class PowerSteeringResult:
    """Final decision from power-steering analysis."""

    decision: Literal["approve", "block"]
    reasons: List[str]
    continuation_prompt: Optional[str] = None
    summary: Optional[str] = None
