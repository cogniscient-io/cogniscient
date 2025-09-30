"""Tests for Chat Interface Functionality with MCP Compliance."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from cogniscient.engine.orchestrator.chat_interface import ChatInterface
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator


def test_chat_interface_initialization():
    """Should initialize chat interface successfully with MCP compliance."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    orchestrator = MagicMock(spec=LLMOrchestrator)
    chat_interface = ChatInterface(orchestrator)
    assert chat_interface is not None
    assert chat_interface.orchestrator == orchestrator


def test_conversation_history():
    """Should maintain conversation history."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    orchestrator = MagicMock(spec=LLMOrchestrator)
    chat_interface = ChatInterface(orchestrator)
    
    # Add a mock to the llm_service to prevent actual API calls
    chat_interface.llm_service.generate_response = AsyncMock(return_value="Mock response")
    
    # Process a message
    import asyncio
    async def run_test():
        await chat_interface.process_user_input("Hello")
        assert len(chat_interface.conversation_history) == 2
        assert chat_interface.conversation_history[0]["role"] == "user"
        assert chat_interface.conversation_history[1]["role"] == "assistant"
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.asyncio
async def test_approval_workflow():
    """Should handle approval requests properly."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    orchestrator = MagicMock(spec=LLMOrchestrator)
    chat_interface = ChatInterface(orchestrator)
    
    # Mock the LLM service response for approval
    chat_interface.llm_service.generate_response = AsyncMock(return_value="yes")
    
    # Test approval request handling
    request = {
        "agent_name": "SampleAgentA",
        "changes": {"timeout": 60}
    }
    
    result = await chat_interface.handle_approval_request(request)
    assert result is True  # Since we mocked the response as "yes"


if __name__ == "__main__":
    pytest.main([__file__])