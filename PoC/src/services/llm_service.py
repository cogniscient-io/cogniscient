"""
LLM service for the Adaptive Chatbot application.
"""

import httpx
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type, retry_if_result
from src.config.settings import settings

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLM APIs."""
    
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = settings.llm_base_url.rstrip('/')  # Ensure no trailing slash
        # Configure httpx client with default timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.llm_request_timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json"
            }
        )
    
    def _is_retryable_error(self, e: Exception) -> bool:
        """Check if an exception is retryable."""
        if isinstance(e, (httpx.NetworkError, httpx.TimeoutException)):
            return True
        if isinstance(e, httpx.HTTPStatusError):
            status_code = e.response.status_code
            # Retry on server errors and rate limits
            return status_code >= 500 or status_code == 429
        return False
    
    def _should_retry_on_result(self, response: httpx.Response) -> bool:
        """Check if a response indicates a retryable condition."""
        if response.status_code == 429:
            logger.warning("Rate limited (429). Retrying...")
            return True
        # Could add more logic here to check response body for specific retryable errors
        return False
    
    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError)) | 
              retry_if_result(lambda r: r.status_code >= 500 or r.status_code == 429),
        reraise=True
    )
    async def _make_api_request(self, endpoint: str, data: Dict[str, Any]) -> httpx.Response:
        """Make an API request with retry logic."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = await self.client.post(url, json=data)
            # Raise for status to trigger retry on 4xx/5xx
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise e
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise e
    
    async def generate_response(self, prompt: str, domain: Optional[str] = None) -> str:
        """Generate a response from the LLM API with robust error handling."""
        if not self.api_key:
            # Return a mock response if no API key is configured
            domain_context = f" [Domain: {domain}]" if domain else ""
            return f"Mock response to: {prompt}{domain_context}"
        
        try:
            # Create messages with domain context if available
            messages = []
            if domain:
                messages.append({
                    "role": "system",
                    "content": f"You are an expert in the {domain} domain. Please explain the error with knowledge specific to this domain and provide options to resolve it."
                })
            
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request data
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7
            }
            
            # Make the API request with retries
            response = await self._make_api_request("chat/completions", data)
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
                    
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            return f"Error: Unable to generate response ({str(e)})"
     
    async def close(self):
        """Close the underlying httpx client."""
        await self.client.aclose()