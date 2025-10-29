"""
Test to verify the current tool calling behavior in the GCS Kernel system.

This test verifies how the system handles tool calls from the LLM and executes them.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult


@pytest.mark.asyncio
async def test_tool_calling_flow():
    """
    Test the complete tool calling flow from LLM response to tool execution and back.
    """
    # Create a mock MCP client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    # Mock tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Fri Oct 25 10:30:45 UTC 2025\n",
        return_display="Fri Oct 25 10:30:45 UTC 2025\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result

    # Create the orchestrator service
    orchestrator = AIOrchestratorService(mock_kernel_client)

    # Mock the system context builder to return available tools
    async def mock_get_available_tools():
        return {
            "shell_command": {
                "name": "shell_command",
                "description": "Execute a shell command and return the output",
                "parameter_schema": {  # External API format from system
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
    
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools

    # Create a mock content generator
    mock_content_generator = MagicMock()
    
    # Create a mock ToolCall object
    class MockToolCall:
        def __init__(self):
            self.id = "call_123"
            self.name = "shell_command"
            self.arguments = {"command": "date"}
            self.arguments_json = '{"command": "date"}'
    
    # Create response object for tool call
    class MockResponse:
        def __init__(self, content="", tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    # When generate_response is called, return a response with tool calls
    mock_content_generator.generate_response = AsyncMock(
        return_value=MockResponse(
            content="I'll get the current date for you.",
            tool_calls=[MockToolCall()]
        )
    )
    
    # When process_tool_result is called, return a final response
    mock_content_generator.process_tool_result = AsyncMock(
        return_value=MockResponse(
            content="The current date is: Fri Oct 25 10:30:45 UTC 2025"
        )
    )
    
    orchestrator.set_content_generator(mock_content_generator)

    # Test the interaction
    result = await orchestrator.handle_ai_interaction("What is the current date?")

    # Verify that the tool execution was called with correct parameters
    mock_kernel_client.submit_tool_execution.assert_called_once()
    
    # Verify that the tool result was retrieved
    mock_kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    # Verify that we got a proper response
    assert "date" in result.lower()


@pytest.mark.asyncio
async def test_tool_calling_with_error():
    """
    Test the tool calling flow when the tool execution results in an error.
    """
    # Create a mock MCP client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    # Simulate an error in tool execution
    error_tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Command failed: Command not found",
        return_display="Command failed: Command not found",
        success=False,
        error="Command not found"
    )
    mock_kernel_client.get_execution_result.return_value = error_tool_result

    # Create the orchestrator service
    orchestrator = AIOrchestratorService(mock_kernel_client)

    # Mock the system context builder to return available tools
    async def mock_get_available_tools():
        return {
            "shell_command": {
                "name": "shell_command",
                "description": "Execute a shell command and return the output",
                "parameter_schema": {  # External API format from system
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
    
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools

    # Create a mock content generator
    mock_content_generator = MagicMock()
    
    # Create a mock ToolCall object for an invalid command
    class MockToolCall:
        def __init__(self):
            self.id = "call_456"
            self.name = "shell_command"
            self.arguments = {"command": "invalid_command"}
            self.arguments_json = '{"command": "invalid_command"}'
    
    # Create response object for tool call
    class MockResponse:
        def __init__(self, content="", tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    # When generate_response is called, return a response with tool calls
    mock_content_generator.generate_response = AsyncMock(
        return_value=MockResponse(
            content="I'll execute a command for you.",
            tool_calls=[MockToolCall()]
        )
    )
    
    # When process_tool_result is called for an error, return an appropriate response
    mock_content_generator.process_tool_result = AsyncMock(
        return_value=MockResponse(
            content="The command execution failed: Command not found"
        )
    )
    
    orchestrator.set_content_generator(mock_content_generator)

    # Test the interaction
    result = await orchestrator.handle_ai_interaction("Run an invalid command")

    # Verify that the tool execution was called
    mock_kernel_client.submit_tool_execution.assert_called_once()
    
    # Verify that the tool result was retrieved
    mock_kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    # Verify that the error was handled appropriately
    assert "failed" in result.lower() or "error" in result.lower()