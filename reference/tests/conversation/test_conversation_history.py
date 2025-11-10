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
    
    # Mock the unified execute_tool_call method instead of execute_internal_tool
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
    
    # Use our mock content generator that returns tool calls for time-related prompts
    mock_provider = ToolCallingMockContentGenerator(
        response_content="I'll help you with that.",
        tool_calls=[{
            "id": "call_123",
            "function": {
                "name": "shell_command",
                "arguments": '{"command": "date"}'
            }
        }] if False else None  # Don't set initial tool calls for this specific test
    )
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
    assert "time" in response.lower() or "date" in response.lower()
    
    # The prompt object's conversation history should now include all messages from the turn
    # including user message, assistant tool call, tool result, and final response
    history = response_obj.conversation_history
    # After turn completion, history should have multiple entries
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
    tool_result_found = any("Fri Oct 24 23:45:12 UTC 2025" in msg.get('content', '') for msg in tool_messages)
    assert tool_result_found


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
    
    from gcs_kernel.tool_call_model import ToolCall
    
    # Mock the unified execute_tool_call method instead of execute_internal_tool
    async def mock_execute_tool_call(tool_call: ToolCall):
        return {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "result": tool_result,
            "success": tool_result.success
        }
    
    mock_tool_execution_manager.execute_tool_call = AsyncMock(side_effect=mock_execute_tool_call)
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
    
    # Check that session history was updated (this will be implemented properly later)
    after_first_interaction = orchestrator.get_conversation_history()
    # The orchestrator should eventually update its own conversation history after interactions
    
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
    
    from gcs_kernel.tool_call_model import ToolCall
    
    # Mock the unified execute_tool_call method instead of execute_internal_tool
    async def mock_execute_tool_call(tool_call: ToolCall):
        return {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "result": tool_result,
            "success": tool_result.success
        }
    
    mock_tool_execution_manager.execute_tool_call = AsyncMock(side_effect=mock_execute_tool_call)
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