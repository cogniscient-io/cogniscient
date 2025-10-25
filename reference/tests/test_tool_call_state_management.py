"""
Test suite for detailed tool call state management in AI Orchestrator.

This module tests that tool calls are properly tracked with detailed states
throughout their lifecycle, similar to Qwen Code's implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService, ToolCallStatus, ToolCallState
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class MockContentGenerator(BaseContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing tool state management.
    """
    def __init__(self, config=None):
        self.config = config or {}
        self.generate_response_calls = []
        self.process_tool_result_calls = []
    
    async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of generate_response that returns a tool call.
        """
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'tools': tools
        })
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # Return a response with a tool call for testing
        class MockToolCall:
            def __init__(self):
                self.id = "test_call_123"
                self.name = "shell_command"
                self.parameters = {"command": "echo hello"}
        
        return ResponseObj(
            content="I'll use a tool to help with that.",
            tool_calls=[MockToolCall()]
        )
    
    async def process_tool_result(self, tool_result, conversation_history=None):
        """
        Mock implementation of process_tool_result.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history
        })
        
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed: {tool_result.llm_content}")
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt}"


@pytest.mark.asyncio
async def test_tool_call_state_initialization():
    """
    Test that tool call states are properly initialized.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a mock tool call state directly
    tool_call_state = ToolCallState(
        call_id="test_123",
        tool_name="shell_command",
        parameters={"command": "echo hello"}
    )
    
    assert tool_call_state.call_id == "test_123"
    assert tool_call_state.tool_name == "shell_command"
    assert tool_call_state.parameters == {"command": "echo hello"}
    assert tool_call_state.status == ToolCallStatus.VALIDATING
    assert tool_call_state.result is None
    assert tool_call_state.error is None


@pytest.mark.asyncio
async def test_tool_call_state_management():
    """
    Test that tool call states are properly managed throughout their lifecycle.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a tool call state using the orchestrator's method
    call_id = "test_call_456"
    tool_state = orchestrator.create_tool_call_state(
        call_id=call_id,
        tool_name="shell_command",
        parameters={"command": "date"}
    )
    
    # Verify the state was created and added to active tool calls
    assert call_id in orchestrator.active_tool_calls
    assert orchestrator.active_tool_calls[call_id].status == ToolCallStatus.VALIDATING
    
    # Simulate the tool execution by updating the status to executing
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Mon Oct 24 23:45:12 UTC 2025\n",
        return_display="Mon Oct 24 23:45:12 UTC 2025\n",
        success=True
    )
    
    orchestrator.update_tool_call_status(
        call_id=call_id,
        status=ToolCallStatus.SUCCESS,
        result=tool_result
    )
    
    # Verify the state was moved to completed tool calls
    assert call_id not in orchestrator.active_tool_calls
    assert call_id in orchestrator.completed_tool_calls
    assert orchestrator.completed_tool_calls[call_id].status == ToolCallStatus.SUCCESS
    assert orchestrator.completed_tool_calls[call_id].result == tool_result


@pytest.mark.asyncio
async def test_tool_call_error_state_management():
    """
    Test that tool call states are properly managed when errors occur.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a tool call state
    call_id = "test_call_789"
    tool_state = orchestrator.create_tool_call_state(
        call_id=call_id,
        tool_name="shell_command",
        parameters={"command": "invalid_command"}
    )
    
    # Verify the state was created
    assert call_id in orchestrator.active_tool_calls
    assert orchestrator.active_tool_calls[call_id].status == ToolCallStatus.VALIDATING
    
    # Simulate an error by updating the status to error
    error_msg = "Command not found"
    orchestrator.update_tool_call_status(
        call_id=call_id,
        status=ToolCallStatus.ERROR,
        error=error_msg
    )
    
    # Verify the state was moved to completed tool calls with error
    assert call_id not in orchestrator.active_tool_calls
    assert call_id in orchestrator.completed_tool_calls
    assert orchestrator.completed_tool_calls[call_id].status == ToolCallStatus.ERROR
    assert orchestrator.completed_tool_calls[call_id].error == error_msg


@pytest.mark.asyncio
async def test_tool_call_state_with_mock_interaction():
    """
    Test tool call state management during a simulated AI interaction.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_789"
    
    # Mock the tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Hello from shell\n",
        return_display="Hello from shell\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Mock the system_context_builder
    async def mock_get_available_tools():
        return {
            "shell_command": {
                "name": "shell_command",
                "description": "Execute a shell command and return the output",
                "parameter_schema": {
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
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the orchestrator to trigger tool call processing
    response = await orchestrator.handle_ai_interaction("Get hello message")
    
    # Verify that the tool call state was managed properly
    # Check that there are no active tool calls (all should be completed)
    assert len(orchestrator.active_tool_calls) == 0
    
    # Check that there is at least one completed tool call
    assert len(orchestrator.completed_tool_calls) > 0
    
    # Get the completed tool calls
    completed_calls = orchestrator.get_completed_tool_calls()
    assert len(completed_calls) > 0
    
    # Check that the tool call has the correct state
    for call_id, call_state in completed_calls.items():
        assert call_state.status in [ToolCallStatus.SUCCESS, ToolCallStatus.ERROR]
        if call_state.status == ToolCallStatus.SUCCESS:
            assert call_state.result is not None


@pytest.mark.asyncio
async def test_multiple_tool_calls_state_management():
    """
    Test state management with multiple concurrent tool calls.
    """
    # Since our current implementation handles tool calls sequentially,
    # this test simulates the management of multiple tool calls
    
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create multiple tool call states
    for i in range(3):
        call_id = f"test_call_{i}"
        tool_state = orchestrator.create_tool_call_state(
            call_id=call_id,
            tool_name="shell_command",
            parameters={"command": f"echo test_{i}"}
        )
        
        # Verify each was created properly
        assert call_id in orchestrator.active_tool_calls
        assert orchestrator.active_tool_calls[call_id].status == ToolCallStatus.VALIDATING
    
    # Verify we have 3 active tool calls
    assert len(orchestrator.active_tool_calls) == 3
    
    # Update each to success status
    for i in range(3):
        call_id = f"test_call_{i}"
        tool_result = ToolResult(
            tool_name="shell_command",
            llm_content=f"test_{i}_output\n",
            return_display=f"test_{i}_output\n",
            success=True
        )
        
        orchestrator.update_tool_call_status(
            call_id=call_id,
            status=ToolCallStatus.SUCCESS,
            result=tool_result
        )
    
    # Verify all were moved to completed
    assert len(orchestrator.active_tool_calls) == 0
    assert len(orchestrator.completed_tool_calls) == 3
    
    # Verify all completed calls have success status
    for call_id, call_state in orchestrator.completed_tool_calls.items():
        assert call_state.status == ToolCallStatus.SUCCESS