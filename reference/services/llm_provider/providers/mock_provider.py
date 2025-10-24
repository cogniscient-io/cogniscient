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
        Build a mock request based on the input.

        Args:
            request: The base request
            user_prompt_id: Unique identifier for the user prompt

        Returns:
            Mock request structure
        """
        # Simply return the request with the user prompt ID for tracking
        enhanced_request = request.copy()
        enhanced_request["user_prompt_id"] = user_prompt_id
        return enhanced_request