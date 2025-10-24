"""
Base Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the base provider following Qwen Code patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers following Qwen Code patterns.
    Provides common configuration and properties for all LLM providers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base provider with configuration.
        
        Args:
            config: Dictionary containing provider configuration
                   Expected keys: api_key, model, base_url, timeout, max_retries
        """
        self.config = config
        self.api_key = config.get("api_key")
        self.model = config.get("model", "default-model")
        self.base_url = config.get("base_url", "https://api.default-llm-provider.com/v1")
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        
    @abstractmethod
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for API requests following Qwen Code patterns.
        
        Returns:
            Dictionary of headers to include in API requests
        """
        pass
    
    @abstractmethod
    def build_client(self):
        """
        Build the API client following Qwen Code patterns.
        
        Returns:
            Initialized API client instance
        """
        pass
    
    @abstractmethod
    def build_request(self, request: Dict[str, Any], user_prompt_id: str) -> Dict[str, Any]:
        """
        Build the request with provider-specific features.
        
        Args:
            request: The base request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Enhanced request with provider-specific features
        """
        pass