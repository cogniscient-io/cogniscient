"""
Authenticated client for making HTTP requests with OAuth tokens.
"""
import asyncio
import httpx
from typing import Dict, Optional, Any
from cogniscient.auth.token_manager import TokenManager


class AuthenticatedHTTPClient:
    """HTTP client that automatically handles authentication headers."""
    
    def __init__(
        self,
        token_manager: TokenManager,
        base_url: str = "https://chat.qwen.ai",
        timeout: int = 30
    ):
        """
        Initialize the authenticated HTTP client.
        
        Args:
            token_manager: TokenManager instance to get tokens
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
        """
        self.token_manager = token_manager
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)
        
        # Initialize retry settings
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get headers with Authorization."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_on_auth_failure: bool = True
    ) -> Optional[httpx.Response]:
        """
        Make an authenticated HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base URL)
            json_data: JSON payload for the request
            headers: Additional headers to include
            retry_on_auth_failure: Whether to retry after refreshing token if unauthorized
            
        Returns:
            Response object if successful, None otherwise
        """
        # Get a valid access token
        token = await self.token_manager.get_valid_access_token()
        if not token:
            print("No valid access token available")
            return None

        # Combine headers
        request_headers = self._get_headers(token)
        if headers:
            request_headers.update(headers)

        url = f"{self.base_url}{endpoint}"
        
        # Prepare request parameters
        request_kwargs = {
            "url": url,
            "headers": request_headers
        }
        if json_data:
            request_kwargs["json"] = json_data

        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                response = await self.http_client.request(method, **request_kwargs)
                
                # If 401 Unauthorized and we haven't retried with a refresh
                if response.status_code == 401 and retry_on_auth_failure and retry_count == 0:
                    print("Access token expired, attempting to refresh...")
                    
                    # Try to refresh the token
                    new_token = await self.token_manager.get_valid_access_token()
                    if new_token:
                        # Retry with new token
                        request_headers = self._get_headers(new_token)
                        request_kwargs["headers"] = request_headers
                        
                        response = await self.http_client.request(method, **request_kwargs)
                    
                    retry_count += 1
                    continue  # Retry the request
                
                # Handle rate limiting
                if response.status_code == 429:
                    # Wait for the specified retry-after time or default time
                    retry_after = float(response.headers.get("Retry-After", self.retry_delay))
                    print(f"Rate limited. Waiting {retry_after}s before retrying...")
                    await asyncio.sleep(retry_after)
                    retry_count += 1
                    continue  # Retry the request
                
                # Success or other error
                return response
                
            except httpx.RequestError as e:
                print(f"Request error: {e}")
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (retry_count + 1))  # Exponential backoff
                    retry_count += 1
                    continue
                else:
                    return None

        return None