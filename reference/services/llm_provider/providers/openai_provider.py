"""
OpenAI Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the OpenAI provider following Qwen Code patterns.
"""

import httpx
from typing import Dict, Any
from services.llm_provider.providers.base_provider import BaseProvider
from services.llm_provider.converter import OpenAIConverter


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation following Qwen Code patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI provider with configuration.
        Uses OpenAI-specific defaults when values are not provided in config.
        
        Args:
            config: Dictionary containing provider configuration
                   Expected keys: api_key, model, base_url, timeout, max_retries
        """
        # Set OpenAI-specific defaults if not provided in config
        config = config.copy()  # Avoid modifying the original config
        if "model" not in config:
            config["model"] = "gpt-4-turbo"
        if "base_url" not in config:
            config["base_url"] = "https://api.openai.com/v1"
        
        # Call the parent constructor with the updated config
        super().__init__(config)
        
        # Initialize the converter for this provider
        self._converter = OpenAIConverter(self.model)
    
    @property
    def converter(self):
        """
        The converter for this OpenAI provider to transform data between kernel and provider formats.
        This returns an OpenAI-compatible converter with minimal transformations.
        """
        return self._converter
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for OpenAI API requests following standard patterns.
        
        Returns:
            Dictionary of headers for OpenAI API requests
        """
        if not self.api_key:
            raise ValueError("API key is required for OpenAI provider")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        return headers
    
    def build_client(self):
        """
        Build the OpenAI API client.
        
        Returns:
            Initialized httpx.AsyncClient instance
        """
        return httpx.AsyncClient(timeout=self.timeout, headers=self.build_headers())
    
    def build_request(self, request: Dict[str, Any], user_prompt_id: str) -> Dict[str, Any]:
        """
        Convert and enhance the request with OpenAI-specific features.
        
        Args:
            request: The base request in kernel format
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Request with OpenAI-specific format and features
        """
        # Convert the kernel format request to OpenAI format
        openai_request = self.converter.convert_kernel_request_to_provider(request)
        
        # Add provider-specific parameters
        if "model" not in openai_request:
            openai_request["model"] = self.model
        if "user" not in openai_request:
            openai_request["user"] = user_prompt_id  # OpenAI's user field for tracking
            
        return openai_request