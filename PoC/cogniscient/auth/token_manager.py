import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Union
import aiofiles
from filelock import FileLock, Timeout


class TokenManagerError(Exception):
    """Base exception for token manager errors."""
    pass


class CredentialsClearRequiredError(TokenManagerError):
    """Exception raised when credential clearing is required."""
    pass


class QwenCredentials:
    """Represents Qwen OAuth credentials."""
    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_type: str = "Bearer",
        expiry_date: Optional[datetime] = None,
        **kwargs
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expiry_date = expiry_date
        # Store any additional tokens or data
        for key, value in kwargs.items():
            setattr(self, key, value)

    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if the token is expired with an optional buffer time."""
        if not self.expiry_date:
            return False  # If no expiry date, assume it doesn't expire
        return datetime.now() >= (self.expiry_date - timedelta(seconds=buffer_seconds))

    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Convert credentials to dictionary."""
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
        }
        if self.expiry_date:
            data["expiry_date"] = self.expiry_date.isoformat()
        
        # Add any additional attributes (like resource_url)
        for attr_name, attr_value in self.__dict__.items():
            if attr_name not in ["access_token", "refresh_token", "token_type", "expiry_date"]:
                data[attr_name] = attr_value
                
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, float, int]]) -> "QwenCredentials":
        """Create credentials from dictionary."""
        expiry_date = None
        if "expiry_date" in data:
            expiry_value = data["expiry_date"]
            if isinstance(expiry_value, str):
                # Handle ISO format string
                expiry_date = datetime.fromisoformat(expiry_value)
            elif isinstance(expiry_value, (int, float)):
                # Handle timestamp - check if it's in milliseconds (as in your file)
                if expiry_value > 1e10:  # If it's a large number, likely milliseconds
                    expiry_date = datetime.fromtimestamp(expiry_value / 1000.0)
                else:  # Otherwise it's seconds
                    expiry_date = datetime.fromtimestamp(expiry_value)
        
        # Extract standard fields and any additional fields
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        token_type = data.get("token_type", "Bearer")
        
        # Get any additional fields (like resource_url)
        additional_fields = {k: v for k, v in data.items() 
                            if k not in ["access_token", "refresh_token", "token_type", "expiry_date"]}
        
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expiry_date=expiry_date,
            **additional_fields  # Pass any additional fields as keyword arguments
        )


class TokenManager:
    """Manages OAuth tokens with file-based caching and distributed file locking."""
    
    def __init__(
        self,
        credentials_file: Optional[str] = None,
        credentials_dir: Optional[str] = None,
        lock_timeout: int = 10
    ):
        """
        Initialize the TokenManager.
        
        Args:
            credentials_file: Path to the credentials file
            credentials_dir: Directory to store credentials (default: ~/.qwen)
            lock_timeout: Timeout for file locks in seconds
        """
        # Set up credentials file path
        if credentials_file:
            self.credentials_file = Path(credentials_file)
        else:
            if credentials_dir:
                creds_dir = Path(credentials_dir)
            else:
                creds_dir = Path.home() / ".qwen"
            creds_dir.mkdir(parents=True, exist_ok=True)
            self.credentials_file = creds_dir / "oauth_creds.json"
        
        # Create directory if it doesn't exist
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set file permissions to 600 (owner read/write only)
        if self.credentials_file.exists():
            os.chmod(self.credentials_file, 0o600)
        
        self.lock_timeout = lock_timeout
        self.lock_file = f"{self.credentials_file}.lock"
        
        # In-memory cache
        self._cached_credentials: Optional[QwenCredentials] = None
        self._cache_timestamp = 0
        
        # Lock for in-memory cache synchronization
        self._cache_lock = asyncio.Lock()

    def _get_file_lock(self) -> FileLock:
        """Get a file lock instance."""
        return FileLock(self.lock_file, timeout=self.lock_timeout)

    async def save_credentials(self, credentials: QwenCredentials) -> bool:
        """
        Save credentials to the file with atomic write and proper permissions.
        
        Args:
            credentials: QwenCredentials object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert credentials to dict
            creds_dict = credentials.to_dict()
            
            # Write to a temporary file first
            temp_file = f"{self.credentials_file}.tmp"
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(creds_dict, indent=2))
            
            # Then atomic move to final location
            os.rename(temp_file, self.credentials_file)
            
            # Set correct file permissions
            os.chmod(self.credentials_file, 0o600)
            
            # Update in-memory cache
            async with self._cache_lock:
                self._cached_credentials = credentials
                self._cache_timestamp = time.time()
            
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    async def load_credentials(self) -> Optional[QwenCredentials]:
        """
        Load credentials from the file with file locking.
        
        Returns:
            QwenCredentials object if found and valid, None otherwise
        """
        # First check in-memory cache
        async with self._cache_lock:
            if self._cached_credentials and (time.time() - self._cache_timestamp < 30):
                # Return cached credentials if still fresh (less than 30 seconds old)
                return self._cached_credentials

        try:
            # Use file lock to prevent concurrent access
            with self._get_file_lock():
                if not self.credentials_file.exists():
                    return None
                
                async with aiofiles.open(self.credentials_file, 'r') as f:
                    content = await f.read()
                    if not content.strip():
                        return None
                    
                    data = json.loads(content)
                    credentials = QwenCredentials.from_dict(data)
                    
                    # Update in-memory cache
                    async with self._cache_lock:
                        self._cached_credentials = credentials
                        self._cache_timestamp = time.time()
                    
                    return credentials
        except (json.JSONDecodeError, KeyError, PermissionError) as e:
            print(f"Error loading credentials: {e}")
            return None
        except Timeout:
            print(f"Timeout waiting for file lock: {self.lock_file}")
            return None

    async def has_valid_credentials(self) -> bool:
        """
        Check if we have valid credentials that aren't expired.
        
        Returns:
            True if valid credentials exist, False otherwise
        """
        credentials = await self.load_credentials()
        if not credentials:
            return False
        return not credentials.is_expired()

    async def get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token string if available, None otherwise
        """
        credentials = await self.load_credentials()
        if not credentials:
            return None
        
        # Check if token is expired
        if credentials.is_expired():
            # Try to refresh the token
            new_credentials = await self._refresh_access_token(credentials)
            if new_credentials:
                # Update in-memory cache
                async with self._cache_lock:
                    self._cached_credentials = new_credentials
                    self._cache_timestamp = time.time()
                return new_credentials.access_token
            else:
                # Refresh failed, so credentials are invalid
                return None
        
        return credentials.access_token

    async def _refresh_access_token(self, credentials: QwenCredentials) -> Optional[QwenCredentials]:
        """
        Refresh the access token using the refresh token.
        
        Args:
            credentials: Current credentials with refresh token
            
        Returns:
            New credentials with refreshed access token, or None if refresh failed
        """
        import aiohttp
        
        # Get the Qwen client ID from settings
        from cogniscient.engine.config.settings import settings
        
        if not settings.qwen_client_id:
            print("Error: QWEN_CLIENT_ID not configured in environment.")
            return None
        
        # Prepare the data for the token refresh request
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": credentials.refresh_token,
            "client_id": settings.qwen_client_id
        }
        
        # Use the authorization server URL for token refresh
        token_endpoint = f"{settings.qwen_authorization_server}/api/v1/oauth2/token"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    token_endpoint,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=aiohttp.FormData(token_data)
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Create new credentials with updated token information
                        new_expiry_date = None
                        if "expires_in" in response_data:
                            import datetime
                            new_expiry_date = datetime.datetime.now() + datetime.timedelta(
                                seconds=response_data["expires_in"]
                            )
                        
                        # Use the resource_url from response if provided, otherwise preserve existing one
                        resource_url = getattr(credentials, 'resource_url', None)
                        if 'resource_url' in response_data and response_data['resource_url']:
                            resource_url = response_data['resource_url']
                        
                        new_credentials = QwenCredentials(
                            access_token=response_data["access_token"],
                            refresh_token=response_data.get("refresh_token", credentials.refresh_token),
                            token_type=response_data.get("token_type", "Bearer"),
                            expiry_date=new_expiry_date,
                            resource_url=resource_url  # Preserve or update resource_url
                        )
                        
                        # Save the new credentials to file
                        if await self.save_credentials(new_credentials):
                            print("Token successfully refreshed and saved to file.")
                            return new_credentials
                        else:
                            print("Failed to save refreshed token to file.")
                            return None
                    else:                        
                        # If refresh fails with 400, we should clear the credentials
                        error_text = await response.text()
                        print(f"Token refresh failed with status {response.status}: {error_text}")
                        
                        # If it's a 400 error (likely refresh token expired), clear the credentials
                        if response.status == 400:
                            print("Refresh token may be expired, clearing credentials.")
                            await self.clear_credentials()
                        
                        return None
        except Exception as e:
            print(f"Error during token refresh: {e}")
            return None

    async def clear_credentials(self) -> bool:
        """
        Clear stored credentials.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use file lock to prevent concurrent access
            with self._get_file_lock():
                if self.credentials_file.exists():
                    self.credentials_file.unlink()
                
                # Clear in-memory cache
                async with self._cache_lock:
                    self._cached_credentials = None
                    self._cache_timestamp = 0
            
            return True
        except Exception as e:
            print(f"Error clearing credentials: {e}")
            return False