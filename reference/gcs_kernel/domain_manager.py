"""
Domain Manager for the GCS Kernel.

This module implements the DomainManager class which handles
dynamic loading of specialized domain knowledge and capabilities.
"""
import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field

from common.settings import settings


class DomainConfig(BaseModel):
    """Configuration for a domain"""
    name: str = Field(description="Name of the domain")
    description: str = Field(description="Description of the domain")
    version: str = Field(default="1.0.0", description="Version of the domain")
    author: Optional[str] = Field(default=None, description="Author of the domain")


class DomainManager:
    """Manages dynamic loading of specialized domains"""
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.domains_directory = Path(settings.domain_directory)
        self.available_domains: Dict[str, Path] = {}
        self.current_domain: Optional[str] = None
        self.system_context_builder = kernel.ai_orchestrator.system_context_builder
        self._default_prompts = None
        self._domain_loaded_tools: List[str] = []  # Track tools loaded from the current domain
        self._domain_loaded_servers: List[str] = []  # Track servers loaded from the current domain
        self._current_domain_data = {}  # Store current domain data to be accessed by system_context_builder
    
    def get_current_domain_data(self) -> Dict[str, Any]:
        """
        Get the currently loaded domain data.
        
        Returns:
            Dictionary containing domain-specific data, or empty dict if no domain is loaded
        """
        return self._current_domain_data.copy()  # Return a copy to prevent external modification
        
        # Store default prompts from the system context builder
        if hasattr(self.system_context_builder, 'prompts'):
            self._default_prompts = self.system_context_builder.prompts

    async def discover_domains(self):
        """Discover available domains in the domains directory"""
        if not self.domains_directory.exists():
            self.domains_directory.mkdir(parents=True, exist_ok=True)
            return

        for domain_dir in self.domains_directory.iterdir():
            if domain_dir.is_dir():
                metadata_path = domain_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        domain_name = metadata.get("name")
                        if domain_name:
                            self.available_domains[domain_name] = domain_dir
                    except (json.JSONDecodeError, KeyError):
                        # Skip invalid domain configurations
                        continue

    def get_available_domains(self) -> Dict[str, str]:
        """Get dictionary of available domains with their descriptions"""
        domains_info = {}
        for domain_name, domain_path in self.available_domains.items():
            metadata_path = domain_path / "metadata.json"
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                domains_info[domain_name] = metadata.get("description", "No description available")
            except (json.JSONDecodeError, FileNotFoundError):
                domains_info[domain_name] = "No description available"
        return domains_info

    def validate_domain(self, domain_name: str) -> bool:
        """Validate that a domain exists and has the required structure"""
        if domain_name not in self.available_domains:
            return False
            
        domain_path = self.available_domains[domain_name]
        
        # Check for required files
        required_files = ["metadata.json"]
        for file in required_files:
            if not (domain_path / file).exists():
                return False
                
        # Validate metadata
        try:
            with open(domain_path / "metadata.json", 'r') as f:
                metadata = json.load(f)
            
            required_fields = ["name", "description", "version"]
            for field in required_fields:
                if field not in metadata:
                    return False
                    
            # Verify domain name in metadata matches directory name
            if metadata["name"] != domain_name:
                return False
                
        except (json.JSONDecodeError, FileNotFoundError):
            return False
            
        return True

    async def load_domain(self, domain_name: str) -> bool:
        """Load a domain by name"""
        # Validate domain exists
        if not self.validate_domain(domain_name):
            return False

        # Unload current domain if one is loaded
        if self.current_domain:
            await self.unload_domain()

        domain_path = self.available_domains[domain_name]
        
        try:
            # Load domain-specific prompts
            await self._apply_domain_prompts(domain_path)

            # Register domain-specific tools
            await self._register_domain_tools(domain_path)

            # Register domain-specific MCP servers
            await self._register_domain_mcp_servers(domain_path)

            self.current_domain = domain_name
            return True
            
        except Exception:
            # If loading fails, ensure cleanup
            if self.current_domain:
                self.current_domain = None
            # Revert to default prompts if we have them
            if self._default_prompts:
                self.system_context_builder.prompts = self._default_prompts
            return False

    async def unload_domain(self) -> bool:
        """Unload the currently loaded domain"""
        if not self.current_domain:
            return True  # Nothing to unload

        try:
            # Unregister domain-specific tools
            await self._unregister_domain_tools(self.available_domains[self.current_domain])

            # Unregister domain-specific MCP servers
            await self._unregister_domain_mcp_servers(self.available_domains[self.current_domain])

            # Revert to default prompts
            await self._revert_to_default_prompts()

            self.current_domain = None
            return True
        except Exception:
            return False

    async def _apply_domain_prompts(self, domain_path: Path):
        """Load domain-specific data from the domain directory into internal state"""
        prompts_path = domain_path / "prompts.json"
        
        if prompts_path.exists():
            try:
                # Load domain data into internal state
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    domain_data = json.load(f)
                
                self._current_domain_data = domain_data.get('system_context', {})
            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                # If domain data is invalid, clear the domain data
                self._current_domain_data = {}
        else:
            # If no domain prompts exist, clear the domain data
            self._current_domain_data = {}

    async def _revert_to_default_prompts(self):
        """Revert back to the default prompts by clearing domain data"""
        self._current_domain_data = {}

    async def _register_domain_tools(self, domain_path: Path):
        """Register domain-specific tools from the domain directory"""
        # Clear the list of domain-loaded tools
        self._domain_loaded_tools = []
        
        # Check for tools.json file
        tools_path = domain_path / "tools.json"
        if tools_path.exists():
            try:
                with open(tools_path, 'r') as f:
                    tools_data = json.load(f)
                
                # Register each tool in the domain
                if isinstance(tools_data, dict) and "tools" in tools_data:
                    domain_tools = tools_data["tools"]
                else:
                    domain_tools = tools_data  # Assume it's a list of tools directly
                
                if isinstance(domain_tools, list):
                    for tool_def in domain_tools:
                        # Register the tool with the kernel registry
                        from gcs_kernel.models import ToolDefinition
                        tool_definition = ToolDefinition(**tool_def)
                        self.kernel.registry.register_tool(tool_definition)
                        self._domain_loaded_tools.append(tool_definition.name)
            except (json.JSONDecodeError, FileNotFoundError, Exception):
                # If tools couldn't be loaded, continue without error
                pass

        # Also check for tools directory with individual tool files
        tools_dir = domain_path / "tools"
        if tools_dir.exists() and tools_dir.is_dir():
            for tool_file in tools_dir.glob("*.json"):
                try:
                    with open(tool_file, 'r') as f:
                        tool_def = json.load(f)
                    
                    from gcs_kernel.models import ToolDefinition
                    tool_definition = ToolDefinition(**tool_def)
                    self.kernel.registry.register_tool(tool_definition)
                    self._domain_loaded_tools.append(tool_definition.name)
                except (json.JSONDecodeError, Exception):
                    # Skip invalid tool files
                    continue

    async def _unregister_domain_tools(self, domain_path: Path):
        """Unregister domain-specific tools"""
        # Unregister only the tools that were loaded from the current domain
        for tool_name in self._domain_loaded_tools:
            try:
                # For local tools, we need to remove them from the registry
                if tool_name in self.kernel.registry.tools:
                    del self.kernel.registry.tools[tool_name]
            except Exception:
                # If there's an error removing a tool, continue with others
                continue
        
        # Clear the list of domain-loaded tools
        self._domain_loaded_tools = []

    async def _register_domain_mcp_servers(self, domain_path: Path):
        """Register domain-specific MCP servers from the domain directory"""
        # Clear the list of domain-loaded servers
        self._domain_loaded_servers = []
        
        # Check for mcp_servers.json file
        mcp_servers_path = domain_path / "mcp_servers.json"
        if mcp_servers_path.exists():
            try:
                with open(mcp_servers_path, 'r') as f:
                    mcp_servers_data = json.load(f)
                
                # Connect to each MCP server specified in the domain
                if isinstance(mcp_servers_data, list):
                    for server_info in mcp_servers_data:
                        server_url = server_info.get("server_url")
                        server_name = server_info.get("name", f"domain_server_{len(self.kernel.mcp_client_manager.clients)}")
                        server_description = server_info.get("description", "Domain-specific MCP server")
                        
                        if server_url:
                            # Connect to the MCP server
                            success = await self.kernel.mcp_client_manager.connect_to_server(
                                server_url, server_name, server_description
                            )
                            if success:
                                # We can't easily get the server ID from the URL, so we'll track by URL for now
                                # For proper implementation, we'd need to enhance the MCPClientManager to return the server ID
                                self._domain_loaded_servers.append(server_url)
            except (json.JSONDecodeError, FileNotFoundError, Exception):
                # If servers couldn't be loaded, continue without error
                pass

        # Also check for mcp_servers directory with individual server files
        mcp_servers_dir = domain_path / "mcp_servers"
        if mcp_servers_dir.exists() and mcp_servers_dir.is_dir():
            for server_file in mcp_servers_dir.glob("*.json"):
                try:
                    with open(server_file, 'r') as f:
                        server_info = json.load(f)
                    
                    server_url = server_info.get("server_url")
                    server_name = server_info.get("name", f"domain_server_{len(self.kernel.mcp_client_manager.clients)}")
                    server_description = server_info.get("description", "Domain-specific MCP server")
                    
                    if server_url:
                        success = await self.kernel.mcp_client_manager.connect_to_server(
                            server_url, server_name, server_description
                        )
                        if success:
                            # We can't easily get the server ID from the URL, so we'll track by URL for now
                            self._domain_loaded_servers.append(server_url)
                except (json.JSONDecodeError, Exception):
                    # Skip invalid server files
                    continue

    async def _unregister_domain_mcp_servers(self, domain_path: Path):
        """Unregister domain-specific MCP servers"""
        # Disconnect only the servers that were loaded from the current domain
        for server_url in self._domain_loaded_servers:
            try:
                # Find the server ID by URL from the MCP client manager
                server_id = None
                for id, client_info in self.kernel.mcp_client_manager.clients.items():
                    if client_info.get('server_url') == server_url:
                        server_id = id
                        break
                
                if server_id:
                    await self.kernel.mcp_client_manager.disconnect_from_server(server_id)
            except Exception:
                # If there's an error disconnecting a server, continue with others
                continue
        
        # Clear the list of domain-loaded servers
        self._domain_loaded_servers = []