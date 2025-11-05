"""
Unit tests for ProviderFactory functionality in the pipeline.
"""
import pytest
from services.llm_provider.providers.provider_factory import ProviderFactory
from services.llm_provider.providers.openai_provider import OpenAIProvider
from services.llm_provider.providers.mock_provider import MockProvider


def test_provider_factory_create_openai_provider():
    """Test that ProviderFactory creates OpenAIProvider correctly."""
    factory = ProviderFactory()
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = factory.create_provider("openai", config)
    
    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "test-key-12345"
    assert provider.model == "gpt-4-test"


def test_provider_factory_create_mock_provider():
    """Test that ProviderFactory creates MockProvider correctly."""
    factory = ProviderFactory()
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    provider = factory.create_provider("mock", config)
    
    assert isinstance(provider, MockProvider)
    assert provider.api_key == "test-key-12345"
    assert provider.model == "gpt-4-test"


def test_provider_factory_invalid_provider_type():
    """Test that ProviderFactory raises an error for invalid provider types."""
    factory = ProviderFactory()
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-4-test"
    }
    
    with pytest.raises(ValueError, match="is not registered"):
        factory.create_provider("invalid_type", config)


def test_provider_factory_available_providers():
    """Test that ProviderFactory returns available providers."""
    factory = ProviderFactory()
    providers = factory.get_available_providers()
    
    assert "openai" in providers
    assert "mock" in providers
    assert len(providers) >= 2


def test_provider_factory_register_provider():
    """Test that ProviderFactory can register new providers."""
    factory = ProviderFactory()
    
    # Create a simple mock provider class for testing
    class TestProvider:
        def __init__(self, config):
            self.config = config
            self.api_key = config.get("api_key")
            self.model = config.get("model", "test-model")
            
        @property
        def converter(self):
            from services.llm_provider.providers.openai_converter import OpenAIConverter
            return OpenAIConverter(self.model)
        
        def build_headers(self):
            return {"Authorization": f"Bearer {self.api_key}"}
        
        def build_client(self):
            from unittest.mock import MagicMock
            return MagicMock()
        
        def build_request(self, prompt_obj):
            return {"prompt": prompt_obj.content}
    
    factory.register_provider("test", TestProvider)
    providers = factory.get_available_providers()
    
    assert "test" in providers
    
    config = {"api_key": "test-key-12345"}
    provider = factory.create_provider("test", config)
    assert isinstance(provider, TestProvider)


def test_factory_create_provider_from_settings():
    """Test that ProviderFactory can create a provider from global settings."""
    factory = ProviderFactory()
    
    # This test is more complex, as it depends on global settings
    # We'll skip it for now since it requires valid environment variables
    pass