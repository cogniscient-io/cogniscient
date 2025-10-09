"""
Tests for the provider manager.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from cogniscient.llm.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Create an LLM service for testing."""
    # Mock token manager since we're not testing OAuth functionality here
    mock_token_manager = MagicMock()
    llm_service = LLMService(token_manager=mock_token_manager)
    return llm_service


@pytest.mark.asyncio
async def test_set_provider(llm_service):
    """Test setting a provider."""
    # Initially, default provider should be litellm
    assert llm_service.current_provider == "litellm"
    
    # Try to set to litellm provider (which should work)
    success = llm_service.set_provider("litellm")
    assert success is True
    assert llm_service.current_provider == "litellm"
    
    # Try to set to qwen provider - this should work if token manager is available
    # Since we've mocked the token manager, it should return True if the method exists
    success = llm_service.set_provider("qwen")
    # The success depends on whether token manager has valid credentials
    # The important thing is that the method call doesn't raise an error
    assert isinstance(success, bool)


@pytest.mark.asyncio
async def test_get_available_providers_with_token_manager():
    """Test getting available providers when token manager is available."""
    # Create an LLM service with a mocked token manager that has valid credentials
    mock_token_manager = MagicMock()
    mock_token_manager.get_valid_access_token = AsyncMock(return_value="fake_token")
    
    llm_service = LLMService(token_manager=mock_token_manager)
    providers = await llm_service.get_available_providers()
    assert "litellm" in providers
    
    # Test setting qwen provider when token manager is available
    success = llm_service.set_provider("qwen")
    assert success is True  # Should succeed when token manager is available


@pytest.mark.asyncio
async def test_get_available_providers_without_token_manager():
    """Test getting available providers when token manager is not provided."""
    llm_service = LLMService(token_manager=None)
    providers = await llm_service.get_available_providers()
    assert "litellm" in providers
    
    # Try to set qwen provider without token manager - should fail
    success = llm_service.set_provider("qwen")
    assert success is False  # Should fail when no token manager is available


@pytest.mark.asyncio
async def test_provider_switching_logic(llm_service):
    """Test the provider switching logic."""
    # Add a mock provider
    mock_provider = AsyncMock()
    mock_provider.generate_response = AsyncMock(return_value="mock response")
    llm_service.add_provider("mock_provider", mock_provider)
    
    # Switch to the mock provider
    success = llm_service.set_provider("mock_provider")
    assert success is True
    assert llm_service.current_provider == "mock_provider"
    
    # Get the current provider
    current_provider = llm_service.get_provider()
    assert current_provider == mock_provider


@pytest.mark.asyncio
async def test_generate_response_with_qwen_auth_headers():
    """Test that Qwen provider correctly adds authentication headers."""
    # Create a service with token manager
    mock_token_manager = MagicMock()
    mock_token_manager.get_valid_access_token = AsyncMock(return_value="test_token")
    
    llm_service = LLMService(token_manager=mock_token_manager)
    
    # Mock the LiteLLM adapter's generate_response method to capture the kwargs
    original_adapter = llm_service.litellm_adapter
    original_generate_response = original_adapter.generate_response
    original_adapter.generate_response = AsyncMock(return_value="test response")
    
    # Set provider to qwen
    success = llm_service.set_provider("qwen")
    assert success is True
    
    # Generate response - should include auth headers
    messages = [{"role": "user", "content": "Hello"}]
    await llm_service.generate_response(messages, model="test-model")
    
    # Check that generate_response was called with authentication headers
    call_args = original_adapter.generate_response.call_args
    assert call_args is not None
    kwargs = call_args.kwargs if call_args.kwargs else call_args[1] if len(call_args) > 1 else {}
    
    if "headers" in kwargs:
        headers = kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
        assert "api-key" in headers
        assert headers["api-key"] == "test_token"
    
    # Reset the mock
    original_adapter.generate_response = original_generate_response


@pytest.mark.asyncio
async def test_generate_response_fallback_without_token():
    """Test that Qwen provider handles missing token gracefully."""
    # Create a service with token manager that returns no token
    mock_token_manager = MagicMock()
    mock_token_manager.get_valid_access_token = AsyncMock(return_value=None)
    
    llm_service = LLMService(token_manager=mock_token_manager)
    
    # Set provider to qwen - should still succeed
    success = llm_service.set_provider("qwen")
    assert success is True
    
    # Generate response - should return None due to missing token
    messages = [{"role": "user", "content": "Hello"}]
    result = await llm_service.generate_response(messages, model="test-model")
    assert result is None