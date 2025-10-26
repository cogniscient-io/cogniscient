"""
Mock Provider for GCS Kernel LLM Provider Backend Integration Testing.

This module implements a mock provider that simulates an LLM response for testing purposes.
"""

import asyncio
from typing import Dict, Any
from services.llm_provider.providers.base_provider import BaseProvider


class MockProvider(BaseProvider):
    """
    Mock provider implementation for integration testing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the mock provider with configuration.
        
        Args:
            config: Dictionary containing provider configuration
        """
        # Call the parent constructor
        super().__init__(config)
        
        # Initialize a converter for this provider
        from services.llm_provider.converter import OpenAIConverter
        self._converter = OpenAIConverter(self.model)
    
    @property
    def converter(self):
        """
        The converter for this mock provider to transform data between kernel and provider formats.
        This returns an OpenAI-compatible converter suitable for testing.
        """
        return self._converter
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for mock API requests.

        Returns:
            Dictionary of headers for mock API requests
        """
        return {"Content-Type": "application/json"}

    def build_client(self):
        """
        Build a mock client that doesn't make actual API calls.

        Returns:
            A mock client (simulated object)
        """
        class MockClient:
            async def post(self, url, json=None, headers=None):
                # Simulate an API response
                class MockResponse:
                    async def json(self):
                        # Return a mock response that includes a "hello world" message
                        return {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "Hello, this is a test response from the LLM!"
                                    }
                                }
                            ]
                        }
                    
                    @property
                    def status_code(self):
                        return 200
                
                await asyncio.sleep(0.1)  # Simulate network delay
                return MockResponse()
        
        return MockClient()
    
    def build_request(self, request: Dict[str, Any], user_prompt_id: str) -> Dict[str, Any]:
        """
        Convert and build a mock request based on the input.
        
        Args:
            request: The base request in kernel format
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Mock request structure in OpenAI-compatible format
        """
        # Convert the kernel format request to OpenAI format (for consistency with testing)
        openai_request = self.converter.convert_kernel_request_to_provider(request)
        
        # Add user prompt ID for tracking
        openai_request["user_prompt_id"] = user_prompt_id
        return openai_request