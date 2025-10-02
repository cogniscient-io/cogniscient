import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .token_manager import QwenCredentials, TokenManager
from .utils import generate_pkce_pair


class DeviceAuthData(BaseModel):
    """Represents response from device authorization endpoint."""
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class DeviceTokenData(BaseModel):
    """Represents successful response from token endpoint."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: Optional[str] = None


class DeviceTokenPendingData(BaseModel):
    """Represents pending response from token endpoint."""
    error: str = "authorization_pending"
    error_description: str = "Authorization pending"


class DeviceTokenSlowDownData(BaseModel):
    """Represents slow down response from token endpoint."""
    error: str = "slow_down"
    error_description: str = "Polling too fast"


class DeviceTokenErrorData(BaseModel):
    """Represents error response from token endpoint."""
    error: str
    error_description: str


class QwenOAuth2Client:
    """Qwen OAuth2 client implementing device authorization flow."""
    
    def __init__(
        self,
        client_id: str,
        authorization_server: str = "https://chat.qwen.ai",
        timeout: int = 30
    ):
        """
        Initialize the Qwen OAuth2 client.
        
        Args:
            client_id: OAuth client ID
            authorization_server: Base URL of the authorization server
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.authorization_server = authorization_server.rstrip('/')
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def request_device_authorization(
        self,
        scope: str = "openid profile email",
        audience: Optional[str] = None
    ) -> Optional[DeviceAuthData]:
        """
        Request device authorization from the authorization server.
        
        Args:
            scope: OAuth scopes to request
            audience: Optional audience parameter
            
        Returns:
            DeviceAuthData if successful, None otherwise
        """
        url = f"{self.authorization_server}/oauth/device/code"
        
        data = {
            "client_id": self.client_id,
            "scope": scope
        }
        
        if audience:
            data["audience"] = audience

        try:
            response = await self.http_client.post(url, data=data)
            response.raise_for_status()
            
            data = response.json()
            # Calculate expiry date based on current time and expires_in
            expiry_date = datetime.now().timestamp() + data["expires_in"]
            data["expires_at"] = expiry_date
            
            return DeviceAuthData(**data)
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            print(f"Error requesting device authorization: {e}")
            return None

    async def poll_device_token(
        self,
        device_code: str,
        code_verifier: str,
        interval: int = 5
    ) -> Optional[
        DeviceTokenData | DeviceTokenPendingData | 
        DeviceTokenSlowDownData | DeviceTokenErrorData
    ]:
        """
        Poll the token endpoint until a response is received.
        
        Args:
            device_code: Device code from device authorization request
            code_verifier: PKCE code verifier
            interval: Polling interval in seconds
            
        Returns:
            Token response data based on the result
        """
        url = f"{self.authorization_server}/oauth/token"
        
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": self.client_id,
            "device_code": device_code,
            "code_verifier": code_verifier  # PKCE code verifier
        }

        try:
            response = await self.http_client.post(url, data=data)
            
            if response.status_code == 200:
                # Success - return token data
                token_data = response.json()
                return DeviceTokenData(**token_data)
            elif response.status_code == 400:
                error_data = response.json()
                error = error_data.get("error", "unknown_error")
                
                if error == "authorization_pending":
                    return DeviceTokenPendingData()
                elif error == "slow_down":
                    return DeviceTokenSlowDownData()
                else:
                    return DeviceTokenErrorData(
                        error=error,
                        error_description=error_data.get("error_description", "Unknown error")
                    )
            else:
                # Other error responses
                return DeviceTokenErrorData(
                    error="http_error",
                    error_description=f"HTTP {response.status_code}: {response.text}"
                )
        except (httpx.RequestError, json.JSONDecodeError) as e:
            print(f"Error polling device token: {e}")
            return DeviceTokenErrorData(
                error="request_error",
                error_description=str(e)
            )

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Optional[QwenCredentials]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            New QwenCredentials if successful, None otherwise
        """
        url = f"{self.authorization_server}/oauth/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token
        }

        try:
            response = await self.http_client.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Calculate expiry date
            expiry_date = datetime.fromtimestamp(
                datetime.now().timestamp() + token_data.get("expires_in", 3600)
            )
            
            return QwenCredentials(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),  # May not be returned
                token_type=token_data.get("token_type", "Bearer"),
                expiry_date=expiry_date
            )
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            print(f"Error refreshing access token: {e}")
            return None


class QwenClientError(Exception):
    """Exception for Qwen API client errors."""
    pass


class NetworkError(QwenClientError):
    """Exception for network-related errors."""
    pass


class AuthenticationError(QwenClientError):
    """Exception for authentication-related errors."""
    pass


class QwenAPIError(QwenClientError):
    """Exception for Qwen API errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Qwen API Error {status_code}: {message}")