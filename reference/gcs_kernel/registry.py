"""
Tool Registry System implementation for the GCS Kernel.

This module implements the ToolRegistry class which manages available tools,
their registration, and discovery (command-based and MCP-based).
"""

import asyncio
from typing import Dict, Any, Optional, Protocol
from gcs_kernel.models import ToolDefinition, ToolResult, ToolApprovalMode


class BaseTool(Protocol):
    """
    Base interface for all tools in the GCS Kernel.
    
    All tools must implement this interface to be compatible with the kernel.
    """
    
    name: str
    display_name: str
    description: str
    parameters: Dict[str, Any]  # Following OpenAI-compatible format
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        ...


class ToolRegistry:
    """
    Tool Registry System that manages available tools, their registration,
    and discovery (command-based and MCP-based).
    """
    
    def __init__(self, mcp_client_manager=None):
        """Initialize the tool registry with necessary components."""
        self.tools: Dict[str, BaseTool] = {}  # Local tools only
        # Map external tool names to their MCP client configuration
        self.external_tool_mcp_configs: Dict[str, str] = {}  # Maps tool names to MCP client server URLs
        self.mcp_clients: Dict[str, Any] = {}  # MCP client instances by server URL
        self.mcp_client_manager = mcp_client_manager  # Reference to MCP client manager
        self.logger = None  # Will be set by kernel

    async def initialize(self, kernel=None):
        """Initialize the registry."""
        # Register built-in tools
        await self._register_built_in_tools(kernel=kernel)

    async def shutdown(self):
        """Shutdown the registry."""
        pass

    async def _register_built_in_tools(self, kernel=None):
        """Register built-in tools available to the kernel."""
        # For now, keep a minimal initialization that doesn't register specific tools
        # All tools will be registered after the registry initialization is complete
        if self.logger:
            self.logger.info("Registry initialized with no pre-registered tools - all tools will be registered post-initialization")

    async def register_tool(self, tool: BaseTool) -> bool:
        """
        Register a new tool with the registry.
        
        Args:
            tool: The tool to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Validate the tool
            if not hasattr(tool, 'name') or not hasattr(tool, 'execute'):
                if self.logger:
                    self.logger.error(f"Invalid tool: missing required attributes: {tool}")
                return False
            
            # Add the tool to the registry
            self.tools[tool.name] = tool
            
            if self.logger:
                self.logger.info(f"Tool registered: {tool.name}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to register tool: {e}")
            return False

    async def unregister_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: The name of the tool to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            # Try to remove from both local tools and external tools
            removed = False
            if tool_name in self.tools:
                del self.tools[tool_name]
                removed = True
                
            if tool_name in self.external_tool_mcp_configs:
                del self.external_tool_mcp_configs[tool_name]
                removed = True
                
            if removed and self.logger:
                self.logger.info(f"Tool unregistered: {tool_name}")
            
            return removed
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to unregister tool: {e}")
            return False

    async def update_tool(self, tool_definition: ToolDefinition) -> bool:
        """
        Update an existing tool in the registry.
        
        Args:
            tool_definition: The updated tool definition
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Check if tool exists
            if tool_definition.name not in self.tools:
                # If tool doesn't exist, register it
                await self.register_tool(tool_definition)
                return True
            
            # Update the existing tool
            self.tools[tool_definition.name] = tool_definition
            
            if self.logger:
                self.logger.info(f"Tool updated: {tool_definition.name}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to update tool: {e}")
            return False

    async def deregister_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: The name of the tool to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        # This is an alias for unregister_tool to maintain backward compatibility
        return await self.unregister_tool(tool_name)

    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a local tool by its name from the registry.
        
        Args:
            tool_name: The name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(tool_name)

    async def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists in the registry (either local or registered external).
        
        Args:
            tool_name: The name of the tool to check
            
        Returns:
            True if the tool exists in either local registry or is registered as external
        """
        # Check if it's a local tool
        if tool_name in self.tools:
            return True
        
        # Check if it's registered as an external tool
        return tool_name in self.external_tool_mcp_configs

    async def get_tool_server_config(self, tool_name: str) -> Optional[str]:
        """
        Get the server config (URL) for a tool (for external tools) or None for local tools.
        
        Args:
            tool_name: The name of the tool to look up
            
        Returns:
            Server URL if the tool is external, None if it's local, None if not found
        """
        # If it's an external tool (exists in external_tool_mcp_configs), return the server URL
        if tool_name in self.external_tool_mcp_configs:
            return self.external_tool_mcp_configs[tool_name]

        # If it's only in the local tools registry, return None (indicating local tool)
        if tool_name in self.tools:
            return None

        # If it doesn't exist at all, return None
        return None

    async def register_external_tool(self, tool_name: str, server_url: str) -> bool:
        """
        Register an external tool that is available via an MCP server.
        
        Args:
            tool_name: Name of the external tool
            server_url: URL of the MCP server hosting the tool
            
        Returns:
            True if registration was successful
        """
        try:
            # Register the tool with its server configuration
            self.external_tool_mcp_configs[tool_name] = server_url
            
            # Create a dynamic external tool instance that routes calls to the MCP server
            # This tool instance will be added to the main tools registry
            external_tool_instance = self._create_external_tool_wrapper(tool_name, server_url)
            
            # Add the external tool to the main tools registry so it appears in get_all_tools()
            self.tools[tool_name] = external_tool_instance
            
            if self.logger:
                self.logger.info(f"External tool registered: {tool_name} on {server_url}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to register external tool {tool_name}: {e}")
            return False

    def _create_external_tool_wrapper(self, tool_name: str, server_url: str):
        """
        Create a wrapper tool instance for an external tool that routes execution to the MCP server.
        
        Args:
            tool_name: Name of the external tool
            server_url: URL of the server hosting the tool
            
        Returns:
            A tool instance that wraps external tool execution
        """
        # Create a dynamic class that implements BaseTool for the external tool
        class MCPExternalToolWrapper:
            def __init__(self, wrapper_tool_name, wrapper_server_url, registry_instance):
                self.name = wrapper_tool_name
                self.display_name = f"{wrapper_tool_name} (external)"
                self.description = f"External tool '{wrapper_tool_name}' available via MCP server at {wrapper_server_url}"
                # Default parameters schema - in real implementation, this would come from the actual tool schema
                self.parameters = {"type": "object", "properties": {}, "required": []}
                self._server_url = wrapper_server_url
                self._registry = registry_instance  # Keep reference to registry for MCP client access

            async def execute(self, parameters):
                # This execution should be handled by the ToolExecutionManager with proper MCP routing
                # For the registry's purposes, we return a result indicating it's an external tool
                from gcs_kernel.models import ToolResult
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"External tool '{self.name}' execution must be handled by ToolExecutionManager with proper MCP routing",
                    llm_content=f"External tool '{self.name}' available but requires MCP client routing for execution",
                    return_display=f"External tool '{self.name}' available on server but requires proper routing"
                )
        
        return MCPExternalToolWrapper(tool_name, server_url, self)

    async def get_mcp_client_for_tool(self, tool_name: str) -> Optional[Any]:
        """
        Get the MCP client instance for a tool.
        
        Args:
            tool_name: Name of the tool to get client for
            
        Returns:
            MCP client instance if available, None otherwise
        """
        server_url = self.external_tool_mcp_configs.get(tool_name)
        if not server_url:
            return None
        
        # First try to get client from the client manager, if available
        if self.mcp_client_manager:
            try:
                # Use the client manager's method to get client for a specific tool
                client = await self.mcp_client_manager.get_client_for_tool(tool_name)
                if client:
                    return client
            except Exception:
                # If client manager method fails, fall back to manual client creation
                pass

        # If client manager isn't available or doesn't have the client, use cached or create new one
        if server_url not in self.mcp_clients:
            # Create and initialize an MCP client for this server using the new architecture
            from gcs_kernel.mcp.client import MCPClient
            from gcs_kernel.mcp.client_manager import MCPConnection

            # Create a direct connection using the new pattern
            connection = MCPConnection(server_url)
            client = await connection.connect()
            client.logger = self.logger

            self.mcp_clients[server_url] = client

        return self.mcp_clients[server_url]
        
    async def deregister_external_tool(self, tool_name: str) -> bool:
        """
        Remove an external tool from the registry.
        
        Args:
            tool_name: The name of the external tool to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            success = False
            # Remove from external tool configurations
            if tool_name in self.external_tool_mcp_configs:
                del self.external_tool_mcp_configs[tool_name]
                success = True
                
            # Also remove from main tools registry if present
            if tool_name in self.tools:
                del self.tools[tool_name]
                
            if self.logger and success:
                self.logger.info(f"External tool deregistered: {tool_name}")
            
            return success
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to deregister external tool: {e}")
            return False

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            A dictionary of all registered tools
        """
        return self.tools.copy()

    async def discover_command_based_tools(self) -> Dict[str, BaseTool]:
        """
        Discover tools using command-based discovery mechanism.
        
        Returns:
            A dictionary of discovered tools
        """
        # In a real system, this would search for available command-line tools
        # For now, return a basic set of command-based tools
        discovered_tools = {}
        
        # Check for common command-line tools
        import shutil
        
        # Example: Check for git
        if shutil.which("git"):
            git_tool = self._create_command_tool("git", "Git Version Control", "Execute git commands", {
                "type": "object",
                "properties": {
                    "subcommand": {
                        "type": "string",
                        "description": "Git subcommand to execute (e.g., status, log, commit)"
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional arguments for the git command"
                    }
                },
                "required": ["subcommand"]
            })
            discovered_tools["git"] = git_tool
        
        # Example: Check for docker
        if shutil.which("docker"):
            docker_tool = self._create_command_tool("docker", "Docker", "Execute docker commands", {
                "type": "object",
                "properties": {
                    "subcommand": {
                        "type": "string",
                        "description": "Docker subcommand to execute (e.g., run, ps, images)"
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional arguments for the docker command"
                    }
                },
                "required": ["subcommand"]
            })
            discovered_tools["docker"] = docker_tool
            
        return discovered_tools
    
    def _create_command_tool(self, name: str, display_name: str, description: str, parameter_schema: Dict[str, Any]):
        """
        Create a dynamic command-based tool.
        
        Args:
            name: The tool name
            display_name: The display name
            description: The tool description
            parameter_schema: The parameter schema for the tool
            
        Returns:
            A dynamic tool object that implements the BaseTool protocol
        """
        import subprocess
        
        class DynamicCommandTool:
            def __init__(self, name, display_name, description, parameter_schema):
                self.name = name
                self.display_name = display_name
                self.description = description
                self.parameters = parameter_schema  # Use parameters as per OpenAI format
                
            async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
                # Build the command to execute
                command = [self.name]
                
                # Add subcommand if provided
                subcommand = parameters.get("subcommand", "")
                if subcommand:
                    command.append(subcommand)
                
                # Add additional arguments if provided
                args = parameters.get("args", "")
                if args:
                    command.extend(args.split())
                
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        output = result.stdout
                        success = True
                    else:
                        output = f"Command failed with exit code {result.returncode}\n{result.stderr}"
                        success = False
                    
                    return ToolResult(
                        tool_name=self.name,
                        success=success,
                        llm_content=output,
                        return_display=output
                    )
                except subprocess.TimeoutExpired:
                    error_msg = f"Command '{' '.join(command)}' timed out"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
                except Exception as e:
                    error_msg = f"Error executing command '{' '.join(command)}': {str(e)}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
        
        return DynamicCommandTool(name, display_name, description, parameter_schema)

    async def discover_mcp_based_tools(self) -> Dict[str, BaseTool]:
        """
        Discover tools using MCP-based discovery mechanism.
        
        Returns:
            A dictionary of discovered tools
        """
        # In a real system, this would connect to MCP servers via HTTP clients
        # and discover tools using the /capabilities endpoint
        # For now, return an empty dictionary
        return {}