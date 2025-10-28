"""
Basic test suite for the GCS Kernel.

This module contains basic unit tests for the core components of the GCS Kernel.
"""
import pytest
import asyncio
from gcs_kernel.models import ToolDefinition, ToolResult


def test_tool_result_creation():
    """Test creating a ToolResult object."""
    result = ToolResult(
        tool_name="test_tool",
        llm_content="Test result for LLM",
        return_display="Test result for user",
        success=True
    )
    
    assert result.tool_name == "test_tool"
    assert result.llm_content == "Test result for LLM"
    assert result.return_display == "Test result for user"
    assert result.success is True


def test_tool_definition_creation():
    """Test creating a ToolDefinition object."""
    schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    }
    
    tool_def = ToolDefinition.create(
        name="test_tool",
        description="A test tool",
        parameters=schema,
        display_name="Test Tool"
    )
    
    assert tool_def.name == "test_tool"
    assert tool_def.display_name == "Test Tool"
    assert tool_def.description == "A test tool"
    assert tool_def.parameters == schema


@pytest.mark.asyncio
async def test_kernel_initialization():
    """Test GCS Kernel initializes all components properly."""
    from gcs_kernel.kernel import GCSKernel
    
    kernel = GCSKernel()
    assert kernel.event_loop is not None
    assert kernel.scheduler is not None
    assert kernel.registry is not None
    assert kernel.resource_manager is not None
    assert kernel.security_layer is not None
    assert kernel.logger is not None
    assert kernel.mcp_client is not None