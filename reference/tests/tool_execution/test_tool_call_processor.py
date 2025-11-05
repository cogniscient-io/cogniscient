#!/usr/bin/env python3
"""
Test script to verify the new tool call model and execution manager functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from gcs_kernel.tool_call_model import ToolCall
from gcs_kernel.tool_execution_manager import ToolExecutionManager


@pytest.mark.asyncio
async def test_tool_call_creation():
    """Test creating ToolCall objects."""
    # Test basic creation
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": '{"param1": "value1", "param2": 123}'
        }
    )
    
    assert tool_call.id == "call_123"
    assert tool_call.name == "test_tool"
    assert tool_call.function["name"] == "test_tool"
    assert tool_call.arguments["param1"] == "value1"
    assert tool_call.arguments["param2"] == 123
    
    # Test creation from dict arguments
    tool_call2 = ToolCall.from_dict_arguments(
        id="call_456",
        name="another_tool",
        arguments={"param1": "test", "param2": True}
    )
    
    assert tool_call2.id == "call_456"
    assert tool_call2.name == "another_tool"
    assert tool_call2.arguments["param1"] == "test"
    assert tool_call2.arguments["param2"] is True


@pytest.mark.asyncio
async def test_process_tool_calls_in_response():
    """Test processing raw tool calls from LLM response."""
    raw_tool_calls = [
        {
            "id": "call_123",
            "function": {
                "name": "test_tool",
                "arguments": '{"param1": "value1"}'
            },
            "type": "function"
        },
        {
            "id": "call_456", 
            "function": {
                "name": "another_tool",
                "arguments": '{"param2": 42}'
            },
            "type": "function"
        }
    ]
    
    # Create a ToolExecutionManager instance
    manager = ToolExecutionManager(None, None)
    content, processed_tool_calls = manager.process_tool_calls_in_response("test content", raw_tool_calls)
    
    assert content == "test content"
    assert len(processed_tool_calls) == 2
    assert processed_tool_calls[0].id == "call_123"
    assert processed_tool_calls[0].name == "test_tool"
    assert processed_tool_calls[1].id == "call_456"
    assert processed_tool_calls[1].name == "another_tool"


@pytest.mark.asyncio
async def test_execute_tool_calls_with_mcp_client():
    """Test executing tool calls with MCP client."""
    # Create mock registry that will return True for has_tool and indicate external tool
    mock_registry = AsyncMock()
    async def mock_has_tool(tool_name):
        if tool_name == "test_tool":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "test_tool":
            return "http://mcp-server:8000"  # Indicate external tool
        return None
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    mock_registry.get_mcp_client_for_tool = AsyncMock()  # This won't be called in this test path

    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    
    # Set up the mock to return success for validation and execution
    mock_mcp_client.validate_tool_schema = AsyncMock(return_value=True)
    mock_mcp_client.submit_tool_execution = AsyncMock(return_value="exec_123")
    
    # Create a mock ToolResult for the get_execution_result method
    from gcs_kernel.models import ToolResult
    mock_tool_result = ToolResult(
        tool_name="test_tool",
        llm_content="Tool executed successfully",
        return_display="Result from tool",
        success=True
    )
    
    # Mock the get_execution_result to return the mock result after a few calls
    async def mock_get_execution_result(execution_id):
        # Simulate that the execution completes on the second call
        if execution_id == "exec_123":
            return mock_tool_result
        return None
    
    mock_mcp_client.get_execution_result = mock_get_execution_result
    
    # Create tool calls to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": '{"param": "value"}'
        }
    )
    
    tool_calls = [tool_call]
    
    # Create a ToolExecutionManager instance with the mock client and registry
    manager = ToolExecutionManager(mock_registry, mock_mcp_client)
    
    # Execute the tool calls
    results = await manager.execute_tool_calls(tool_calls)
    
    # Verify the results
    assert len(results) == 1
    result = results[0]
    assert result["tool_call_id"] == "call_123"
    assert result["tool_name"] == "test_tool"
    assert result["success"] is True
    # In the new architecture, external tool execution IDs have 'external_' prefix
    assert "external_call_123" == result["execution_id"]


@pytest.mark.asyncio
async def test_execute_tool_calls_failure():
    """Test executing tool calls with MCP client when validation fails."""
    # Create mock registry that will return True for has_tool and indicate external tool
    mock_registry = AsyncMock()
    async def mock_has_tool(tool_name):
        if tool_name == "failing_tool":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "failing_tool":
            return "http://mcp-server:8000"  # Indicate external tool
        return None
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    # Mock get_mcp_client_for_tool to return the general client for this test
    async def get_mcp_client_for_tool(tool_name):
        if tool_name == "failing_tool":
            # This is for testing with the general mcp_client passed to manager
            return None
        return None
    mock_registry.get_mcp_client_for_tool = get_mcp_client_for_tool

    # Create mock MCP client where validation fails
    mock_mcp_client = AsyncMock()
    mock_mcp_client.validate_tool_schema = AsyncMock(return_value=False)
    
    # Create tool call to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "failing_tool",
            "arguments": '{"param": "value"}'
        }
    )
    
    tool_calls = [tool_call]
    
    # Create a ToolExecutionManager instance with the mock client and registry
    manager = ToolExecutionManager(mock_registry, mock_mcp_client)
    
    # Execute the tool calls
    results = await manager.execute_tool_calls(tool_calls)
    
    # Verify the results show failure
    assert len(results) == 1
    result = results[0]
    assert result["tool_call_id"] == "call_123"
    assert result["tool_name"] == "failing_tool"
    assert result["success"] is False
    assert "Invalid tool parameters" in result["result"].error


@pytest.mark.asyncio
async def test_execute_tool_calls_no_client():
    """Test executing tool calls when no MCP client can be created for registered external tool."""
    # Create mock registry that will return True for has_tool and indicate external tool
    mock_registry = AsyncMock()
    async def mock_has_tool(tool_name):
        if tool_name == "test_tool":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "test_tool":
            return "http://mcp-server:8000"  # Indicate external tool
        return None
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    # Mock get_mcp_client_for_tool to return None, simulating inability to create/connect to client
    async def get_mcp_client_for_tool(tool_name):
        if tool_name == "test_tool":
            return None  # Simulate that client cannot be created or connected
        return None
    mock_registry.get_mcp_client_for_tool = get_mcp_client_for_tool

    # Create tool call to execute
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": '{"param": "value"}'
        }
    )
    
    tool_calls = [tool_call]
    
    # Create a ToolExecutionManager instance with registry but no default client
    manager = ToolExecutionManager(mock_registry, None)
    
    # Execute the tool calls - should fail because external tool client cannot be obtained
    results = await manager.execute_tool_calls(tool_calls)
    
    # Verify the results show failure because MCP client for the tool is not available
    assert len(results) == 1
    result = results[0]
    assert result["tool_call_id"] == "call_123"
    assert result["tool_name"] == "test_tool"
    assert result["success"] is False
    assert "No MCP client available for tool" in result["result"].error


@pytest.mark.asyncio
async def test_tool_call_execute_with_manager_method():
    """Test the execute_with_manager method of ToolCall."""
    # Create a mock ToolResult
    from gcs_kernel.models import ToolResult
    mock_tool_result = ToolResult(
        tool_name="test_tool",
        llm_content="Tool executed successfully",
        return_display="Result from tool",
        success=True
    )
    
    # Create a mock registry that will return True for has_tool and indicate internal tool (no server config)
    mock_registry = AsyncMock()
    async def mock_has_tool(tool_name):
        if tool_name == "test_tool":
            return True
        return False
    mock_registry.has_tool = mock_has_tool
    async def mock_get_tool_server_config(tool_name):
        if tool_name == "test_tool":  # Return None to indicate internal tool
            return None
        return "http://other-server:8000"  # External for other tools
    mock_registry.get_tool_server_config = mock_get_tool_server_config
    
    # Create a mock ToolExecutionManager
    mock_manager = AsyncMock()
    # Ensure the mock manager has a registry attribute
    mock_manager.registry = mock_registry
    # Mock the execute_internal_tool method to return our mock result
    mock_manager.execute_internal_tool = AsyncMock(return_value=mock_tool_result)
    # Also mock execute_external_tool_via_mcp to avoid confusion (it shouldn't be called in this test)
    mock_manager.execute_external_tool_via_mcp = AsyncMock()
    
    # Create a tool call and execute it with the manager
    tool_call = ToolCall(
        id="call_123",
        function={
            "name": "test_tool",
            "arguments": '{"param": "value"}'
        }
    )
    
    result = await tool_call.execute_with_manager(mock_manager)
    
    # Verify the result
    assert result["tool_call_id"] == "call_123"
    assert result["tool_name"] == "test_tool"
    assert result["result"].success is True


if __name__ == "__main__":
    print("Running tool call model and execution manager tests...")
    
    # Run the tests
    import asyncio
    
    async def run_tests():
        await test_tool_call_creation()
        print("✓ test_tool_call_creation passed")
        
        await test_process_tool_calls_in_response()
        print("✓ test_process_tool_calls_in_response passed")
        
        await test_execute_tool_calls_with_mcp_client()
        print("✓ test_execute_tool_calls_with_mcp_client passed")
        
        await test_execute_tool_calls_failure()
        print("✓ test_execute_tool_calls_failure passed")
        
        await test_execute_tool_calls_no_client()
        print("✓ test_execute_tool_calls_no_client passed")
        
        await test_tool_call_execute_with_manager_method()
        print("✓ test_tool_call_execute_with_manager_method passed")
        
        print("\nAll tests passed! ✓")
    
    asyncio.run(run_tests())