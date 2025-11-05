"""
Unit tests for OpenAIProvider functionality in the pipeline.
"""
import pytest
from unittest.mock import MagicMock
from services.llm_provider.providers.openai_provider import OpenAIProvider


def test_openai_provider_initialization():
    """Test that OpenAIProvider initializes properly."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test",
        "base_url": "https://api.test.com/v1"
    }
    
    provider = OpenAIProvider(config)
    
    assert provider.api_key == "test-key-12345"
    assert provider.model == "gpt-4-test"
    assert provider.base_url == "https://api.test.com/v1"
    assert provider.converter is not None


def test_openai_provider_build_headers():
    """Test that OpenAIProvider builds correct headers."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = OpenAIProvider(config)
    headers = provider.build_headers()
    
    expected_headers = {
        "Authorization": "Bearer test-key-12345",
        "Content-Type": "application/json"
    }
    
    assert headers == expected_headers


def test_openai_provider_build_client():
    """Test that OpenAIProvider builds a client."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = OpenAIProvider(config)
    client = provider.build_client()
    
    # Client should be an httpx.AsyncClient or similar
    assert client is not None


def test_openai_provider_build_request():
    """Test that OpenAIProvider builds correct requests."""
    from gcs_kernel.models import PromptObject
    
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = OpenAIProvider(config)
    
    # Create a PromptObject with specific parameters
    prompt_obj = PromptObject.create(
        content="Test prompt",
        max_tokens=100,
        temperature=0.7
    )
    prompt_obj.conversation_history = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "Previous user message"},
        {"role": "user", "content": "Test prompt"}  # Current message should be in history
    ]
    
    request = provider.build_request(prompt_obj)
    
    # Verify the request structure
    assert "messages" in request
    assert request["model"] == "gpt-4-test"
    assert request["max_tokens"] == 100
    assert request["temperature"] == 0.7
    
    # Verify messages include conversation history and current prompt
    messages = request["messages"]
    assert len(messages) == 3  # system, user, and current prompt
    assert messages[0]["content"] == "System message"
    assert messages[1]["content"] == "Previous user message"
    assert messages[2]["content"] == "Test prompt"


def test_openai_provider_build_request_with_tool_calls():
    """Test that OpenAIProvider handles tool calls in requests."""
    from gcs_kernel.models import PromptObject
    
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = OpenAIProvider(config)
    
    # Create a PromptObject with conversation history and tools
    prompt_obj = PromptObject.create(content="Test with tools")
    prompt_obj.conversation_history = [
        {"role": "user", "content": "Previous message"},
        {"role": "user", "content": "Test with tools"}  # Current message should be in history
    ]
    
    request = provider.build_request(prompt_obj)
    
    # Verify the request structure
    assert "messages" in request
    assert request["model"] == "gpt-4-test"
    assert len(request["messages"]) == 2  # previous message + current prompt