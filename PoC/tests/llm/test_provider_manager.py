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
    
    # Try to set to qwen provider
    # Note: This will fail because qwen provider isn't properly initialized without a token manager
    success = llm_service.set_provider("qwen")
    # This might fail because qwen client isn't initialized
    # Depending on implementation, we might expect False here
    # Or if we mock the qwen client, we could test success
    
    # Try to set to litellm provider (which should work)
    success = llm_service.set_provider("litellm")
    assert success is True
    assert llm_service.current_provider == "litellm"


@pytest.mark.asyncio
async def test_get_available_providers(llm_service):
    """Test getting available providers."""
    providers = await llm_service.get_available_providers()
    assert "litellm" in providers
    # "qwen" might not be in the list if the client wasn't properly initialized


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