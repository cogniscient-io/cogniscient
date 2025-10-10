"""Unit tests for token counting functionality through ContextualLLMService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService


@pytest.mark.asyncio
async def test_contextual_llm_service_token_counting():
    """Should count tokens for input and output through the contextual service."""
    # Create a mock provider manager that returns token-aware responses
    mock_provider = AsyncMock()
    
    # Mock the response with token counts
    expected_response = {
        "response": "This is a test response.",
        "token_counts": {
            "input_tokens": 15,
            "output_tokens": 25,
            "total_tokens": 40
        }
    }
    
    # Set up the mock to return our expected response
    mock_provider.generate_response.return_value = expected_response
    
    # Create contextual LLM service with the mock provider
    contextual_service = ContextualLLMService(provider_manager=mock_provider)
    
    # Test with return_token_counts=True
    result = await contextual_service.generate_response(
        prompt="Hello, how are you?",
        return_token_counts=True
    )
    
    # Verify that the result includes token counts
    assert isinstance(result, dict)
    assert "response" in result
    assert "token_counts" in result
    assert result["token_counts"]["input_tokens"] == 15
    assert result["token_counts"]["output_tokens"] == 25
    assert result["token_counts"]["total_tokens"] == 40
    assert result["response"] == "This is a test response."
    
    # Verify the provider was called correctly
    mock_provider.generate_response.assert_called_once()
    
    # Check that the call was made with messages (the prompt is converted internally)
    call_args = mock_provider.generate_response.call_args
    assert call_args is not None
    assert "messages" in call_args.kwargs


@pytest.mark.asyncio 
async def test_contextual_llm_service_token_counting_async():
    """Should count tokens for input and output in async context through the contextual service."""
    # Create a mock provider manager
    mock_provider = AsyncMock()
    
    # Mock response data
    expected_response = {
        "response": "Async response test.",
        "token_counts": {
            "input_tokens": 12,
            "output_tokens": 18,
            "total_tokens": 30
        }
    }
    
    # Set up the mock
    mock_provider.generate_response.return_value = expected_response
    
    # Create contextual LLM service
    contextual_service = ContextualLLMService(provider_manager=mock_provider)
    
    # Test with domain context
    result = await contextual_service.generate_response(
        prompt="Count these tokens",
        domain="General",
        return_token_counts=True
    )
    
    # Verify the result includes token counts
    assert isinstance(result, dict)
    assert "response" in result
    assert "token_counts" in result
    assert result["token_counts"]["input_tokens"] == 12
    assert result["token_counts"]["output_tokens"] == 18
    assert result["token_counts"]["total_tokens"] == 30
    assert result["response"] == "Async response test."
    
    # Verify the provider was called
    mock_provider.generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_contextual_llm_service_token_counting_with_custom_model():
    """Should count tokens using a custom model through the contextual service."""
    # Create a mock provider manager
    mock_provider = AsyncMock()
    
    # Mock response with custom model
    expected_response = {
        "response": "Custom model response.",
        "token_counts": {
            "input_tokens": 20,
            "output_tokens": 30,
            "total_tokens": 50
        }
    }
    
    # Set up the mock
    mock_provider.generate_response.return_value = expected_response
    
    # Create contextual LLM service
    contextual_service = ContextualLLMService(provider_manager=mock_provider)
    
    # Test with custom model
    result = await contextual_service.generate_response(
        prompt="Test with custom model",
        model="gpt-4",
        return_token_counts=True
    )
    
    # Verify the result
    assert isinstance(result, dict)
    assert "response" in result
    assert "token_counts" in result
    assert result["token_counts"]["input_tokens"] == 20
    assert result["token_counts"]["output_tokens"] == 30
    assert result["token_counts"]["total_tokens"] == 50
    assert result["response"] == "Custom model response."
    
    # Verify the provider was called with the custom model
    mock_provider.generate_response.assert_called_once()
    call_args = mock_provider.generate_response.call_args
    assert call_args.kwargs.get("model") == "gpt-4"