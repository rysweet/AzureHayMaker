"""Unit tests for workflow composition engine.

Tests cover:
- Workflow creation and brick addition
- Sequential brick execution
- Context threading through workflow
- Telemetry aggregation
- Error handling and stop-on-failure
- Workflow validation

Following TDD - these tests WILL FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from azure_haymaker.engineering_sim.bricks.base import (
    BrickContext,
    BrickResult,
    WorkflowBrick,
    BrickExecutionError,
)
from azure_haymaker.engineering_sim.workflow import Workflow


class TestWorkflowCreation:
    """Test Workflow instantiation and configuration."""

    def test_workflow_initialization(self):
        """Test Workflow can be initialized with name."""
        workflow = Workflow("feature_development")

        assert workflow.name == "feature_development"
        assert workflow.bricks == []

    def test_workflow_add_brick(self, mock_brick):
        """Test add_brick() adds brick to workflow."""
        workflow = Workflow("test_workflow")
        workflow.add_brick(mock_brick)

        assert len(workflow.bricks) == 1
        assert workflow.bricks[0] == mock_brick

    def test_workflow_add_brick_returns_self(self, mock_brick):
        """Test add_brick() returns self for chaining."""
        workflow = Workflow("test_workflow")
        result = workflow.add_brick(mock_brick)

        assert result is workflow

    def test_workflow_add_multiple_bricks_chaining(self, mock_brick):
        """Test multiple bricks can be added via chaining."""
        brick1 = Mock(spec=WorkflowBrick)
        brick2 = Mock(spec=WorkflowBrick)
        brick3 = Mock(spec=WorkflowBrick)

        workflow = (Workflow("test_workflow")
                    .add_brick(brick1)
                    .add_brick(brick2)
                    .add_brick(brick3))

        assert len(workflow.bricks) == 3
        assert workflow.bricks[0] == brick1
        assert workflow.bricks[1] == brick2
        assert workflow.bricks[2] == brick3


class TestWorkflowExecution:
    """Test Workflow execute() method."""

    @pytest.mark.asyncio
    async def test_execute_empty_workflow(self):
        """Test execute() on workflow with no bricks."""
        workflow = Workflow("empty_workflow")
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert result.success is True
        assert result.context == context

    @pytest.mark.asyncio
    async def test_execute_single_brick(self):
        """Test execute() runs single brick."""
        brick = Mock(spec=WorkflowBrick)
        brick.name = "TestBrick"
        brick.validate = Mock(return_value=True)
        brick.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={"brick": "test"}
        ))

        workflow = Workflow("test_workflow").add_brick(brick)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert result.success is True
        brick.validate.assert_called_once()
        brick.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_bricks_sequentially(self):
        """Test execute() runs bricks in sequence."""
        execution_order = []

        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)
        brick1.execute = AsyncMock(side_effect=lambda ctx: (
            execution_order.append(1),
            BrickResult(
                success=True,
                context=ctx.update(metadata={"brick1": "done"}),
                telemetry={"brick": "1"}
            )
        )[1])

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock(side_effect=lambda ctx: (
            execution_order.append(2),
            BrickResult(
                success=True,
                context=ctx.update(metadata={**ctx.metadata, "brick2": "done"}),
                telemetry={"brick": "2"}
            )
        )[1])

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert result.success is True
        assert execution_order == [1, 2]

    @pytest.mark.asyncio
    async def test_execute_threads_context_between_bricks(self):
        """Test context updates flow from brick to brick."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)
        brick1.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api",
                branch_name="feature/test"
            ),
            telemetry={}
        ))

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api",
                branch_name="feature/test",
                commit_sha="abc123"
            ),
            telemetry={}
        ))

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        # brick2 should receive context from brick1
        brick2_call_context = brick2.execute.call_args[0][0]
        assert brick2_call_context.branch_name == "feature/test"

    @pytest.mark.asyncio
    async def test_execute_aggregates_telemetry(self):
        """Test execute() aggregates telemetry from all bricks."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)
        brick1.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={"brick1": "data1"}
        ))

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={"brick2": "data2"}
        ))

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert "bricks" in result.telemetry
        assert len(result.telemetry["bricks"]) == 2


class TestWorkflowErrorHandling:
    """Test Workflow error handling."""

    @pytest.mark.asyncio
    async def test_execute_stops_on_validation_failure(self):
        """Test execute() stops when validation fails."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.name = "FailingBrick"
        brick1.validate = Mock(return_value=False)  # Validation fails
        brick1.execute = AsyncMock()

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock()

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert result.success is False
        assert "Validation failed" in result.error
        brick1.execute.assert_not_called()
        brick2.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_stops_on_brick_failure(self):
        """Test execute() stops when brick fails."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)
        brick1.execute = AsyncMock(return_value=BrickResult(
            success=False,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={},
            error="Brick execution failed"
        ))

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock()

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        result = await workflow.execute(context)

        assert result.success is False
        brick2.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_continues_on_failure_if_configured(self):
        """Test execute() can continue on failures when stop_on_failure=False."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)
        brick1.execute = AsyncMock(return_value=BrickResult(
            success=False,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={},
            error="Brick 1 failed"
        ))

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)
        brick2.execute = AsyncMock(return_value=BrickResult(
            success=True,
            context=BrickContext(
                team_id="team_alpha",
                sprint_id="sprint_42",
                repo_name="backend-api"
            ),
            telemetry={}
        ))

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        # Execute with stop_on_failure=False
        result = await workflow.execute(context, stop_on_failure=False)

        # Both bricks should execute
        brick1.execute.assert_called_once()
        brick2.execute.assert_called_once()


class TestWorkflowValidation:
    """Test Workflow validation methods."""

    def test_validate_all_returns_empty_list_when_valid(self):
        """Test validate_all() returns empty list when all bricks valid."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.validate = Mock(return_value=True)

        brick2 = Mock(spec=WorkflowBrick)
        brick2.validate = Mock(return_value=True)

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        errors = workflow.validate_all(context)

        assert errors == []

    def test_validate_all_returns_errors_when_invalid(self):
        """Test validate_all() returns errors for invalid bricks."""
        brick1 = Mock(spec=WorkflowBrick)
        brick1.name = "Brick1"
        brick1.validate = Mock(return_value=True)

        brick2 = Mock(spec=WorkflowBrick)
        brick2.name = "Brick2"
        brick2.validate = Mock(return_value=False)

        workflow = Workflow("test_workflow").add_brick(brick1).add_brick(brick2)
        context = BrickContext(
            team_id="team_alpha",
            sprint_id="sprint_42",
            repo_name="backend-api"
        )

        errors = workflow.validate_all(context)

        assert len(errors) > 0

    def test_estimate_duration_returns_float(self):
        """Test estimate_duration() returns estimated seconds."""
        workflow = Workflow("test_workflow")

        duration = workflow.estimate_duration()

        assert isinstance(duration, float)
        assert duration >= 0
