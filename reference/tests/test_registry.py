"""
Test suite for the GCS Kernel Registry.

This module contains tests for the ToolRegistry component of the GCS Kernel.
"""
import pytest
import asyncio
from gcs_kernel.registry import ToolRegistry, BaseTool
from gcs_kernel.models import ToolResult


class MockTool(BaseTool):
    """A mock tool for testing purposes."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.display_name = name
        self.description = description
        self.parameter_schema = {"type": "object", "properties": {}}
    
    async def execute(self, parameters):
        return ToolResult(
            tool_name=self.name,
            llm_content=f"Executed {self.name}",
            return_display=f"Executed {self.name}",
            success=True
        )


@pytest.mark.asyncio
async def test_tool_registry_initialization():
    """Test that ToolRegistry initializes properly."""
    registry = ToolRegistry()
    
    assert registry.tools == {}


@pytest.mark.asyncio
async def test_register_tool():
    """Test registering a tool with the registry."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "A test tool")
    
    success = await registry.register_tool(tool)
    
    assert success is True
    assert "test_tool" in registry.tools
    assert registry.tools["test_tool"] == tool


@pytest.mark.asyncio
async def test_get_tool():
    """Test retrieving a tool from the registry."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "A test tool")
    await registry.register_tool(tool)
    
    retrieved_tool = await registry.get_tool("test_tool")
    
    assert retrieved_tool is not None
    assert retrieved_tool.name == "test_tool"


@pytest.mark.asyncio
async def test_deregister_tool():
    """Test removing a tool from the registry."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", "A test tool")
    await registry.register_tool(tool)
    
    success = await registry.deregister_tool("test_tool")
    
    assert success is True
    assert "test_tool" not in registry.tools