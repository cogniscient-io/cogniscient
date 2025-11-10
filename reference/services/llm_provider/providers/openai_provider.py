"""
OpenAI Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the OpenAI provider following Qwen Code patterns.
"""

import httpx
from typing import Dict, Any
from gcs_kernel.models import PromptObject
from services.llm_provider.providers.base_provider import BaseProvider
from .openai_converter import OpenAIConverter


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
    
    def build_request(self, prompt_obj: 'PromptObject') -> Dict[str, Any]:
        """
        Build the request with OpenAI-specific features from a PromptObject.
        
        Args:
            prompt_obj: The PromptObject containing all necessary information
            
        Returns:
            Request with OpenAI-specific format and features
        """
        # Start with the messages from the prompt object
        # OpenAI-compliant: messages should contain the complete conversation history
        messages = prompt_obj.conversation_history.copy()
        
        # Log the messages for debugging to see if system message is present
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"OpenAIProvider build_request - conversation history: {messages}")
        
        # Create the OpenAI request from the prompt object fields
        openai_request = {
            "messages": messages,
            "model": self.model
        }
        
        # Add optional parameters if present in the prompt object
        if prompt_obj.max_tokens is not None:
            openai_request["max_tokens"] = prompt_obj.max_tokens
        if prompt_obj.temperature:
            openai_request["temperature"] = prompt_obj.temperature
        
        # Add tools if specified in the prompt object
        if prompt_obj.tool_policy and prompt_obj.tool_policy.value != "none":
            # In a real implementation, we would fetch tools based on policy
            # For now, we'll use any custom tools in the prompt object
            if prompt_obj.custom_tools:
                openai_request["tools"] = prompt_obj.custom_tools
        
        # Add the user ID for tracking
        if prompt_obj.user_id:
            openai_request["user"] = prompt_obj.user_id
        elif prompt_obj.prompt_id:
            # Use prompt_id if user_id is not available
            openai_request["user"] = prompt_obj.prompt_id
        
        # Add other fields that may be relevant from the prompt object
        if prompt_obj.streaming_enabled:
            openai_request["stream"] = True

        # Convert the request to OpenAI format using the converter
        openai_request = self.converter.convert_kernel_request_to_provider(openai_request)
        
        return openai_request