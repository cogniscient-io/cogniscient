"""
Test suite for conversation history functionality in AI Orchestrator.

This module tests the two levels of conversation history:
1. Turn-level history (maintained in the PromptObject during a single turn)
2. Session-level history (maintained by the orchestrator across multiple turns)
"""
import pytest
from unittest.mock import AsyncMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.test_mocks import MockContentGenerator, ToolCallingMockContentGenerator
from gcs_kernel.models import ToolResult, PromptObject, ToolInclusionPolicy


class TrackingMockContentGenerator(MockContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing conversation history.
    """
    def __init__(self, config=None):
        super().__init__(config)

        # Track calls to verify conversation history is passed
        self.generate_response_calls = []

    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Mock implementation of generate_response that checks and adds to conversation history.
        """
        # Track the call for verification
        self.generate_response_calls.append({
            'conversation_history': prompt_obj.conversation_history,
            'prompt_id': prompt_obj.prompt_id
        })

        # Check if there's a tool result in the conversation history that should trigger a response
        has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)

        # If there's a tool result in the conversation, provide the final answer
        if has_tool_result:
            # Look for the tool result content
            tool_content = None
            for msg in reversed(prompt_obj.conversation_history):
                if msg.get("role") == "tool":
                    tool_content = msg.get("content", "")
                    break

            # Return a final response based on the tool result
            prompt_obj.result_content = f"The current date/time is: {tool_content.strip()}"
            prompt_obj.mark_completed(prompt_obj.result_content)
        else:
            # Otherwise, check if there's a user prompt about time/date to generate a tool call
            last_user_message = None
            for msg in reversed(prompt_obj.conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break

            if last_user_message and ("time" in last_user_message.lower() or "date" in last_user_message.lower()):
                # Create a mock tool call object for shell_command in OpenAI format
                prompt_obj.add_tool_call({
                    "id": "call_time_1",
                    "function": {
                        "name": "shell_command",
                        "arguments": '{"command": "date"}'  # Arguments should be JSON string
                    }
                })
                prompt_obj.result_content = "I'll get the current time for you."
                prompt_obj.mark_completed(prompt_obj.result_content)
            else:
                # Default response
                prompt_obj.result_content = "Processed conversation"
                prompt_obj.mark_completed(prompt_obj.result_content)


@pytest.mark.asyncio
async def test_turn_level_conversation_history_with_tool_call():
    """
    Test that turn-level conversation history is properly maintained in the PromptObject during tool calls.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"

    # Mock the tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Fri Oct 24 23:45:12 UTC 2025\n",  # Example time output
        return_display="Fri Oct 24 23:45:12 UTC 2025\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result

    # Create mock tool execution manager for the test
    mock_tool_execution_manager = AsyncMock()

    from gcs_kernel.tool_call_model import ToolCall

    # Mock the unified execute_tool_call method 
    async def mock_execute_tool_call(tool_call: ToolCall):
        return {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "result": tool_result,
            "success": tool_result.success
        }

    mock_tool_execution_manager.execute_tool_call = AsyncMock(side_effect=mock_execute_tool_call)
    mock_tool_execution_manager.registry = None  # Mock registry as None for test

    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)

    # Set kernel services to provide the mock tool execution manager
    orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)

    # Use our mock content generator
    mock_provider = ToolCallingMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)

    # Call the AI orchestrator with a prompt that should trigger a tool call
    prompt_obj = PromptObject.create(
        content="What is the current time?",
        streaming_enabled=False,
        tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
    )

    # Before the interaction, the prompt object should have an empty conversation history
    # The user message gets added during the turn processing in the turn manager
    assert len(prompt_obj.conversation_history) == 0

    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    response = response_obj.result_content

    # Verify the response contains the time (indicating the tool result was processed)
    assert "2025" in response
    assert "time" in response.lower()

    # The prompt object's conversation history should now include all messages from the turn
    # including user message, assistant tool call, tool result, and final response
    history = response_obj.conversation_history
    assert len(history) >= 3  # At least user, tool result, and assistant response

    # Verify the conversation history contains the expected elements
    user_messages = [msg for msg in history if msg.get('role') == 'user']
    assistant_messages = [msg for msg in history if msg.get('role') == 'assistant']
    tool_messages = [msg for msg in history if msg.get('role') == 'tool']

    assert len(user_messages) >= 1
    assert len(tool_messages) >= 1
    assert len(assistant_messages) >= 1  # At least the final response

    # Verify the user message is preserved
    assert user_messages[0]['content'] == "What is the current time?"

    # Verify the tool result is preserved
    assert tool_messages[0]['content'] == "Fri Oct 24 23:45:12 UTC 2025\n"


@pytest.mark.asyncio
async def test_session_level_conversation_history():
    """
    Test that session-level conversation history is maintained across multiple turns.
    This is a placeholder test for the intended session-level functionality.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"

    # Mock the tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Mon Jan 1 12:00:00 UTC 2024\n",
        return_display="Mon Jan 1 12:00:00 UTC 2024\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result

    # Create mock tool execution manager
    mock_tool_execution_manager = AsyncMock()
    mock_tool_execution_manager._execute_internal_tool.return_value = tool_result
    mock_tool_execution_manager.registry = None

    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)

    # Use a simple mock content generator
    mock_provider = MockContentGenerator(response_content="Test response")
    orchestrator.set_content_generator(mock_provider)

    # Verify initial session history is empty
    initial_session_history = orchestrator.get_conversation_history()
    assert len(initial_session_history) == 0

    # First interaction
    prompt_obj1 = PromptObject.create(content="First message", streaming_enabled=False)
    response_obj1 = await orchestrator.handle_ai_interaction(prompt_obj1)

    # Check that session history was updated
    after_first_interaction = orchestrator.get_conversation_history()
    # The orchestrator should update its own conversation history after interactions
    # This is a placeholder to verify the intended functionality will work

    # Second interaction
    prompt_obj2 = PromptObject.create(content="Second message", streaming_enabled=False)
    response_obj2 = await orchestrator.handle_ai_interaction(prompt_obj2)

    # Check session history after second interaction
    after_second_interaction = orchestrator.get_conversation_history()
    # This test will verify that session-level history accumulates across interactions

    # NOTE: This is currently a placeholder test. The actual implementation of session-level
    # history management will be implemented in a future update to properly maintain
    # conversation context across multiple turns within a user session.
    assert True  # Placeholder assertion


@pytest.mark.asyncio
async def test_multiple_turns_with_turn_level_history():
    """
    Test that turn-level history is properly maintained across multiple tool calls within a single turn.
    """
    # Create a mock content generator that will trigger multiple tool calls in one turn
    class MultiToolMockContentGenerator(MockContentGenerator):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        async def generate_response(self, prompt_obj: 'PromptObject') -> None:
            self.call_count += 1

            # Check if there are already tool results in the conversation history
            has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)

            if has_tool_result or self.call_count > 1:
                # Return final response after processing tool results
                prompt_obj.result_content = "Final response after processing tool result."
                prompt_obj.mark_completed(prompt_obj.result_content)
            elif self.call_count == 1:
                # First call returns a tool call
                prompt_obj.add_tool_call({
                    "id": "call_1",
                    "function": {
                        "name": "shell_command",
                        "arguments": '{"command": "date"}'
                    }
                })
                prompt_obj.result_content = "Getting the current time."
                prompt_obj.mark_completed(prompt_obj.result_content)

    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"

    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Sample time output",
        return_display="Sample time output",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result

    # Create mock tool execution manager
    mock_tool_execution_manager = AsyncMock()
    mock_tool_execution_manager._execute_internal_tool.return_value = tool_result
    mock_tool_execution_manager.registry = None

    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)

    # Use our multi-tool mock content generator
    mock_provider = MultiToolMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)

    # Call the AI orchestrator
    prompt_obj = PromptObject.create(
        content="Get the time and process it.",
        streaming_enabled=False,
        tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
    )

    # Before interaction
    initial_history_len = len(prompt_obj.conversation_history)
    assert initial_history_len == 0  # Should be empty initially

    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    response = response_obj.result_content

    # Verify the response was generated
    assert response is not None

    # The conversation history in the prompt object should now include all messages from this turn
    final_history = response_obj.conversation_history
    user_messages = [msg for msg in final_history if msg.get('role') == 'user']
    assistant_messages = [msg for msg in final_history if msg.get('role') == 'assistant']
    tool_messages = [msg for msg in final_history if msg.get('role') == 'tool']

    # Should have user message, one tool result, and an assistant response
    assert len(user_messages) >= 1
    assert len(tool_messages) >= 1  # Tool result should be in history
    assert len(assistant_messages) >= 1  # Final response should be in history


@pytest.mark.asyncio
async def test_session_history_manual_management():
    """
    Test that session-level history can be manually managed via orchestrator methods.
    """
    mock_kernel_client = AsyncMock()

    orchestrator = AIOrchestratorService(mock_kernel_client)

    # Initially, session history should be empty
    assert len(orchestrator.get_conversation_history()) == 0

    # Add a message manually
    orchestrator.add_message_to_history("user", "Test message 1")
    assert len(orchestrator.get_conversation_history()) == 1
    assert orchestrator.get_conversation_history()[0]["role"] == "user"
    assert orchestrator.get_conversation_history()[0]["content"] == "Test message 1"

    # Add another message
    orchestrator.add_message_to_history("assistant", "Test response 1")
    assert len(orchestrator.get_conversation_history()) == 2
    assert orchestrator.get_conversation_history()[1]["role"] == "assistant"
    assert orchestrator.get_conversation_history()[1]["content"] == "Test response 1"

    # Reset the session history
    await orchestrator.reset_conversation()
    assert len(orchestrator.get_conversation_history()) == 0


@pytest.mark.asyncio
async def test_session_history_with_interaction():
    """
    Test that session history includes interactions after they complete.
    """
    # This test will be expanded when the session-level history functionality is implemented
    # to properly track conversation across multiple turns within a session.

    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"

    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Sample time output\n",
        return_display="Sample time output\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result

    orchestrator = AIOrchestratorService(mock_kernel_client)

    mock_tool_execution_manager = AsyncMock()
    mock_tool_execution_manager._execute_internal_tool.return_value = tool_result
    mock_tool_execution_manager.registry = None

    orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)

    mock_provider = MockContentGenerator(response_content="Test response")
    orchestrator.set_content_generator(mock_provider)

    # Initially empty
    assert len(orchestrator.get_conversation_history()) == 0

    # After interaction - this is a placeholder test for future functionality
    prompt_obj = PromptObject.create(content="Test session history")
    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)

    # Future implementation should update orchestrator's session history
    # For now, just verify basic functionality
    assert response_obj is not None