"""
Qwen API client for interacting with Qwen LLM services.
"""
import asyncio
from typing import List, Dict, Any, Optional
from .auth_client import AuthenticatedHTTPClient
from .models import QwenMessage, QwenChatRequest, QwenChatResponse
from cogniscient.auth.token_manager import TokenManager


class QwenClient:
    """Qwen API client for generating responses."""
    
    def __init__(self, token_manager: TokenManager, base_url: str = "https://chat.qwen.ai"):
        """
        Initialize the Qwen client.
        
        Args:
            token_manager: Token manager for authentication
            base_url: Base URL for Qwen API
        """
        self.token_manager = token_manager
        self.auth_client = AuthenticatedHTTPClient(token_manager, base_url)

    async def close(self):
        """Close any resources held by the client."""
        await self.auth_client.close()

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen3:8b",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Optional[str]:
        """
        Generate a response from the Qwen API.
        
        Args:
            messages: List of messages in the format {"role": "...", "content": "..."}
            model: Model to use for generation
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Generated response text, or None if the request failed
        """
        # Convert messages to the expected format
        qwen_messages = [QwenMessage(role=msg["role"], content=msg["content"]) for msg in messages]
        
        # Prepare the request
        request_data = QwenChatRequest(
            model=model,
            messages=qwen_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Make the API call
        response = await self.auth_client._make_request(
            method="POST",
            endpoint="/api/v1/chat/completions",
            json_data=request_data.dict()
        )
        
        if response is None:
            print("Failed to get response from Qwen API")
            return None
        
        if response.status_code != 200:
            print(f"Qwen API error {response.status_code}: {response.text}")
            return None
        
        try:
            # Parse the response
            response_data = response.json()
            qwen_response = QwenChatResponse(**response_data)
            
            # Extract the content from the first choice
            if qwen_response.choices and len(qwen_response.choices) > 0:
                content = qwen_response.choices[0]["message"]["content"]
                return content
            else:
                print("No choices in Qwen API response")
                return None
        except Exception as e:
            print(f"Error parsing Qwen API response: {e}")
            return None

    async def get_models(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get available models from the Qwen API.
        
        Returns:
            List of available models, or None if the request failed
        """
        response = await self.auth_client._make_request(
            method="GET",
            endpoint="/api/v1/models"
        )
        
        if response is None:
            print("Failed to get models from Qwen API")
            return None
        
        if response.status_code != 200:
            print(f"Qwen API error {response.status_code}: {response.text}")
            return None
        
        try:
            response_data = response.json()
            return response_data.get("data", [])
        except Exception as e:
            print(f"Error parsing Qwen API response: {e}")
            return None

    async def check_credentials(self) -> bool:
        """
        Check if credentials are valid by making a test request.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        # Make a simple test request
        response = await self.auth_client._make_request(
            method="GET",
            endpoint="/api/v1/models"
        )
        
        if response is None:
            return False
        
        # If we get any response (success or auth error), credentials were validly formed
        # If we get a 401, the token was invalid/expired
        return response.status_code != 401