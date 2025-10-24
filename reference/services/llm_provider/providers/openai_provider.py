"""
OpenAI Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the OpenAI provider following Qwen Code patterns.
"""

import httpx
from typing import Dict, Any
from services.llm_provider.providers.base_provider import BaseOpenAIProvider


class OpenAIProvider(BaseOpenAIProvider):
    """
    OpenAI provider implementation following Qwen Code patterns.
    """
    
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
        Enhance the request with OpenAI-specific features.
        
        Args:
            request: The base OpenAI-compatible request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Enhanced request with OpenAI-specific features
        """
        # Add user prompt ID as metadata to the request
        enhanced_request = request.copy()
        
        # Add provider-specific parameters if not already present
        if "model" not in enhanced_request:
            enhanced_request["model"] = self.model
        if "user" not in enhanced_request:
            enhanced_request["user"] = user_prompt_id  # OpenAI's user field for tracking
            
        return enhanced_request