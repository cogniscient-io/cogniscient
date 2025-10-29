"""
Test to verify the current tool calling behavior in the GCS Kernel system.

This test verifies how the system handles tool calls from the LLM and executes them.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


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
        llm_content="Command executed successfully",
        return_display="Command executed successfully",
        success=True
    )
    kernel_client.get_execution_result = AsyncMock(return_value=tool_result)
    
    # Create a mock system context builder that returns available tools including shell_command
    from unittest.mock import AsyncMock as AsyncMockForTest
    
    mock_system_context_builder = AsyncMockForTest()
    async def mock_get_available_tools():
        return {
            "shell_command": {
                "name": "shell_command",
                "description": "Execute a shell command and return the output",
                "parameters": {  # Using OpenAI-compatible format
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    mock_system_context_builder.get_available_tools = mock_get_available_tools

    # Create the orchestrator service
    orchestrator = AIOrchestratorService(kernel_client)
    
    # Replace the system context builder with our mock
    orchestrator.system_context_builder = mock_system_context_builder
    
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
            self.parameters = {"command": "echo hello world"}  # For compatibility

    # When generate_response is called, return a response with tool calls
    mock_content_generator.generate_response = AsyncMock(return_value=MockResponse(
        content="I'll execute a shell command for you.",
        tool_calls=[MockToolCall()]
    ))
    
    # When process_tool_result is called, return a final response
    mock_content_generator.process_tool_result = AsyncMock(return_value=MockResponse(
        content="The command was executed successfully and returned: hello world",
        tool_calls=[]
    ))
    
    orchestrator.content_generator = mock_content_generator
    
    # Test the interaction
    result = await orchestrator.handle_ai_interaction("Run a shell command to echo 'hello world'")
    
    print(f"Orchestrator result: {result}")
    
    # Verify that the tool execution was called
    kernel_client.submit_tool_execution.assert_called_once_with(
        "shell_command",
        {"command": "echo hello world"}
    )
    
    # Verify that the tool result was retrieved
    kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    print("✓ Tool calling flow test passed!")
    
    return True


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
    
    # Create a mock system context builder that returns available tools including shell_command
    from unittest.mock import AsyncMock as AsyncMockForTest
    
    mock_system_context_builder = AsyncMockForTest()
    async def mock_get_available_tools():
        return {
            "shell_command": {
                "name": "shell_command",
                "description": "Execute a shell command and return the output",
                "parameters": {  # Using OpenAI-compatible format
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    mock_system_context_builder.get_available_tools = mock_get_available_tools

    # Create the orchestrator service
    orchestrator = AIOrchestratorService(kernel_client)
    
    # Replace the system context builder with our mock
    orchestrator.system_context_builder = mock_system_context_builder
    
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
            self.parameters = {"command": "invalid_command_that_does_not_exist"}  # For compatibility

    # Mock response with a tool call
    mock_content_generator.generate_response = AsyncMock(return_value=MockResponse(
        content="I'll execute a shell command for you.",
        tool_calls=[MockToolCall()]
    ))
    
    # When process_tool_result is called for an error, return an appropriate response
    mock_content_generator.process_tool_result = AsyncMock(return_value=MockResponse(
        content="The command execution failed: Command failed with exit code 1",
        tool_calls=[]
    ))
    
    orchestrator.content_generator = mock_content_generator
    
    # Test the interaction
    result = await orchestrator.handle_ai_interaction("Run a shell command that doesn't exist")
    
    print(f"Orchestrator error result: {result}")
    
    # Verify that the tool execution was called
    kernel_client.submit_tool_execution.assert_called_once_with(
        "shell_command",
        {"command": "invalid_command_that_does_not_exist"}
    )
    
    # Verify that the tool result was retrieved
    kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    print("✓ Tool calling flow with error test passed!")
    
    return True


async def main():
    """
    Main function to run the tests.
    """
    print("Starting tool calling verification tests...\n")
    
    success1 = await test_tool_calling_flow()
    success2 = await test_tool_calling_with_error()
    
    if success1 and success2:
        print("\n✓ All tool calling verification tests passed!")
    else:
        print("\n✗ Some tests failed.")
        
    return success1 and success2


if __name__ == "__main__":
    asyncio.run(main())