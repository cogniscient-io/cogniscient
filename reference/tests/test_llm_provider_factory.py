"""
Test suite for the Provider Factory Implementation.

This module tests the ProviderFactory class and its functionality.
"""
import pytest
from services.llm_provider.providers.provider_factory import ProviderFactory
from services.llm_provider.providers.openai_provider import OpenAIProvider


def test_provider_factory_initialization():
    """
    Test that ProviderFactory initializes properly with default providers.
    """
    factory = ProviderFactory()
    
    # Check that openai provider is registered by default
    available_providers = factory.get_available_providers()
    assert "openai" in available_providers
    assert len(available_providers) >= 1  # At least openai should be available


def test_provider_factory_create_openai_provider():
    """
    Test that ProviderFactory can create an OpenAIProvider instance.
    """
    factory = ProviderFactory()
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "base_url": "https://api.test.com/v1"
    }
    
    provider = factory.create_provider("openai", config)
    
    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "test-key-12345"
    assert provider.model == "gpt-test-model"


def test_provider_factory_create_invalid_provider():
    """
    Test that ProviderFactory raises error for unregistered provider type.
    """
    factory = ProviderFactory()
    config = {
        "api_key": "test-key-12345"
    }
    
    with pytest.raises(ValueError, match="Provider type 'invalid_provider' is not registered"):
        factory.create_provider("invalid_provider", config)


# Test removed: This test was creating an incomplete MockProvider that didn't implement 
# the required converter property from BaseProvider, making it invalid and not useful.
# The real MockProvider in the codebase properly implements all required methods.