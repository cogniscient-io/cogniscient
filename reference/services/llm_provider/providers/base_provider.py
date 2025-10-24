"""
Base Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the base provider following Qwen Code patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseOpenAIProvider(ABC):
    """
    Abstract base class for OpenAI-compatible providers following Qwen Code patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-4-turbo")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
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
        Enhance the OpenAI-compatible request with provider-specific features.
        
        Args:
            request: The base OpenAI-compatible request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Enhanced request with provider-specific features
        """
        pass