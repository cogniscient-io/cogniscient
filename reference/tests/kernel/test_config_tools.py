"""
Test suite for the new Config Tools functionality.
"""

import pytest
import logging
from gcs_kernel.tools.system_tools import SetConfigTool, GetConfigTool
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.kernel import GCSKernel
from common.settings import settings


@pytest.mark.asyncio
async def test_set_config_tool_initialization():
    """Test that SetConfigTool can be initialized properly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = SetConfigTool(kernel)

    assert tool.name == "set_config"
    assert tool.display_name == "Set Configuration"
    assert "configuration parameter" in tool.description.lower()

    # Check parameters structure
    assert "properties" in tool.parameters
    assert "param_name" in tool.parameters["properties"]
    assert "param_value" in tool.parameters["properties"]
    assert "required" in tool.parameters
    assert "param_name" in tool.parameters["required"]
    assert "param_value" in tool.parameters["required"]

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_get_config_tool_initialization():
    """Test that GetConfigTool can be initialized properly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = GetConfigTool(kernel)

    assert tool.name == "get_config"
    assert tool.display_name == "Get Configuration"
    assert "configuration parameter" in tool.description.lower()

    # Check parameters structure
    assert "properties" in tool.parameters
    assert "param_name" in tool.parameters["properties"]
    # param_name is not required, so it's optional

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_config_tool_log_level():
    """Test that SetConfigTool can change log level correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = SetConfigTool(kernel)

    # Test setting log level to DEBUG
    result = await tool.execute({"param_name": "log_level", "param_value": "DEBUG"})
    assert result.success is True
    assert "DEBUG" in result.llm_content
    assert result.error is None

    # Verify log level was actually changed
    current_level = logging.getLogger().getEffectiveLevel()
    assert current_level == logging.DEBUG

    # Test setting log level to WARNING
    result = await tool.execute({"param_name": "log_level", "param_value": "WARNING"})
    assert result.success is True
    assert "WARNING" in result.llm_content
    assert result.error is None

    # Verify log level was actually changed
    current_level = logging.getLogger().getEffectiveLevel()
    assert current_level == logging.WARNING

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_config_tool_max_tokens():
    """Test that SetConfigTool can change max_tokens correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = SetConfigTool(kernel)

    # Store original value
    original_max_tokens = settings.llm_max_tokens

    # Test setting max_tokens
    result = await tool.execute({"param_name": "max_tokens", "param_value": 2000})
    assert result.success is True
    assert "2000" in result.llm_content
    assert "max_tokens" in result.llm_content
    assert result.error is None

    # Verify the setting was actually changed
    assert settings.llm_max_tokens == 2000

    # Test with invalid value
    result = await tool.execute({"param_name": "max_tokens", "param_value": 50000})
    assert result.success is False
    assert "between 1 and 4096" in result.llm_content

    # Restore original value
    settings.llm_max_tokens = original_max_tokens

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_config_tool_max_context_length():
    """Test that SetConfigTool can change max_context_length correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = SetConfigTool(kernel)

    # Store original value
    original_max_context_length = settings.llm_max_context_length

    # Test setting max_context_length
    result = await tool.execute({"param_name": "max_context_length", "param_value": 32000})
    assert result.success is True
    assert "32000" in result.llm_content
    assert "max_context_length" in result.llm_content
    assert result.error is None

    # Verify the setting was actually changed
    assert settings.llm_max_context_length == 32000

    # Test with invalid value
    result = await tool.execute({"param_name": "max_context_length", "param_value": 500})
    assert result.success is False
    assert "between 1024 and 128000" in result.llm_content

    # Restore original value
    settings.llm_max_context_length = original_max_context_length

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_set_config_tool_invalid_parameters():
    """Test that SetConfigTool handles invalid parameters correctly."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = SetConfigTool(kernel)

    # Test with non-existent parameter
    result = await tool.execute({"param_name": "nonexistent_param", "param_value": "value"})
    assert result.success is False
    assert "does not exist" in result.llm_content.lower()

    # Test with missing param_name
    result = await tool.execute({"param_value": "value"})
    assert result.success is False
    assert "missing required parameter: param_name" in result.llm_content.lower()

    # Test with missing param_value
    result = await tool.execute({"param_name": "log_level"})
    assert result.success is False
    assert "missing required parameter: param_value" in result.llm_content.lower()

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_get_config_tool_functionality():
    """Test that GetConfigTool works correctly for different parameters."""
    # Create a minimal kernel instance to pass to the tool
    kernel = GCSKernel()
    await kernel._initialize_components()

    tool = GetConfigTool(kernel)

    # Test getting a specific parameter (log_level)
    result = await tool.execute({"param_name": "log_level"})
    assert result.success is True
    assert "log_level" in result.llm_content
    assert result.error is None

    # Test getting all parameters
    result = await tool.execute({})
    assert result.success is True
    assert "log_level" in result.llm_content
    assert result.error is None

    # Test getting a specific parameter (llm_max_tokens)
    result = await tool.execute({"param_name": "llm_max_tokens"})
    assert result.success is True
    assert "llm_max_tokens" in result.llm_content
    assert result.error is None

    # Test getting non-existent parameter
    result = await tool.execute({"param_name": "nonexistent_param"})
    assert result.success is False
    assert "does not exist" in result.llm_content.lower()

    await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_config_tools_registered_in_kernel():
    """Test that Config Tools are properly registered in the kernel."""
    # Create a kernel instance that will register all tools
    kernel = GCSKernel()
    await kernel._initialize_components()

    # Check that the SetConfigTool is registered
    set_tool = await kernel.registry.get_tool("set_config")
    assert set_tool is not None
    assert set_tool.name == "set_config"
    assert set_tool.display_name == "Set Configuration"

    # Check that the GetConfigTool is registered
    get_tool = await kernel.registry.get_tool("get_config")
    assert get_tool is not None
    assert get_tool.name == "get_config"
    assert get_tool.display_name == "Get Configuration"

    await kernel._cleanup_components()