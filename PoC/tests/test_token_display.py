"""Unit tests for token display functionality and validation."""

from unittest.mock import MagicMock, patch
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter as LLMService
from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface
from cogniscient.engine.gcs_runtime import GCSRuntime
import pytest


@pytest.mark.asyncio
async def test_llm_service_returns_token_counts():
    """Test that LLM service properly returns token counts when requested."""
    llm_service = LLMService()
    
    # Mock the acompletion function to avoid actual API calls
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! How can I assist you today?"
    
    # Mock the token_counter function separately
    with patch('cogniscient.llm.providers.litellm_adapter.litellm.token_counter') as mock_token_counter, \
         patch('cogniscient.llm.providers.litellm_adapter.acompletion', return_value=mock_response):
        
        mock_token_counter.side_effect = [15, 25]  # Input tokens, output tokens
        
        # Test with return_token_counts=True
        result = await llm_service.generate_response(
            messages=[{"role": "user", "content": "Hello"}],
            return_token_counts=True
        )
        
        # Verify the result is a dict with expected structure
        assert isinstance(result, dict)
        assert "response" in result
        assert "token_counts" in result
        assert result["token_counts"]["input_tokens"] == 15
        assert result["token_counts"]["output_tokens"] == 25
        assert result["token_counts"]["total_tokens"] == 40
        
        # Verify token counter was called twice (once for input, once for output)
        assert mock_token_counter.call_count == 2


@pytest.mark.asyncio
async def test_contextual_llm_service_passes_through_token_counts():
    """Test that Contextual LLM service passes through token counts."""
    from unittest.mock import AsyncMock
    
    # Create a mock LLM service with the same mocking
    mock_llm_service = AsyncMock()
    
    # Mock the response
    mock_response = {"response": "Hello from contextual service!", "token_counts": {"input_tokens": 12, "output_tokens": 18, "total_tokens": 30}}
    
    # Set up the mock to return our expected response when generate_response is called
    mock_llm_service.generate_response.return_value = mock_response
    
    contextual_service = ContextualLLMService(mock_llm_service)
    
    # Test with return_token_counts=True
    result = await contextual_service.generate_response(
        prompt="Hello",
        return_token_counts=True
    )
    
    # Verify the result is a dict with expected structure
    assert isinstance(result, dict)
    assert "response" in result
    assert "token_counts" in result
    assert result["token_counts"]["input_tokens"] == 12
    assert result["token_counts"]["output_tokens"] == 18
    assert result["token_counts"]["total_tokens"] == 30
    
    # Verify the mock was called correctly
    mock_llm_service.generate_response.assert_called()


@pytest.mark.asyncio
async def test_chat_interface_formats_token_counts():
    """Test that chat interface properly formats responses with token counts."""
    from unittest.mock import AsyncMock
    
    # Initialize full system stack
    ucs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    ucs_runtime.load_all_agents()
    
    # Create a mock orchestrator that returns a result with token counts
    mock_orchestrator = AsyncMock()
    mock_result = {
        "response": "This is a test response.",
        "token_counts": {
            "input_tokens": 560,
            "output_tokens": 22,
            "total_tokens": 582
        }
    }
    # Mock the process_user_request method to simulate streaming behavior
    async def mock_process_user_request(user_input, conversation_history, send_stream_event):
        # Simulate sending events like the real implementation would
        await send_stream_event("assistant_response", "This is a test response.", None)
        await send_stream_event("token_counts", None, {
            "input_tokens": 560,
            "output_tokens": 22,
            "total_tokens": 582
        })
        await send_stream_event("final_response", None, {
            "conversation_history": conversation_history + [{"role": "assistant", "content": "This is a test response."}]
        })
        return mock_result
    
    mock_orchestrator.process_user_request.side_effect = mock_process_user_request
    
    chat_interface = ChatInterface(mock_orchestrator, max_history_length=20, compression_threshold=15)
    
    # Process user input with streaming
    events_collected = []
    
    async def mock_send_stream_event(event_type: str, content: str = None, data: dict = None):
        event = {
            "type": event_type,
            "content": content,
            "data": data
        }
        events_collected.append(event)
    
    result = await chat_interface.process_user_input_streaming("What is your name?", chat_interface.conversation_history, mock_send_stream_event)
    
    # Verify result contains token counts
    assert "token_counts" in result
    token_counts = result["token_counts"]
    assert token_counts["input_tokens"] == 560
    assert token_counts["output_tokens"] == 22
    assert token_counts["total_tokens"] == 582
    
    # Verify the formatted response with tokens is included
    assert "response_with_tokens" in result
    assert "[Token Usage: Input: 560, Output: 22, Total: 582]" in result["response_with_tokens"]
    
    # Verify the conversation history includes the response with token counts
    assistant_msg = next(
        msg for msg in chat_interface.conversation_history 
        if msg["role"] == "assistant"
    )
    assert "[Token Usage: Input: 560, Output: 22, Total: 582]" in assistant_msg["content"]
    
    # Verify the mock was called correctly
    mock_orchestrator.process_user_request.assert_called()


@pytest.mark.asyncio
async def test_chat_interface_handles_result_without_token_counts():
    """Test that chat interface properly handles results without token counts."""
    from unittest.mock import AsyncMock
    
    # Initialize full system stack
    ucs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    ucs_runtime.load_all_agents()
    
    # Create a mock orchestrator that returns a result without token counts
    mock_orchestrator = AsyncMock()
    mock_result = {
        "response": "This is a test response without token counts.",
        # Note: no token_counts in this result
    }
    # Mock the process_user_request method to simulate streaming behavior without token counts
    async def mock_process_user_request_no_tokens(user_input, conversation_history, send_stream_event):
        # Simulate sending events like the real implementation would (without token counts)
        await send_stream_event("assistant_response", "This is a test response without token counts.", None)
        await send_stream_event("final_response", None, {
            "conversation_history": conversation_history + [{"role": "assistant", "content": "This is a test response without token counts."}]
        })
        return mock_result
    
    mock_orchestrator.process_user_request.side_effect = mock_process_user_request_no_tokens
    
    chat_interface = ChatInterface(mock_orchestrator, max_history_length=20, compression_threshold=15)


if __name__ == "__main__":
    pytest.main([__file__])