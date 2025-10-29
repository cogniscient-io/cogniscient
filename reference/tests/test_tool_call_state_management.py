"""
Test suite for detailed tool call state management in AI Orchestrator.

This module tests that tool calls are properly tracked with detailed states
throughout their lifecycle, similar to Qwen Code's implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult, ToolState


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
                import json
                self.arguments = self.parameters  # Use parameters directly as arguments
                self.arguments_json = json.dumps(self.parameters)
        
        return ResponseObj(
            content="I'll use a tool to help with that.",
            tool_calls=[MockToolCall()]
        )
    
    async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
        """
        Mock implementation of process_tool_result.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'available_tools': available_tools
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
    
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the orchestrator to trigger tool call processing
    response = await orchestrator.handle_ai_interaction("Get hello message")
    
    # Verify that the response was generated successfully
    assert response is not None
    assert "Error" not in response  # Ensure no error occurred during processing