"""
Test to verify the current tool calling behavior in the GCS Kernel system.

This test verifies how the ToolExecutionManager handles tool calls from LLM responses and executes them.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from gcs_kernel.tool_call_model import ToolCall
from gcs_kernel.tool_execution_manager import ToolExecutionManager
from gcs_kernel.models import ToolDefinition, ToolApprovalMode, ToolResult
from gcs_kernel.registry import ToolRegistry


@pytest.mark.asyncio
async def test_tool_calling_flow():
    """
    Test the complete tool calling flow using ToolExecutionManager to execute tool calls from LLM.
    """
    # Create a mock MCP client for external tools
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution.return_value = "exec_123"
    
    # Mock the tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Fri Oct 25 10:30:45 UTC 2025\n",
        return_display="Fri Oct 25 10:30:45 UTC 2025\n",
        success=True
    )
    mock_mcp_client.get_execution_result.return_value = tool_result

    # Create a mock registry with proper mocking for tool existence
    mock_registry = AsyncMock()
    
    # Mock that the shell_command tool exists
    async def mock_has_tool(tool_name):
        if tool_name == "shell_command":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    
    # Mock that the shell_command tool is an external tool (needs MCP)
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "shell_command":
            return "http://mcp-server:8000"  # Indicate external tool
        return None
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    # Mock that there's no specific client for this tool, causing it to use the default client
    async def mock_get_mcp_client_for_tool(tool_name):
        return None  # Use default client
    mock_registry.get_mcp_client_for_tool = mock_get_mcp_client_for_tool
    
    # Create the ToolExecutionManager
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object as would be returned by the LLM using the factory method
    tool_call = ToolCall.from_dict_arguments(
        id="call_123",
        name="shell_command",
        arguments={"command": "date"}
    )
    
    # Execute the tool call using the manager
    results = await manager.execute_tool_calls([tool_call])
    
    # Verify that the tool execution was called with correct parameters
    mock_mcp_client.submit_tool_execution.assert_called_once()
    
    # Verify that the tool result was retrieved
    mock_mcp_client.get_execution_result.assert_called_once_with("exec_123")
    
    # Verify that we got proper results
    assert len(results) == 1
    assert results[0]["tool_call_id"] == "call_123"
    assert results[0]["tool_name"] == "shell_command"
    assert results[0]["success"] is True
    # Check for a substring that's in the mock result
    assert "oct" in results[0]["result"].llm_content.lower()


@pytest.mark.asyncio
async def test_tool_calling_with_error():
    """
    Test the tool calling flow when the tool execution results in an error.
    """
    # Create a mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.submit_tool_execution.return_value = "exec_123"
    
    # Simulate an error in tool execution
    error_tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Command failed: Command not found",
        return_display="Command failed: Command not found",
        success=False,
        error="Command not found"
    )
    mock_mcp_client.get_execution_result.return_value = error_tool_result

    # Create a mock registry with proper mocking for tool existence
    mock_registry = AsyncMock()
    
    # Mock that the shell_command tool exists
    async def mock_has_tool(tool_name):
        if tool_name == "shell_command":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    
    # Mock that the shell_command tool is an external tool (needs MCP)
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "shell_command":
            return "http://mcp-server:8000"  # Indicate external tool
        return None
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    # Mock that there's no specific client for this tool, causing it to use the default client
    async def mock_get_mcp_client_for_tool(tool_name):
        return None  # Use default client
    mock_registry.get_mcp_client_for_tool = mock_get_mcp_client_for_tool
    
    # Create the ToolExecutionManager
    manager = ToolExecutionManager(kernel_registry=mock_registry, mcp_client=mock_mcp_client)

    # Create a ToolCall object that will fail
    tool_call = ToolCall.from_dict_arguments(
        id="call_456",
        name="shell_command",
        arguments={"command": "invalid_command"}
    )
    
    # Execute the tool call using the manager
    results = await manager.execute_tool_calls([tool_call])
    
    # Verify that the tool execution was called
    mock_mcp_client.submit_tool_execution.assert_called_once()
    
    # Verify that the tool result was retrieved
    mock_mcp_client.get_execution_result.assert_called_once_with("exec_123")
    
    # Verify that the error was handled appropriately
    assert len(results) == 1
    assert results[0]["tool_call_id"] == "call_456"
    assert results[0]["tool_name"] == "shell_command"
    assert results[0]["success"] is False
    assert "failed" in results[0]["result"].llm_content.lower() or "error" in results[0]["result"].llm_content.lower()