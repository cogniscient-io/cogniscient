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
    
    def __init__(self):
        """Initialize the tool registry with necessary components."""
        self.tools: Dict[str, BaseTool] = {}  # Local tools only
        # Map external tool names to their MCP client configuration
        self.external_tool_mcp_configs: Dict[str, str] = {}  # Maps tool names to MCP client server URLs
        self.mcp_clients: Dict[str, Any] = {}  # MCP client instances by server URL
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
        # Import built-in tools
        from gcs_kernel.tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool
        from gcs_kernel.tools.shell_command import ShellCommandTool
        from gcs_kernel.tools.system_tools import ListToolsTool, GetToolInfoTool, SetLogLevelTool
        
        # Create instances of built-in tools
        tools_to_register = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            ShellCommandTool()
        ]
        
        # Register each built-in tool
        for tool in tools_to_register:
            # Use the default approval mode for built-in tools
            # In a real system, you might want to set different approval modes based on tool risk
            await self.register_tool(tool)
        
        # Register system tools that need access to the kernel
        if kernel:
            system_tools = [
                ListToolsTool(kernel),
                GetToolInfoTool(kernel),
                SetLogLevelTool(kernel)
            ]
            
            for tool in system_tools:
                await self.register_tool(tool)

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

    async def deregister_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: The name of the tool to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                
                if self.logger:
                    self.logger.info(f"Tool deregistered: {tool_name}")
                
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to deregister tool: {e}")
            return False

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
        # If it's a local tool, return None
        if tool_name in self.tools:
            return None
        
        # If it's an external tool, return the server URL from the config
        return self.external_tool_mcp_configs.get(tool_name)

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
            
            if self.logger:
                self.logger.info(f"External tool registered: {tool_name} on {server_url}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to register external tool {tool_name}: {e}")
            return False

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
        
        # Return the cached client or create a new one if needed
        if server_url not in self.mcp_clients:
            # Create and initialize an MCP client for this server
            from gcs_kernel.mcp.client import MCPClient
            from gcs_kernel.models import MCPConfig
            
            config = MCPConfig(server_url=server_url)
            client = MCPClient(config)
            client.logger = self.logger
            await client.initialize()
            
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
            if tool_name in self.external_tool_mcp_configs:
                del self.external_tool_mcp_configs[tool_name]
                
                if self.logger:
                    self.logger.info(f"External tool deregistered: {tool_name}")
                
                return True
            return False
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