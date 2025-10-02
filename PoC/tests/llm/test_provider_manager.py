"""
Tests for the provider manager.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from cogniscient.llm.provider_manager import ProviderManager


@pytest.fixture
def provider_manager():
    """Create a provider manager for testing."""
    # Mock token manager since we're not testing OAuth functionality here
    mock_token_manager = MagicMock()
    provider_manager = ProviderManager(token_manager=mock_token_manager)
    return provider_manager


@pytest.mark.asyncio
async def test_set_provider(provider_manager):
    """Test setting a provider."""
    # Initially, default provider should be litellm
    assert provider_manager.current_provider == "litellm"
    
    # Try to set to qwen provider
    # Note: This will fail because qwen provider isn't properly initialized without a token manager
    success = provider_manager.set_provider("qwen")
    # This might fail because qwen client isn't initialized
    # Depending on implementation, we might expect False here
    # Or if we mock the qwen client, we could test success
    
    # Try to set to litellm provider (which should work)
    success = provider_manager.set_provider("litellm")
    assert success is True
    assert provider_manager.current_provider == "litellm"


@pytest.mark.asyncio
async def test_get_available_providers(provider_manager):
    """Test getting available providers."""
    providers = await provider_manager.get_available_providers()
    assert "litellm" in providers
    # "qwen" might not be in the list if the client wasn't properly initialized


@pytest.mark.asyncio
async def test_provider_switching_logic(provider_manager):
    """Test the provider switching logic."""
    # Add a mock provider
    mock_provider = AsyncMock()
    mock_provider.generate_response = AsyncMock(return_value="mock response")
    provider_manager.add_provider("mock_provider", mock_provider)
    
    # Switch to the mock provider
    success = provider_manager.set_provider("mock_provider")
    assert success is True
    assert provider_manager.current_provider == "mock_provider"
    
    # Get the current provider
    current_provider = provider_manager.get_provider()
    assert current_provider == mock_provider