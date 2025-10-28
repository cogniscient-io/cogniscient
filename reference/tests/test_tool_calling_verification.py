"""
Test to verify the current tool calling behavior in the GCS Kernel system.

This test verifies how the system handles tool calls from the LLM and executes them.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.ai_orchestrator.turn_manager import TurnManager
from services.llm_provider.content_generator import LLMContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


@pytest.mark.asyncio
async def test_tool_calling_flow():
    """
    Test the complete tool calling flow from LLM response to tool execution and back.
    """
    print("Testing the complete tool calling flow...")
    
    # Create a mock MCP client
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    # Mock the kernel client methods since we're testing the flow, not actual communication
    kernel_client.submit_tool_execution = AsyncMock(return_value="exec_123")
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="hello world\n",
        return_display="Command executed successfully: hello world",
        success=True
    )
    kernel_client.get_execution_result = AsyncMock(return_value=tool_result)
    
    # Create a mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create the orchestrator service
    orchestrator = AIOrchestratorService(kernel_client, kernel=mock_kernel)
    
    # Create a mock content generator to return the tool call
    mock_content_generator = MagicMock()
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    # Create a mock ToolCall object to mimic the actual implementation
    class MockToolCall:
        def __init__(self):
            self.id = "call_123"
            self.name = "shell_command"
            self.arguments = {"command": "echo hello world"}
            self.arguments_json = '{"command": "echo hello world"}'  # Required for the new architecture

    # When generate_response is called, return a response with tool calls on first call, then final response
    call_count = 0
    def mock_generate_response(prompt, system_context=None):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # First call: return tool call response
            return MockResponse(
                content="I'll execute a shell command for you.",
                tool_calls=[MockToolCall()]
            )
        else:
            # Subsequent calls: return final response
            return MockResponse(
                content="The command was executed successfully and returned: hello world",
                tool_calls=[]
            )
    
    mock_content_generator.generate_response = AsyncMock(side_effect=mock_generate_response)
    
    orchestrator.content_generator = mock_content_generator
    
    # Create turn manager to handle the conversation flow
    turn_manager = TurnManager(kernel_client, mock_content_generator, mock_kernel)
    
    # Test the interaction using the turn manager
    result_content = ""
    async for event in turn_manager.run_turn("Run a shell command to echo 'hello world'", system_context="You are a helpful assistant."):
        if event.type == "content":
            result_content += event.value
        elif event.type == "finished":
            break
    
    print(f"Turn manager result: {result_content}")
    
    # Verify that the tool execution was called
    kernel_client.submit_tool_execution.assert_called_once_with(
        "shell_command",
        {"command": "echo hello world"}
    )
    
    # Verify that the tool result was retrieved
    kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    print("✓ Tool calling flow test passed!")
    
    assert "hello world" in result_content or "executed" in result_content.lower()


@pytest.mark.asyncio
async def test_tool_calling_with_error():
    """
    Test the tool calling flow when the tool execution results in an error.
    """
    print("\nTesting the tool calling flow with an error...")
    
    # Create a mock MCP client
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    # Mock the kernel client methods
    kernel_client.submit_tool_execution = AsyncMock(return_value="exec_123")
    
    # Simulate an error in tool execution
    error_tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Command failed with exit code 1",
        return_display="Command failed with exit code 1",
        success=False,
        error="Command failed with exit code 1"
    )
    kernel_client.get_execution_result = AsyncMock(return_value=error_tool_result)
    
    # Create a mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create the orchestrator service
    orchestrator = AIOrchestratorService(kernel_client, kernel=mock_kernel)
    
    # Create a mock content generator to return the tool call
    mock_content_generator = MagicMock()
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    # Create a mock ToolCall object to mimic the actual implementation
    class MockToolCall:
        def __init__(self):
            self.id = "call_123"
            self.name = "shell_command"
            self.arguments = {"command": "invalid_command_that_does_not_exist"}
            self.arguments_json = '{"command": "invalid_command_that_does_not_exist"}'  # Required for the new architecture

    # Mock response with a tool call
    call_count = 0
    def mock_generate_response(prompt, system_context=None):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # First call: return tool call response
            return MockResponse(
                content="I'll execute a shell command for you.",
                tool_calls=[MockToolCall()]
            )
        else:
            # Subsequent calls: return error response
            return MockResponse(
                content="The command execution failed: Command failed with exit code 1",
                tool_calls=[]
            )
    
    mock_content_generator.generate_response = AsyncMock(side_effect=mock_generate_response)
    
    orchestrator.content_generator = mock_content_generator
    
    # Create turn manager to handle the conversation flow
    turn_manager = TurnManager(kernel_client, mock_content_generator, mock_kernel)
    
    # Test the interaction using the turn manager
    result_content = ""
    async for event in turn_manager.run_turn("Run a shell command that doesn't exist", system_context="You are a helpful assistant."):
        if event.type == "content":
            result_content += event.value
        elif event.type == "finished":
            break
    
    print(f"Turn manager error result: {result_content}")
    
    # Verify that the tool execution was called
    kernel_client.submit_tool_execution.assert_called_once_with(
        "shell_command",
        {"command": "invalid_command_that_does_not_exist"}
    )
    
    # Verify that the tool result was retrieved
    kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    print("✓ Tool calling flow with error test passed!")
    
    assert "failed" in result_content.lower() or "error" in result_content.lower()


if __name__ == "__main__":
    import asyncio
    print("Starting tool calling verification tests...\n")
    
    async def run_tests():
        await test_tool_calling_flow()
        await test_tool_calling_with_error()
        print("\n✓ All tool calling verification tests passed!")
    
    asyncio.run(run_tests())