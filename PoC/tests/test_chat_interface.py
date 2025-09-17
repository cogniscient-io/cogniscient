"""Tests for the Chat Interface."""

import pytest
from unittest.mock import AsyncMock, patch
from src.orchestrator.chat_interface import ChatInterface
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.ucs_runtime import UCSRuntime


def test_chat_interface_initialization():
    """Should initialize chat interface successfully."""
    orchestrator = LLMOrchestrator(UCSRuntime())
    chat_interface = ChatInterface(orchestrator)
    assert chat_interface is not None
    assert chat_interface.orchestrator == orchestrator


@pytest.mark.asyncio
async def test_user_input_processing():
    """Should process user input and generate response."""
    orchestrator = LLMOrchestrator(UCSRuntime())
    chat_interface = ChatInterface(orchestrator)
    
    # Mock LLM service
    with patch.object(chat_interface.llm_service, 'generate_response', new=AsyncMock(return_value='Hello! How can I help you?')) as mock_generate:
        user_input = "Hello, how are you?"
        response = await chat_interface.process_user_input(user_input)
        
        # Verify LLM service was called
        mock_generate.assert_called_once_with(user_input)
        
        # Verify response
        assert isinstance(response, str)
        assert len(response) > 0
        assert response == 'Hello! How can I help you?'
        
        # Verify conversation history
        assert len(chat_interface.conversation_history) == 2
        assert chat_interface.conversation_history[0]["role"] == "user"
        assert chat_interface.conversation_history[0]["content"] == user_input
        assert chat_interface.conversation_history[1]["role"] == "assistant"
        assert chat_interface.conversation_history[1]["content"] == response


@pytest.mark.asyncio
async def test_approval_request_handling():
    """Should handle approval requests from the orchestrator."""
    orchestrator = LLMOrchestrator(UCSRuntime())
    chat_interface = ChatInterface(orchestrator)
    
    # Test approval request
    request = {"agent": "SampleAgentA", "changes": {"timeout": 50}}
    result = await chat_interface.handle_approval_request(request)
    
    # For this implementation, should return False
    assert not result