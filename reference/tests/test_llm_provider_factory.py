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


def test_provider_factory_register_new_provider():
    """
    Test that ProviderFactory can register and create a new provider type.
    """
    from services.llm_provider.providers.base_provider import BaseProvider
    
    class MockProvider(BaseProvider):
        def build_headers(self):
            return {}
        
        def build_client(self):
            return None
        
        def build_request(self, request, user_prompt_id):
            return request
    
    factory = ProviderFactory()
    
    # Register a new provider type
    factory.register_provider("mock_provider", MockProvider)
    
    config = {"api_key": "test-key"}
    provider = factory.create_provider("mock_provider", config)
    
    assert isinstance(provider, MockProvider)
    
    # Check that the new provider is available
    available_providers = factory.get_available_providers()
    assert "mock_provider" in available_providers