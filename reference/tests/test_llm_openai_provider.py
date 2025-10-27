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
    request = {
        "prompt": "Test prompt",
        "temperature": 0.7
    }
    
    enhanced_request = provider.build_request(request, "user_prompt_123")
    
    # Check that the request is converted to OpenAI format (messages instead of prompt)
    assert "messages" in enhanced_request
    assert len(enhanced_request["messages"]) == 1
    assert enhanced_request["messages"][0]["role"] == "user"
    assert enhanced_request["messages"][0]["content"] == "Test prompt"
    assert enhanced_request["temperature"] == 0.7
    
    # Check that default model is added if not present in original request
    assert enhanced_request["model"] == "gpt-test-model"
    
    # Check that user field is added for OpenAI tracking
    assert enhanced_request["user"] == "user_prompt_123"


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
    request = {
        "prompt": "Test prompt",
        "model": "gpt-specific-model",
        "temperature": 0.7
    }
    
    enhanced_request = provider.build_request(request, "user_prompt_123")
    
    # Original model should be preserved, not overridden by config
    assert enhanced_request["model"] == "gpt-specific-model"
    
    # Check that the request is converted to OpenAI format (messages instead of prompt)
    assert "messages" in enhanced_request
    assert len(enhanced_request["messages"]) == 1
    assert enhanced_request["messages"][0]["role"] == "user"
    assert enhanced_request["messages"][0]["content"] == "Test prompt"
    
    assert enhanced_request["user"] == "user_prompt_123"