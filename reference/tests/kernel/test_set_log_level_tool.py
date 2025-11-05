"""
Test suite for the new SetLogLevelTool functionality.
"""

import pytest
import logging
from gcs_kernel.tools.system_tools import SetLogLevelTool
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.kernel import GCSKernel


@pytest.mark.asyncio
async def test_set_log_level_tool_initialization():
    """Test that SetLogLevelTool can be initialized properly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()
    
    tool = SetLogLevelTool(kernel)
    
    assert tool.name == "set_log_level"
    assert tool.display_name == "Set Log Level"
    assert "DEBUG" in tool.description
    assert "INFO" in tool.description
    assert "WARNING" in tool.description
    assert "ERROR" in tool.description
    assert "CRITICAL" in tool.description
    
    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_log_level_tool_valid_levels():
    """Test that SetLogLevelTool can change log levels correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()
    
    tool = SetLogLevelTool(kernel)
    
    # Test setting to DEBUG level
    result = await tool.execute({"level": "DEBUG"})
    assert result.success is True
    assert "DEBUG" in result.llm_content
    assert result.error is None
    
    # Verify log level was actually changed
    current_level = logging.getLogger().getEffectiveLevel()
    assert current_level == logging.DEBUG
    
    # Test setting to WARNING level
    result = await tool.execute({"level": "WARNING"})
    assert result.success is True
    assert "WARNING" in result.llm_content
    assert result.error is None
    
    # Verify log level was actually changed
    current_level = logging.getLogger().getEffectiveLevel()
    assert current_level == logging.WARNING
    
    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_log_level_tool_invalid_level():
    """Test that SetLogLevelTool handles invalid log levels correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()
    
    tool = SetLogLevelTool(kernel)
    
    # Test with an invalid log level
    result = await tool.execute({"level": "INVALID"})
    assert result.success is False
    assert "Invalid log level" in result.llm_content
    assert "INVALID" in result.llm_content
    
    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_log_level_tool_missing_parameter():
    """Test that SetLogLevelTool handles missing parameters correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()
    
    tool = SetLogLevelTool(kernel)
    
    # Test with no parameters
    result = await tool.execute({})
    assert result.success is False
    assert "Missing required parameter: level" in result.llm_content
    
    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_log_level_tool_registered_in_kernel():
    """Test that SetLogLevelTool is properly registered in the kernel."""
    # Create a kernel instance that will register all tools
    kernel = GCSKernel()
    await kernel._initialize_components()
    
    # Check that the tool is registered
    tool = await kernel.registry.get_tool("set_log_level")
    assert tool is not None
    assert tool.name == "set_log_level"
    assert tool.display_name == "Set Log Level"
    
    # Verify the tool has the right parameters structure
    assert "properties" in tool.parameters
    assert "level" in tool.parameters["properties"]
    assert "enum" in tool.parameters["properties"]["level"]
    assert "required" in tool.parameters
    assert "level" in tool.parameters["required"]
    
    await kernel._cleanup_components()