"""
Qwen API client for interacting with Qwen LLM services.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from .auth_client import AuthenticatedHTTPClient
from .models import QwenMessage, QwenChatRequest, QwenChatResponse
from cogniscient.auth.token_manager import TokenManager


class QwenClient:
    """Qwen API client for generating responses."""
    
    def __init__(self, token_manager: TokenManager, base_url: str = None):
        """
        Initialize the Qwen client.
        
        Args:
            token_manager: Token manager for authentication
            base_url: Base URL for Qwen API (will be determined dynamically from credentials if not provided)
        """
        self.token_manager = token_manager
        
        # The base_url will be set dynamically in the generate_response method
        # based on the resource_url from the credentials
        self.base_url = base_url
        self.auth_client = None  # Will be created dynamically

    async def close(self):
        """Close any resources held by the client."""
        if self.auth_client:
            await self.auth_client.close()

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,  # Will use settings default if None
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
        # Load credentials to get the resource_url
        credentials = await self.token_manager.load_credentials()
        if not credentials:
            print("No Qwen credentials available")
            return None
            
        # Determine the correct endpoint based on resource_url
        resource_url = getattr(credentials, 'resource_url', None)
        if resource_url:
            # Use the resource_url from credentials
            base_url = f"https://{resource_url}/v1" if not resource_url.startswith('http') else resource_url
            if not base_url.endswith('/v1'):
                base_url = f"{base_url}/v1"
        else:
            # Fallback to DashScope endpoint
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
        print(f"Using Qwen API endpoint: {base_url}")
        
        # Create auth client with the correct endpoint
        self.auth_client = AuthenticatedHTTPClient(self.token_manager, base_url)
        
        # Use settings default model if no model specified
        if model is None:
            from cogniscient.engine.config.settings import settings
            model = settings.qwen_model
        
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
        
        # Make the API call - use OpenAI-compatible endpoint for DashScope
        response = await self.auth_client._make_request(
            method="POST",
            endpoint="/chat/completions",  # OpenAI-compatible endpoint for DashScope
            json_data=request_data.dict()
        )
        
        if response is None:
            print("Failed to get response from Qwen API")
            return None
        
        if response.status_code != 200:
            print(f"Qwen API error {response.status_code}: {response.text}")
            return None
        
        try:
            # Check if response has content
            if not response.text or not response.text.strip():
                print("Qwen API returned empty response")
                return ""
            
            # Check if response looks like HTML (probably a WAF challenge page)
            if response.text.strip().lower().startswith('<!doctype') or '<html' in response.text.lower():
                print("Qwen API returned a WAF challenge page (HTML) instead of JSON API response.")
                print("This indicates that additional verification is required or the request was blocked by a firewall.")
                print("This may require interactive verification or checking rate limits.")
                print(f"Response preview: {response.text[:200]}...")
                return "Error: Access blocked by security verification. Please complete the required verification in a browser."
            
            # Parse the response
            response_data = response.json()
            qwen_response = QwenChatResponse(**response_data)
            
            # Extract the content from the first choice
            if qwen_response.choices and len(qwen_response.choices) > 0:
                content = qwen_response.choices[0]["message"]["content"]
                # Ensure content is not None before returning
                return content if content is not None else ""
            else:
                print("No choices in Qwen API response")
                print(f"Full response: {response.text[:500]}")  # Print first 500 chars of response for debugging
                return ""
        except json.JSONDecodeError as e:
            print(f"Error parsing Qwen API response as JSON: {e}")
            print(f"Raw response: '{response.text[:500]}...'")  # Limited to first 500 chars to avoid too much output
            # Check if it's a WAF page
            if response.text.strip().lower().startswith('<!doctype') or '<html' in response.text.lower():
                print("Detected HTML response (likely WAF challenge page) instead of API response.")
                return "Error: Access blocked by security verification. Please complete the required verification in a browser."
            return ""
        except Exception as e:
            print(f"Error processing Qwen API response: {e}")
            print(f"Raw response: '{response.text[:500]}...'")  # Limited to first 500 chars to avoid too much output
            return ""

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