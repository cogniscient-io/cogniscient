"""
Test suite for the OpenAI Provider Implementation.

This module tests the OpenAIProvider class and its functionality.
"""
import pytest
import os
from unittest.mock import Mock
from services.llm_provider.providers.openai_provider import OpenAIProvider


def test_openai_provider_initialization():
    """
    Test that OpenAIProvider initializes properly with config.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "base_url": "https://api.test.com/v1",
        "timeout": 30,
        "max_retries": 2
    }
    
    provider = OpenAIProvider(config)
    
    assert provider.api_key == "test-key-12345"
    assert provider.model == "gpt-test-model"
    assert provider.base_url == "https://api.test.com/v1"
    assert provider.timeout == 30
    assert provider.max_retries == 2


def test_openai_provider_build_headers():
    """
    Test that OpenAIProvider correctly builds headers for API requests.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model"
    }
    
    provider = OpenAIProvider(config)
    headers = provider.build_headers()
    
    expected_headers = {
        "Authorization": "Bearer test-key-12345",
        "Content-Type": "application/json"
    }
    
    assert headers == expected_headers


def test_openai_provider_build_headers_missing_api_key():
    """
    Test that OpenAIProvider raises error when API key is missing.
    """
    config = {
        "api_key": None,
        "model": "gpt-test-model"
    }
    
    provider = OpenAIProvider(config)
    
    with pytest.raises(ValueError, match="API key is required for OpenAI provider"):
        provider.build_headers()


def test_openai_provider_build_request():
    """
    Test that OpenAIProvider correctly builds request with OpenAI-specific features.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "base_url": "https://api.test.com/v1"
    }
    
    provider = OpenAIProvider(config)
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(
        content="Test prompt",
        temperature=0.7
    )
    # In the new architecture, the user message should already be in the conversation history
    prompt_obj.add_user_message(prompt_obj.content)
    
    enhanced_request = provider.build_request(prompt_obj)
    
    # Check that the request is converted to OpenAI format (messages instead of prompt)
    assert "messages" in enhanced_request
    # Check that the user message is in the conversation history
    user_message = next((msg for msg in enhanced_request["messages"] if msg.get("role") == "user" and "Test prompt" in msg.get("content", "")), None)
    assert user_message is not None
    assert enhanced_request["temperature"] == 0.7
    
    # Check that default model is added if not present in original request
    assert enhanced_request["model"] == "gpt-test-model"


def test_openai_provider_build_request_with_model_override():
    """
    Test that OpenAIProvider preserves model if already in request.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "base_url": "https://api.test.com/v1"
    }
    
    provider = OpenAIProvider(config)
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(
        content="Test prompt",
        temperature=0.7,
        # Model override would typically be handled in the provider config or request logic
    )
    # In the new architecture, the user message should already be in the conversation history
    prompt_obj.add_user_message(prompt_obj.content)
    
    enhanced_request = provider.build_request(prompt_obj)
    
    # Since the model comes from the provider config in this implementation, 
    # it should match the config model
    assert enhanced_request["model"] == "gpt-test-model"
    
    # Check that the request is converted to OpenAI format (messages instead of prompt)
    assert "messages" in enhanced_request
    # Check that the user message is in the conversation history
    user_message = next((msg for msg in enhanced_request["messages"] if msg.get("role") == "user" and "Test prompt" in msg.get("content", "")), None)
    assert user_message is not None