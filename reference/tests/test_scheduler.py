"""
Test suite for the GCS Kernel Scheduler.

This module contains tests for the ToolExecutionScheduler component of the GCS Kernel.
"""
import pytest
import asyncio
from gcs_kernel.scheduler import ToolExecutionScheduler
from gcs_kernel.models import ToolDefinition, ToolState


@pytest.mark.asyncio
async def test_scheduler_initialization():
    """Test that ToolExecutionScheduler initializes properly."""
    scheduler = ToolExecutionScheduler()
    
    assert scheduler.executions == {}
    assert scheduler.approval_queue is not None


@pytest.mark.asyncio
async def test_tool_execution_lifecycle():
    """Tool execution goes through all required states properly."""
    scheduler = ToolExecutionScheduler()
    tool_def = ToolDefinition(
        name="test_tool",
        display_name="Test Tool",
        description="A test tool",
        parameter_schema={"type": "object", "properties": {"value": {"type": "string"}}},
        approval_required=False  # Explicitly set to False to bypass approval
    )
    
    execution_id = await scheduler.submit_tool_execution(tool_def, {"value": "test"})
    execution = scheduler.executions[execution_id]
    
    # Since approval is not required, it should move to scheduled or executing state
    assert execution.state in [ToolState.SCHEDULED, ToolState.EXECUTING, ToolState.COMPLETED]


@pytest.mark.asyncio
async def test_tool_execution_with_approval():
    """Tool execution properly requests and processes approval."""
    scheduler = ToolExecutionScheduler()
    tool_def = ToolDefinition(
        name="secure_tool",
        display_name="Secure Tool",
        description="A tool requiring approval",
        parameter_schema={"type": "object", "properties": {"value": {"type": "string"}}},
        approval_required=True
    )
    
    execution_id = await scheduler.submit_tool_execution(tool_def, {"value": "test"})
    execution = scheduler.executions[execution_id]
    
    # Should be awaiting approval since approval_required=True
    assert execution.state == ToolState.AWAITING_APPROVAL