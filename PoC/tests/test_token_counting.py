"""Unit tests for token counting functionality."""

import pytest
from unittest.mock import patch, MagicMock
from cogniscient.engine.services.litellm_adapter import LiteLLMAdapter as LLMService


def test_llm_service_token_counting():
    """Should count tokens for input and output."""
    # Mock the LiteLLM token_counter function
    with patch('cogniscient.engine.services.litellm_adapter.litellm.token_counter') as mock_token_counter:
        with patch('cogniscient.engine.services.litellm_adapter.acompletion') as mock_acompletion:
            # Set up mocks
            mock_token_counter.side_effect = [15, 25]  # Input tokens, output tokens
            mock_acompletion.return_value = MagicMock()
            mock_acompletion.return_value.choices = [MagicMock()]
            mock_acompletion.return_value.choices[0].message.content = "This is a test response."
            
            # Create LLM service
            llm_service = LLMService()
            
            # Test messages
            messages = [
                {"role": "user", "content": "Hello, how are you?"}
            ]
            
            # Call the method (we need to run it in an async context)
            import asyncio
            response = asyncio.run(llm_service.generate_response(messages))
            
            # Verify token counter was called twice (once for input, once for output)
            assert mock_token_counter.call_count == 2
            
            # Verify the response
            assert response == "This is a test response."
            
            # Verify token counter was called with correct arguments
            # First call for input tokens
            mock_token_counter.assert_any_call(model=llm_service.model, messages=messages)
            # Second call for output tokens
            mock_token_counter.assert_any_call(model=llm_service.model, text="This is a test response.")


@pytest.mark.asyncio
async def test_llm_service_token_counting_async():
    """Should count tokens for input and output in async context."""
    # Mock the LiteLLM token_counter function
    with patch('cogniscient.engine.services.litellm_adapter.litellm.token_counter') as mock_token_counter:
        with patch('cogniscient.engine.services.litellm_adapter.acompletion') as mock_acompletion:
            # Set up mocks
            mock_token_counter.side_effect = [12, 18]  # Input tokens, output tokens
            mock_acompletion.return_value = MagicMock()
            mock_acompletion.return_value.choices = [MagicMock()]
            mock_acompletion.return_value.choices[0].message.content = "Async response test."
            
            # Create LLM service
            llm_service = LLMService()
            
            # Test messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count these tokens"}
            ]
            
            # Call the method
            response = await llm_service.generate_response(messages)
            
            # Verify token counter was called twice (once for input, once for output)
            assert mock_token_counter.call_count == 2
            
            # Verify the response
            assert response == "Async response test."


def test_llm_service_token_counting_with_custom_model():
    """Should count tokens using a custom model."""
    # Mock the LiteLLM token_counter function
    with patch('cogniscient.engine.services.litellm_adapter.litellm.token_counter') as mock_token_counter:
        with patch('cogniscient.engine.services.litellm_adapter.acompletion') as mock_acompletion:
            # Set up mocks
            mock_token_counter.side_effect = [20, 30]  # Input tokens, output tokens
            mock_acompletion.return_value = MagicMock()
            mock_acompletion.return_value.choices = [MagicMock()]
            mock_acompletion.return_value.choices[0].message.content = "Custom model response."
            
            # Create LLM service with a custom model
            llm_service = LLMService(model="gpt-4")
            
            # Test messages
            messages = [
                {"role": "user", "content": "Test with custom model"}
            ]
            
            # Call the method (we need to run it in an async context)
            import asyncio
            response = asyncio.run(llm_service.generate_response(messages, model="gpt-4"))
            
            # Verify the response
            assert response == "Custom model response."
            
            # Verify token counter was called with correct model
            mock_token_counter.assert_any_call(model="gpt-4", messages=messages)
            mock_token_counter.assert_any_call(model="gpt-4", text="Custom model response.")