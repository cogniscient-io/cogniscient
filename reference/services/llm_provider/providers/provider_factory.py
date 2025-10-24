"""
Provider Factory for GCS Kernel LLM Provider Backend.

This module implements the provider factory following Qwen Code patterns.
"""

from typing import Dict, Any, Type
from services.llm_provider.providers.base_provider import BaseProvider
from services.llm_provider.providers.openai_provider import OpenAIProvider
from services.llm_provider.providers.mock_provider import MockProvider


class ProviderFactory:
    """
    Factory class for creating different LLM providers following Qwen Code patterns.
    """
    
    def __init__(self):
        self.providers: Dict[str, Type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "mock": MockProvider,
        }
    
    def register_provider(self, name: str, provider_class: Type[BaseProvider]):
        """
        Register a new provider type with the factory.
        
        Args:
            name: Name of the provider type
            provider_class: Class of the provider to register
        """
        self.providers[name] = provider_class
    
    def create_provider(self, provider_type: str, config: Dict[str, Any]) -> BaseProvider:
        """
        Create a provider instance of the specified type.
        
        Args:
            provider_type: Type of provider to create
            config: Configuration for the provider
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider type is not registered
        """
        if provider_type not in self.providers:
            raise ValueError(f"Provider type '{provider_type}' is not registered")
        
        provider_class = self.providers[provider_type]
        return provider_class(config)
    
    def get_available_providers(self) -> list[str]:
        """
        Get list of available provider types.
        
        Returns:
            List of available provider type names
        """
        return list(self.providers.keys())