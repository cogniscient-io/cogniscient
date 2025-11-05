"""
Test configuration and fixtures for turn_manager tests.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, PromptObject, ToolResult, ToolInclusionPolicy
from gcs_kernel.tool_call_model import ToolCall
from services.llm_provider.base_generator import BaseContentGenerator


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock(spec=MCPClient)
    client.config = MCPConfig(server_url="http://test-server")
    client.get_execution_result = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_content_generator():
    """Mock content generator for testing."""
    generator = AsyncMock(spec=BaseContentGenerator)
    generator.generate_response = AsyncMock()
    
    # Create a proper async generator function for streaming
    async def mock_stream_response(prompt_obj):
        # This will be replaced in individual tests
        yield "default"
    
    generator.stream_response = mock_stream_response
    return generator


@pytest.fixture
def mock_tool_execution_manager():
    """Mock tool execution manager for testing."""
    manager = AsyncMock()
    manager.execute_internal_tool = AsyncMock()
    manager.registry = AsyncMock()
    manager.registry.has_tool = AsyncMock(return_value=True)
    manager.registry.get_tool_server_config = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def sample_prompt_object():
    """Sample prompt object for testing."""
    return PromptObject(
        prompt_id="test-prompt-123",
        content="Test prompt content",
        tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
    )


@pytest.fixture
def sample_tool_call():
    """Sample tool call for testing."""
    return ToolCall(
        id="test-call-123",
        function={
            "name": "test_tool",
            "arguments": '{"param1": "value1", "param2": 123}'
        }
    )


@pytest.fixture
def sample_tool_result():
    """Sample tool result for testing."""
    return ToolResult(
        tool_name="test_tool",
        llm_content="Result from test tool",
        return_display="Result from test tool",
        success=True
    )