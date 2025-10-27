"""
Provider Factory for GCS Kernel LLM Provider Backend.

This module implements the provider factory following Qwen Code patterns.
"""

from typing import Dict, Any, Type
from services.config import settings
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
    
    def create_provider_from_settings(self) -> BaseProvider:
        """
        Create a provider instance using configuration from global settings.
        This eliminates the need for callers to handle configuration details.
        
        Returns:
            Provider instance configured from global settings
            
        Raises:
            ValueError: If provider type is not registered or required settings are missing
        """
        # Get configuration from global settings
        llm_config = settings
        
        provider_type = llm_config.llm_provider_type
        if not provider_type:
            raise ValueError("Provider type is not specified in configuration")
        
        if provider_type not in self.providers:
            raise ValueError(f"Provider type '{provider_type}' is not registered")
        
        # Build configuration dictionary from settings
        config = {
            "api_key": llm_config.llm_api_key,
        }
        
        # Add optional configuration if provided
        if llm_config.llm_model:
            config["model"] = llm_config.llm_model
        if llm_config.llm_base_url:
            config["base_url"] = llm_config.llm_base_url
        if llm_config.llm_timeout:
            config["timeout"] = llm_config.llm_timeout
        if llm_config.llm_max_retries:
            config["max_retries"] = llm_config.llm_max_retries
            
        # Validate required configuration
        if not config["api_key"]:
            raise ValueError("API key is required but not provided in environment variables")
            
        provider_class = self.providers[provider_type]
        return provider_class(config)
    
    def get_available_providers(self) -> list[str]:
        """
        Get list of available provider types.
        
        Returns:
            List of available provider type names
        """
        return list(self.providers.keys())