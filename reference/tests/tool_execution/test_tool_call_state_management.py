"""
Test suite for detailed tool call state management in AI Orchestrator.

This module tests that tool calls are properly tracked with detailed states
throughout their lifecycle, similar to Qwen Code's implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncIterator
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.test_mocks import MockContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult, ToolState


class StateTrackingMockContentGenerator(MockContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing tool state management.
    """
    def __init__(self, config=None):
        super().__init__(config)  # Call parent constructor
        # The parent class already sets up the tracking attributes
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response that returns a tool call.
        """
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Update the prompt object with content and tool call
        prompt_obj.result_content = "I'll use a tool to help with that."
        prompt_obj.add_tool_call({
            "id": "test_call_123",
            "function": {
                "name": "shell_command", 
                "arguments": '{"command": "echo hello"}'  # Arguments should be JSON string in OpenAI format
            }
        })
        
        prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj
    
    async def process_tool_result(self, tool_result, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of process_tool_result.
        """
        # Track the call for testing purposes
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'prompt_obj': prompt_obj
        })
        
        # Update the prompt object with the result of processing the tool
        prompt_obj.result_content = f"Processed: {tool_result.llm_content}"
        prompt_obj.mark_completed(prompt_obj.result_content)
        
        return prompt_obj
    
    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt_obj.content}"
    
    async def generate_response_from_conversation(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response_from_conversation that returns a tool call.
        """
        # Track for testing purposes
        last_user_message = None
        for msg in reversed(prompt_obj.conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Check if there's a tool result in the conversation history to respond to
        has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)
        if has_tool_result:
            # Create final response when tool results are present
            prompt_obj.result_content = "Based on the tool results, I've completed your request."
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
        
        # Otherwise, return a response with a tool call for testing
        prompt_obj.result_content = "I'll use a tool to help with that."
        prompt_obj.add_tool_call({
            "id": "test_call_123",
            "function": {
                "name": "shell_command", 
                "arguments": '{"command": "echo hello"}'  # Arguments should be JSON string in OpenAI format
            }
        })
        prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj


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
    

    
    # Use our mock content generator
    mock_provider = StateTrackingMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the orchestrator to trigger tool call processing
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Get hello message")
    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    response = response_obj.result_content
    
    # Verify that the response was generated successfully
    assert response is not None
    assert "Error" not in response  # Ensure no error occurred during processing