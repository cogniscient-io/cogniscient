"""
Unit tests for BaseProvider functionality in the pipeline.
"""
import pytest
from typing import Dict, Any
from services.llm_provider.providers.base_provider import BaseProvider


class ConcreteBaseProvider(BaseProvider):
    """Concrete implementation of BaseProvider for testing."""
    
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
        # Simple implementation for testing
        return {"prompt": prompt_obj.content}

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        # Simple implementation for testing
        return {
            "model": model_name,
            "capabilities": ["text-generation", "tool-calling"],
            "max_tokens": 4096
        }


def test_base_provider_abstract_methods():
    """Test that BaseProvider has the required abstract methods."""
    # Verify the abstract methods exist
    assert hasattr(BaseProvider, 'build_client')
    assert hasattr(BaseProvider, 'build_request')
    assert hasattr(BaseProvider, 'build_headers')
    assert hasattr(BaseProvider, 'converter')
    
    # BaseProvider can't be instantiated directly due to abstract methods
    with pytest.raises(TypeError):
        BaseProvider({})


def test_concrete_provider_implements_abstract_methods():
    """Test that concrete provider implements abstract methods."""
    config = {"api_key": "test-key"}
    provider = ConcreteBaseProvider(config)
    
    # Should be able to call the abstract methods
    headers = provider.build_headers()
    assert headers is not None
    
    converter = provider.converter
    assert converter is not None
    
    client = provider.build_client()
    assert client is not None
    
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="test")
    request = provider.build_request(prompt_obj)
    assert request is not None