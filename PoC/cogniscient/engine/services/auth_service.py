"""Auth Service implementation following the ringed architecture."""

from typing import Any, Dict, Optional
from cogniscient.engine.services.service_interface import AuthServiceInterface
from cogniscient.auth.token_manager import TokenManager


class AuthServiceImpl(AuthServiceInterface):
    """Implementation of AuthService following the ringed architecture."""
    
    def __init__(self, credentials_file: Optional[str] = None, credentials_dir: Optional[str] = None):
        """Initialize the auth service.
        
        Args:
            credentials_file: Path to the credentials file
            credentials_dir: Directory to store credentials
        """
        self.token_manager = TokenManager(
            credentials_file=credentials_file,
            credentials_dir=credentials_dir
        )
        
    async def initialize(self) -> bool:
        """Initialize the auth service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check if we have existing valid credentials
        # await self.token_manager.has_valid_credentials()  # Could check this in a real implementation
        return True  # Always return True for now, in a real implementation we might check more
        
    async def shutdown(self) -> bool:
        """Shutdown the auth service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # For now, there's nothing special to do on shutdown for auth
        return True

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate a user.
        
        Args:
            credentials: Dictionary containing authentication credentials
            
        Returns:
            True if authentication was successful, False otherwise
        """
        # For now, we'll just check if we have valid stored credentials
        # In a real implementation, this would validate the provided credentials
        return await self.token_manager.has_valid_credentials()

    async def get_token(self) -> Optional[str]:
        """Get an authentication token.
        
        Returns:
            Valid access token if available, None otherwise
        """
        return await self.token_manager.get_valid_access_token()

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the auth service.
        Note: Only safe methods are exposed - credential validation is NOT exposed for security reasons.
        """
        if not hasattr(self, 'gcs_runtime') or not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register get token tool - only allows getting tokens for already authenticated entities
        get_token_tool = {
            "name": "auth_get_token",
            "description": "Get an authentication token if valid credentials exist",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            get_token_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            get_token_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool