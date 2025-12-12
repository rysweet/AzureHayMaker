"""Unit tests for base brick framework.

Tests cover:
- BrickContext model validation and state management
- BrickResult model validation and telemetry handling
- WorkflowBrick interface contract
- Context threading between bricks
- Error handling and validation

These tests define the interface contracts that all bricks must follow.
Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from dataclasses import replace
from typing import Dict, Any
from datetime import datetime

# These imports WILL FAIL - implementation doesn't exist yet
from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickResult,
    WorkflowBrick,
    BrickExecutionError,
    BrickValidationError,
)


class TestBrickContext:
    """Test BrickContext data model."""

    def test_brick_context_initialization_with_required_fields(self):
        """Test BrickContext can be initialized with required fields only."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        assert context.team_id == "team_alpha"
        assert context.sprint_id == "sprint_42"
        assert context.repo_name == "backend-api"
        assert context.branch_name is None
        assert context.pr_number is None
        assert context.commit_sha is None
        assert context.base_branch == "main"
        assert isinstance(context.metadata, dict)
        assert len(context.metadata) == 0

    def test_brick_context_initialization_with_all_fields(self):
        """Test BrickContext can be initialized with all fields."""
        metadata = {"test_key": "test_value", "iteration": 1}

        context = BrickContext(
            team_id="team_beta",
            sprint_id="sprint_43",
            repo_name="frontend-app",
            branch_name="feature/oauth2",
            pr_number=142,
            commit_sha="a1b2c3d4e5f6",
            base_branch="develop",
            metadata=metadata
        )

        assert context.team_id == "team_beta"
        assert context.sprint_id == "sprint_43"
        assert context.repo_name == "frontend-app"
        assert context.branch_name == "feature/oauth2"
        assert context.pr_number == 142
        assert context.commit_sha == "a1b2c3d4e5f6"
        assert context.base_branch == "develop"
        assert context.metadata == metadata

    def test_brick_context_metadata_defaults_to_empty_dict(self):
        """Test metadata is initialized as empty dict if None."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            metadata=None
        )

        assert isinstance(context.metadata, dict)
        assert len(context.metadata) == 0

    def test_brick_context_update_creates_new_instance(self):
        """Test update() creates new context with updated fields."""
        original = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2"
        )

        updated = original.update(
            commit_sha="abc123",
            pr_number=142
        )

        # Original should be unchanged
        assert original.commit_sha is None
        assert original.pr_number is None

        # Updated should have new values
        assert updated.commit_sha == "abc123"
        assert updated.pr_number == 142
        assert updated.team_id == "team_alpha"
        assert updated.branch_name == "feature/oauth2"

    def test_brick_context_update_preserves_unmodified_fields(self):
        """Test update() preserves fields not explicitly updated."""
        original = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            branch_name="feature/oauth2",
            metadata={"key1": "value1"}
        )

        updated = original.update(commit_sha="abc123")

        assert updated.team_id == "team_alpha"
        assert updated.sprint_id == "sprint_42"
        assert updated.repo_name == "backend-api"
        assert updated.branch_name == "feature/oauth2"
        assert updated.metadata == {"key1": "value1"}

    def test_brick_context_immutability(self):
        """Test that context follows immutable pattern."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        # update() should return new instance, not modify original
        new_context = context.update(branch_name="feature/test")

        assert context is not new_context
        assert context.branch_name is None
        assert new_context.branch_name == "feature/test"

    def test_brick_context_metadata_can_be_updated(self):
        """Test metadata dict can be updated through context update."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api",
            metadata={"key1": "value1"}
        )

        new_metadata = {**context.metadata, "key2": "value2"}
        updated = context.update(metadata=new_metadata)

        assert updated.metadata == {"key1": "value1", "key2": "value2"}
        assert context.metadata == {"key1": "value1"}


class TestBrickResult:
    """Test BrickResult data model."""

    def test_brick_result_success_initialization(self):
        """Test BrickResult for successful execution."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        telemetry = {
            "brick_type": "commit",
            "commit_sha": "abc123",
            "timestamp": datetime.now().isoformat()
        }

        result = BrickResult(
            success=True,
            context=context,
            telemetry=telemetry,
            duration_seconds=1.23
        )

        assert result.success is True
        assert result.context == context
        assert result.telemetry == telemetry
        assert result.error is None
        assert result.duration_seconds == 1.23

    def test_brick_result_failure_initialization(self):
        """Test BrickResult for failed execution."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = BrickResult(
            success=False,
            context=context,
            telemetry={},
            error="Failed to create commit: branch not found",
            duration_seconds=0.45
        )

        assert result.success is False
        assert result.context == context
        assert result.error == "Failed to create commit: branch not found"
        assert result.telemetry == {}
        assert result.duration_seconds == 0.45

    def test_brick_result_merge_telemetry(self):
        """Test merging telemetry from multiple results."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result1 = BrickResult(
            success=True,
            context=context,
            telemetry={"commit_sha": "abc123", "files": ["file1.py"]}
        )

        result2 = BrickResult(
            success=True,
            context=context,
            telemetry={"pr_number": 142, "title": "Add feature"}
        )

        merged = result1.merge_telemetry(result2)

        assert merged.telemetry == {
            "commit_sha": "abc123",
            "files": ["file1.py"],
            "pr_number": 142,
            "title": "Add feature"
        }

    def test_brick_result_merge_telemetry_overwrites_duplicate_keys(self):
        """Test that merge_telemetry overwrites duplicate keys."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result1 = BrickResult(
            success=True,
            context=context,
            telemetry={"status": "pending", "count": 1}
        )

        result2 = BrickResult(
            success=True,
            context=context,
            telemetry={"status": "completed", "count": 2}
        )

        merged = result1.merge_telemetry(result2)

        assert merged.telemetry["status"] == "completed"
        assert merged.telemetry["count"] == 2

    def test_brick_result_duration_defaults_to_zero(self):
        """Test duration_seconds defaults to 0.0."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = BrickResult(
            success=True,
            context=context,
            telemetry={}
        )

        assert result.duration_seconds == 0.0


class TestWorkflowBrick:
    """Test WorkflowBrick abstract base class."""

    def test_workflow_brick_cannot_be_instantiated_directly(self):
        """Test WorkflowBrick is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            WorkflowBrick()

    def test_workflow_brick_requires_execute_implementation(self):
        """Test concrete brick must implement execute()."""
        class IncompleteBrick(WorkflowBrick):
            pass  # Missing execute() implementation

        with pytest.raises(TypeError):
            IncompleteBrick()

    def test_workflow_brick_with_execute_implementation_can_be_instantiated(self):
        """Test concrete brick with execute() can be instantiated."""
        class CompleteBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(
                    success=True,
                    context=context,
                    telemetry={}
                )

        brick = CompleteBrick()
        assert isinstance(brick, WorkflowBrick)
        assert brick.name == "CompleteBrick"

    @pytest.mark.asyncio
    async def test_workflow_brick_execute_returns_brick_result(self):
        """Test execute() returns BrickResult."""
        class TestBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(
                    success=True,
                    context=context,
                    telemetry={"test": "data"}
                )

        brick = TestBrick()
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await brick.execute(context)

        assert isinstance(result, BrickResult)
        assert result.success is True
        assert result.telemetry == {"test": "data"}

    def test_workflow_brick_validate_defaults_to_true(self):
        """Test validate() defaults to returning True."""
        class TestBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(success=True, context=context, telemetry={})

        brick = TestBrick()
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        assert brick.validate(context) is True

    def test_workflow_brick_validate_can_be_overridden(self):
        """Test validate() can be overridden in concrete brick."""
        class TestBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(success=True, context=context, telemetry={})

            def validate(self, context: BrickContext) -> bool:
                return context.branch_name is not None

        brick = TestBrick()

        context_no_branch = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )
        assert brick.validate(context_no_branch) is False

        context_with_branch = context_no_branch.update(branch_name="feature/test")
        assert brick.validate(context_with_branch) is True

    def test_workflow_brick_name_property_returns_class_name(self):
        """Test name property returns class name by default."""
        class CustomBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(success=True, context=context, telemetry={})

        brick = CustomBrick()
        assert brick.name == "CustomBrick"

    def test_workflow_brick_repr_returns_readable_string(self):
        """Test __repr__ returns readable representation."""
        class TestBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(success=True, context=context, telemetry={})

        brick = TestBrick()
        repr_str = repr(brick)

        assert "TestBrick" in repr_str
        assert "()" in repr_str


class TestBrickContextThreading:
    """Test context threading between bricks."""

    @pytest.mark.asyncio
    async def test_context_flows_between_bricks(self):
        """Test context updates flow from one brick to the next."""
        class FirstBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                updated_context = context.update(branch_name="feature/test")
                return BrickResult(
                    success=True,
                    context=updated_context,
                    telemetry={"brick": "first"}
                )

        class SecondBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                # Should receive updated context from FirstBrick
                assert context.branch_name == "feature/test"
                updated_context = context.update(commit_sha="abc123")
                return BrickResult(
                    success=True,
                    context=updated_context,
                    telemetry={"brick": "second"}
                )

        initial_context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        first = FirstBrick()
        first_result = await first.execute(initial_context)

        second = SecondBrick()
        second_result = await second.execute(first_result.context)

        assert second_result.context.branch_name == "feature/test"
        assert second_result.context.commit_sha == "abc123"

    @pytest.mark.asyncio
    async def test_metadata_accumulates_across_bricks(self):
        """Test metadata can accumulate across brick executions."""
        class AddMetadataBrick(WorkflowBrick):
            def __init__(self, key: str, value: str):
                self.key = key
                self.value = value

            async def execute(self, context: BrickContext) -> BrickResult:
                new_metadata = {**context.metadata, self.key: self.value}
                updated_context = context.update(metadata=new_metadata)
                return BrickResult(
                    success=True,
                    context=updated_context,
                    telemetry={}
                )

        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        brick1 = AddMetadataBrick("key1", "value1")
        result1 = await brick1.execute(context)

        brick2 = AddMetadataBrick("key2", "value2")
        result2 = await brick2.execute(result1.context)

        brick3 = AddMetadataBrick("key3", "value3")
        result3 = await brick3.execute(result2.context)

        assert result3.context.metadata == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }


class TestBrickExceptions:
    """Test brick exception handling."""

    def test_brick_execution_error_can_be_raised(self):
        """Test BrickExecutionError exception exists and can be raised."""
        with pytest.raises(BrickExecutionError) as exc_info:
            raise BrickExecutionError("Test error message")

        assert str(exc_info.value) == "Test error message"

    def test_brick_validation_error_can_be_raised(self):
        """Test BrickValidationError exception exists and can be raised."""
        with pytest.raises(BrickValidationError) as exc_info:
            raise BrickValidationError("Validation failed")

        assert str(exc_info.value) == "Validation failed"

    @pytest.mark.asyncio
    async def test_brick_execute_can_raise_execution_error(self):
        """Test brick execute() can raise BrickExecutionError."""
        class FailingBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                raise BrickExecutionError("Simulated failure")

        brick = FailingBrick()
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        with pytest.raises(BrickExecutionError) as exc_info:
            await brick.execute(context)

        assert "Simulated failure" in str(exc_info.value)

    def test_brick_validate_raising_validation_error(self):
        """Test brick validate() can raise BrickValidationError."""
        class StrictBrick(WorkflowBrick):
            async def execute(self, context: BrickContext) -> BrickResult:
                return BrickResult(success=True, context=context, telemetry={})

            def validate(self, context: BrickContext) -> bool:
                if context.branch_name is None:
                    raise BrickValidationError("branch_name is required")
                return True

        brick = StrictBrick()
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        with pytest.raises(BrickValidationError) as exc_info:
            brick.validate(context)

        assert "branch_name is required" in str(exc_info.value)


class TestBrickEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_brick_context_with_empty_strings(self):
        """Test BrickContext handles empty string values."""
        context = BrickContext(
            team_id="",
            sprint_id="",
            repo_name=""
        )

        assert context.team_id == ""
        assert context.sprint_id == ""
        assert context.repo_name == ""

    def test_brick_context_with_special_characters(self):
        """Test BrickContext handles special characters in strings."""
        context = BrickContext(
            team_id="team-alpha_2024",
            sprint_id="sprint/42",
            repo_name="backend.api.v2"
        )

        assert context.team_id == "team-alpha_2024"
        assert context.sprint_id == "sprint/42"
        assert context.repo_name == "backend.api.v2"

    def test_brick_result_with_empty_telemetry(self):
        """Test BrickResult with empty telemetry dict."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = BrickResult(
            success=True,
            context=context,
            telemetry={}
        )

        assert result.telemetry == {}
        assert isinstance(result.telemetry, dict)

    def test_brick_result_with_complex_telemetry(self):
        """Test BrickResult with nested telemetry data."""
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        telemetry = {
            "commit": {
                "sha": "abc123",
                "author": {"name": "Alice", "email": "alice@example.com"},
                "files": ["file1.py", "file2.py"]
            },
            "metrics": {
                "lines_added": 100,
                "lines_deleted": 50
            }
        }

        result = BrickResult(
            success=True,
            context=context,
            telemetry=telemetry
        )

        assert result.telemetry["commit"]["sha"] == "abc123"
        assert result.telemetry["metrics"]["lines_added"] == 100
