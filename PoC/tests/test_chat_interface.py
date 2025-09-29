"""Unit tests for chat interface functionality."""

import pytest
from unittest.mock import patch
from unittest.mock import AsyncMock
from cogniscient.engine.orchestrator.chat_interface import ChatInterface
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.gcs_runtime import GCSRuntime


def test_chat_interface_initialization():
    """Should initialize chat interface successfully."""
    orchestrator = LLMOrchestrator(GCSRuntime())
    chat_interface = ChatInterface(orchestrator, max_history_length=20, compression_threshold=15)
    assert chat_interface is not None
    assert chat_interface.orchestrator == orchestrator


@pytest.mark.asyncio
async def test_user_input_processing():
    """Should process user input and generate response."""
    from unittest.mock import AsyncMock
    ucs_runtime = GCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator, max_history_length=20, compression_threshold=15)
    
    # Mock the orchestrator's process_user_request method instead
    with patch.object(orchestrator, 'process_user_request', new=AsyncMock(return_value={'response': 'Hello! How can I help you?', 'token_counts': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}})) as mock_process:
        user_input = "Hello, how are you?"
        response = await chat_interface.process_user_input(user_input)
        
        # Verify orchestrator was called with the correct parameters
        mock_process.assert_called_once_with(user_input, chat_interface.conversation_history)
        
        # Verify response structure
        assert isinstance(response, dict)
        assert "response" in response
        assert response["response"] == 'Hello! How can I help you?'
        
        # Verify conversation history
        assert len(chat_interface.conversation_history) == 2
        assert chat_interface.conversation_history[0]["role"] == "user"
        assert chat_interface.conversation_history[0]["content"] == user_input
        assert chat_interface.conversation_history[1]["role"] == "assistant"
        assert "Hello! How can I help you?" in chat_interface.conversation_history[1]["content"]


@pytest.mark.asyncio
async def test_approval_request_handling():
    """Should handle approval requests from the orchestrator."""
    orchestrator = LLMOrchestrator(GCSRuntime())
    chat_interface = ChatInterface(orchestrator, max_history_length=20, compression_threshold=15)
    
    # Test approval request
    request = {"agent": "SampleAgentA", "changes": {"timeout": 50}}
    result = await chat_interface.handle_approval_request(request)
    
    # For this implementation, should return False
    assert not result