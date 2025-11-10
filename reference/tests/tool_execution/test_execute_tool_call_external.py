#!/usr/bin/env python3
"""
Test script for testing external tool execution via the execute_tool_call public interface in ToolExecutionManager.
This tests the public interface that handles both internal and external tool execution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import json

from gcs_kernel.models import ToolResult
from gcs_kernel.tool_execution_manager import ToolExecutionManager
from gcs_kernel.tool_call_model import ToolCall


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_success():
    """Test successful execution of an external tool via the execute_tool_call public interface."""
    # Create a mock MCP client first
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")

    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=mock_mcp_client)  # Return the mock client

    # Create a mock result that will be returned after the first call, None for others
    async def mock_get_execution_result(execution_id):
        if execution_id == "exec_123":
            return ToolResult(
                tool_name="test_tool",
                success=True,
                llm_content="Test tool executed successfully",
                return_display="Test tool executed successfully"
            )
        return None

    mock_mcp_client.get_execution_result = mock_get_execution_result

    # Create the ToolExecutionManager with registry and default client
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions
    assert result["success"] is True
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is True
    assert "Test tool executed successfully" in result["result"].llm_content
    assert "Test tool executed successfully" in result["result"].return_display

    # Verify the client methods were called as expected
    mock_mcp_client.submit_tool_execution.assert_called_once_with("test_tool", {"input": "test"})


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_success_without_validation():
    """Test that execute_tool_call succeeds for external tools (no validation in MCP world)."""
    # Create a mock MCP client that returns a successful result
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")
    mock_mcp_client.get_execution_result = AsyncMock(return_value={
        "output": "Test tool executed successfully",
        "isError": False
    })

    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=mock_mcp_client)  # Return the mock client

    # Create the ToolExecutionManager with registry and client
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions - now it should succeed (no validation in MCP world)
    assert result["success"] is True
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is True
    assert "Test tool executed successfully" in result["result"].llm_content

    # Verify the client methods were called as expected
    mock_mcp_client.submit_tool_execution.assert_called_once_with("test_tool", {"input": "test"})


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_timeout():
    """Test that execute_tool_call returns a timeout error when polling fails for external tools."""
    # Create a mock MCP client first
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")

    # Mock get_execution_result to always return None (simulating timeout)
    mock_mcp_client.get_execution_result = AsyncMock(return_value=None)

    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=mock_mcp_client)  # Return the mock client

    # Create the ToolExecutionManager
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions
    assert result["success"] is False
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is False
    assert "Tool execution timed out" in result["result"].error
    assert "Tool execution timed out" in result["result"].llm_content


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_exception():
    """Test that execute_tool_call handles exceptions properly for external tools."""
    # Create a mock MCP client that raises an exception during submit_tool_execution
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution.side_effect = Exception("Connection failed")

    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=mock_mcp_client)  # Return the mock client

    # Create the ToolExecutionManager
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions
    assert result["success"] is False
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is False
    assert "Connection failed" in result["result"].error
    assert "Tool execution failed: Connection failed" in result["result"].llm_content


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_no_client():
    """Test that execute_tool_call returns an error when no MCP client is available for registered external tool."""
    # Create a mock registry that will return True for has_tool and indicate external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicate external tool
    # Mock get_mcp_client_for_tool to return None, simulating inability to create/connect to client
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=None)

    # Create the ToolExecutionManager with registry but no default client
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=None)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call - should fail because external tool client cannot be obtained
    result = await manager.execute_tool_call(tool_call)

    # Verify the result shows failure because MCP client for the tool is not available
    assert result["success"] is False
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is False
    assert "No MCP client available for tool" in result["result"].error


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_with_non_toolresult_return():
    """Test handling when the execution result is not a ToolResult object for external tools."""
    # Create a mock MCP client first
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")

    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=mock_mcp_client)  # Return the mock client

    # Mock get_execution_result to return a string instead of a ToolResult
    async def mock_get_execution_result(execution_id):
        if execution_id == "exec_123":
            return "Raw execution result string"  # Not a ToolResult object
        return None

    mock_mcp_client.get_execution_result = mock_get_execution_result

    # Create the ToolExecutionManager
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions
    assert result["success"] is True
    assert result["result"].llm_content == "Raw execution result string"
    assert result["result"].return_display == "Raw execution result string"


@pytest.mark.asyncio
async def test_execute_tool_call_external_tool_fallback_to_default_client():
    """Test that external tools use the default client if no specific client is available."""
    # Create a mock registry that indicates this is an external tool
    mock_registry = AsyncMock()
    mock_registry.has_tool = AsyncMock(return_value=True)
    mock_registry.get_tool_server_config = AsyncMock(return_value="http://mcp-server:8000")  # Indicates external tool
    mock_registry.get_mcp_client_for_tool = AsyncMock(return_value=None)  # No specific client, should use default

    # Create a mock default MCP client
    mock_default_mcp_client = AsyncMock()
    mock_default_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")

    async def mock_get_execution_result(execution_id):
        if execution_id == "exec_123":
            return ToolResult(
                tool_name="test_tool",
                success=True,
                llm_content="Test tool executed with default client",
                return_display="Test tool executed with default client"
            )
        return None

    mock_default_mcp_client.get_execution_result = mock_get_execution_result

    # Create the ToolExecutionManager with the default client
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_default_mcp_client)

    # Create a ToolCall object to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": json.dumps({"input": "test"})
        }
    )

    # Execute the tool call through the public interface
    result = await manager.execute_tool_call(tool_call)

    # Assertions
    assert result["success"] is True
    assert result["tool_name"] == "test_tool"
    assert result["tool_call_id"] == "call_123"
    assert result["result"].success is True
    assert "Test tool executed with default client" in result["result"].llm_content
    assert "Test tool executed with default client" in result["result"].return_display

    # Verify the default client methods were called as expected
    mock_default_mcp_client.submit_tool_execution.assert_called_once_with("test_tool", {"input": "test"})


if __name__ == "__main__":
    print("Running tests for execute_tool_call public interface with external tools...")

    # Run the tests
    import asyncio

    async def run_tests():
        await test_execute_tool_call_external_tool_success()
        print("✓ test_execute_tool_call_external_tool_success passed")

        await test_execute_tool_call_external_tool_validation_failure()
        print("✓ test_execute_tool_call_external_tool_validation_failure passed")

        await test_execute_tool_call_external_tool_timeout()
        print("✓ test_execute_tool_call_external_tool_timeout passed")

        await test_execute_tool_call_external_tool_exception()
        print("✓ test_execute_tool_call_external_tool_exception passed")

        await test_execute_tool_call_external_tool_no_client()
        print("✓ test_execute_tool_call_external_tool_no_client passed")

        await test_execute_tool_call_external_tool_with_non_toolresult_return()
        print("✓ test_execute_tool_call_external_tool_with_non_toolresult_return passed")

        await test_execute_tool_call_external_tool_fallback_to_default_client()
        print("✓ test_execute_tool_call_external_tool_fallback_to_default_client passed")

        print("\nAll tests passed! 🎉")

    asyncio.run(run_tests())