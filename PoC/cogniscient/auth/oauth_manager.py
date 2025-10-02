import asyncio
import webbrowser
from typing import Optional
from .providers import QwenOAuth2Client, DeviceAuthData, DeviceTokenData, DeviceTokenPendingData, DeviceTokenSlowDownData, DeviceTokenErrorData
from .token_manager import TokenManager, QwenCredentials
from .utils import generate_pkce_pair


class OAuthManager:
    """Manages OAuth flows and coordinates between token manager and OAuth client."""
    
    def __init__(
        self,
        client_id: str,
        authorization_server: str = "https://chat.qwen.ai",
        credentials_file: Optional[str] = None,
        credentials_dir: Optional[str] = None
    ):
        """
        Initialize the OAuth Manager.
        
        Args:
            client_id: OAuth client ID
            authorization_server: Base URL of the authorization server
            credentials_file: Path to credentials file
            credentials_dir: Directory to store credentials
        """
        self.client_id = client_id
        self.authorization_server = authorization_server
        self.token_manager = TokenManager(credentials_file, credentials_dir)
        self.auth_client = QwenOAuth2Client(client_id, authorization_server)

    async def authenticate_with_device_flow(
        self,
        scope: str = "openid profile email model.completion",
        audience: Optional[str] = None,
        open_browser: bool = True
    ) -> bool:
        """
        Perform OAuth device authorization flow.
        
        Args:
            scope: OAuth scopes to request
            audience: Optional audience parameter
            open_browser: Whether to automatically open the browser for user verification
            
        Returns:
            True if authentication was successful, False otherwise
        """
        # Generate PKCE code verifier and challenge
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Request device authorization
        device_auth: Optional[DeviceAuthData] = await self.auth_client.request_device_authorization(
            scope=scope,
            audience=audience
        )
        
        if not device_auth:
            print("Failed to initiate device authorization flow")
            return False
        
        # Display verification URI to user
        print(f"Visit: {device_auth.verification_uri_complete}")
        print(f"User Code: {device_auth.user_code}")
        
        # Optionally open the verification URL in default browser
        if open_browser:
            try:
                webbrowser.open(device_auth.verification_uri_complete)
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print("Please manually visit the URL above to continue.")
        
        # Poll for token (with appropriate delays as specified by server)
        interval = device_auth.interval  # Use the interval recommended by the server
        
        while True:
            token_response = await self.auth_client.poll_device_token(
                device_code=device_auth.device_code,
                code_verifier=code_verifier,
                interval=interval
            )
            
            if isinstance(token_response, DeviceTokenData):
                # Success - save credentials
                expiry_date = None
                if hasattr(token_response, 'expires_in'):
                    from datetime import datetime, timedelta
                    expiry_date = datetime.now() + timedelta(seconds=token_response.expires_in)
                
                credentials = QwenCredentials(
                    access_token=token_response.access_token,
                    refresh_token=token_response.refresh_token,
                    token_type=token_response.token_type,
                    expiry_date=expiry_date
                )
                
                save_success = await self.token_manager.save_credentials(credentials)
                if save_success:
                    print("Authentication successful! Credentials saved.")
                    return True
                else:
                    print("Authentication successful but failed to save credentials.")
                    return False
                    
            elif isinstance(token_response, DeviceTokenPendingData):
                # Wait and retry - use the interval from the server
                await asyncio.sleep(interval)
                
            elif isinstance(token_response, DeviceTokenSlowDownData):
                # Server asked us to slow down, increase polling interval by 5 seconds
                interval += 5
                await asyncio.sleep(interval)
                
            elif isinstance(token_response, DeviceTokenErrorData):
                # Error occurred
                print(f"OAuth error: {token_response.error} - {token_response.error_description}")
                
                # Handle specific error cases
                if token_response.error == "expired_token":
                    print("Device code expired. Please restart the authentication process.")
                    return False
                elif token_response.error == "access_denied":
                    print("Access denied by user. Authentication cancelled.")
                    return False
                else:
                    print(f"Authentication failed: {token_response.error_description}")
                    return False
            else:
                # Unexpected response type
                print("Unexpected response from authorization server")
                return False

    async def refresh_access_token(self) -> Optional[QwenCredentials]:
        """
        Refresh the access token using the stored refresh token.
        
        Returns:
            New QwenCredentials if refresh was successful, None otherwise
        """
        # Get current credentials
        current_credentials = await self.token_manager.load_credentials()
        if not current_credentials or not current_credentials.refresh_token:
            print("No refresh token available")
            return None

        # Use the refresh token to get new credentials
        new_credentials = await self.auth_client.refresh_access_token(
            current_credentials.refresh_token
        )
        
        if new_credentials:
            # Save the new credentials
            save_success = await self.token_manager.save_credentials(new_credentials)
            if save_success:
                print("Access token refreshed successfully")
                return new_credentials
            else:
                print("Failed to save refreshed credentials")
                return None
        else:
            print("Failed to refresh access token")
            return None

    async def get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token if available, None otherwise
        """
        return await self.token_manager.get_valid_access_token()

    async def has_valid_credentials(self) -> bool:
        """
        Check if valid credentials exist.
        
        Returns:
            True if valid credentials exist, False otherwise
        """
        return await self.token_manager.has_valid_credentials()

    async def clear_credentials(self) -> bool:
        """
        Clear stored credentials.
        
        Returns:
            True if successful, False otherwise
        """
        return await self.token_manager.clear_credentials()

    async def close(self):
        """Close any resources held by the manager."""
        await self.auth_client.close()