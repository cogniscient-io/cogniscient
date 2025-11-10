"""
MCP (Model Context Protocol) tools for the GCS Kernel.

This module implements tools for managing and interacting with MCP servers.
"""

import hashlib
from typing import Dict, Any
from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class MCPServerListTool:
    """
    System tool to list all registered MCP servers.
    """
    name = "list_mcp_servers"
    display_name = "List MCP Servers"
    description = "List all registered MCP servers with their status and details"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the list MCP servers tool.
        
        Args:
            parameters: The parameters for tool execution (none required)
            
        Returns:
            A ToolResult containing the execution result
        """
        try:
            # Get the client manager from the kernel
            if not self.kernel or not hasattr(self.kernel, 'mcp_client_manager') or self.kernel.mcp_client_manager is None:
                result = "MCP client manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=result,
                    llm_content=result,
                    return_display=result
                )
            
            # Get detailed server information
            servers = await self.kernel.mcp_client_manager.list_known_servers_detailed()
            
            if not servers:
                result = "No MCP servers are currently registered."
            else:
                server_list = []
                for server_info in servers:
                    server_list.append(
                        f"  - ID: {server_info.server_id}, URL: {server_info.server_url}, "
                        f"Name: {server_info.name}, Status: {server_info.status}"
                    )
                
                result = "Registered MCP Servers:\n" + "\n".join(server_list)
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error listing MCP servers: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class MCPServerStatusTool:
    """
    System tool to get the status of a specific MCP server.
    """
    name = "get_mcp_server_status"
    display_name = "Get MCP Server Status"
    description = "Get the connection status of a specific MCP server"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "The unique identifier of the MCP server to check"
            }
        },
        "required": ["server_id"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the get MCP server status tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        server_id = parameters.get("server_id")
        
        if not server_id:
            error_msg = "Missing required parameter: server_id"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Get the client manager from the kernel
            if not self.kernel or not hasattr(self.kernel, 'mcp_client_manager'):
                error_msg = "MCP client manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Check if server exists in registry
            server_exists = await self.kernel.mcp_client_manager.server_exists(server_id)
            if not server_exists:
                error_msg = f"MCP server with ID '{server_id}' not found in registry"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Get detailed server information
            servers = await self.kernel.mcp_client_manager.list_known_servers_detailed()
            server_info = None
            for s in servers:
                if s.server_id == server_id:
                    server_info = s
                    break
            
            if not server_info:
                error_msg = f"MCP server with ID '{server_id}' details not found"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            result = (
                f"MCP Server Status:\n"
                f"  ID: {server_info.server_id}\n"
                f"  URL: {server_info.server_url}\n"
                f"  Name: {server_info.name}\n"
                f"  Description: {server_info.description}\n"
                f"  Status: {server_info.status}\n"
                f"  Capabilities: {server_info.capabilities}\n"
                f"  Last Connected: {server_info.last_connected}"
            )
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error getting MCP server status for '{server_id}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class MCPServerConnectTool:
    """
    System tool to connect to an MCP server.
    """
    name = "connect_mcp_server"
    display_name = "Connect MCP Server"
    description = "Connect to an MCP server by specifying its URL"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "server_url": {
                "type": "string",
                "description": "The URL of the MCP server to connect to (e.g., http://localhost:8080)"
            },
            "server_name": {
                "type": "string",
                "description": "An optional name to assign to this server connection"
            },
            "description": {
                "type": "string",
                "description": "An optional description for this server connection"
            }
        },
        "required": ["server_url"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the connect MCP server tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        server_url = parameters.get("server_url")
        server_name = parameters.get("server_name")
        description = parameters.get("description")
        
        # Validate required parameters
        if not server_url:
            error_msg = "Missing required parameter: server_url"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Get the client manager from the kernel
            if not self.kernel or not hasattr(self.kernel, 'mcp_client_manager'):
                error_msg = "MCP client manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Attempt to connect to the MCP server using the official Streamable HTTP protocol
            success = await self.kernel.mcp_client_manager.connect_to_server(
                server_url,
                server_name,
                description
            )
            
            if success:
                # Generate server ID from URL (similar to how client manager does it)
                server_id = hashlib.md5(server_url.encode()).hexdigest()
                
                # The tools will be automatically registered via the event system triggered by the connection
                # The MCP client manager emits a 'tools_discovered' event which will be handled by the tool discovery service
                server_info = self.kernel.mcp_client_manager.server_registry.get_server(server_id)

                result = f"Successfully connected to MCP server '{server_id}' at {server_url} using official Streamable HTTP protocol. Discovered {len(server_info.capabilities) if server_info else 0} tools: {', '.join(server_info.capabilities) if server_info and server_info.capabilities else 'None'}"
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    llm_content=result,
                    return_display=result
                )
            else:
                error_msg = f"Failed to connect to MCP server at {server_url} - server may not support the official Streamable HTTP protocol"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
        except Exception as e:
            error_msg = f"Error connecting to MCP server at {server_url}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class MCPServerDisconnectTool:
    """
    System tool to disconnect from an MCP server.
    """
    name = "disconnect_mcp_server"
    display_name = "Disconnect MCP Server"
    description = "Disconnect from an MCP server by specifying its ID"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "The unique identifier of the MCP server to disconnect"
            }
        },
        "required": ["server_id"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the disconnect MCP server tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        server_id = parameters.get("server_id")
        
        if not server_id:
            error_msg = "Missing required parameter: server_id"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Get the client manager from the kernel
            if not self.kernel or not hasattr(self.kernel, 'mcp_client_manager'):
                error_msg = "MCP client manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Check if server exists in registry
            server_exists = await self.kernel.mcp_client_manager.server_exists(server_id)
            if not server_exists:
                error_msg = f"MCP server with ID '{server_id}' not found in registry"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Attempt to disconnect from the MCP server
            success = await self.kernel.mcp_client_manager.disconnect_from_server(server_id)
            
            if success:
                result = f"Successfully disconnected from MCP server '{server_id}'"
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    llm_content=result,
                    return_display=result
                )
            else:
                error_msg = f"Failed to disconnect from MCP server '{server_id}'. Server may not be connected."
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
        except Exception as e:
            error_msg = f"Error disconnecting from MCP server '{server_id}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class MCPServerRemoveTool:
    """
    System tool to remove an MCP server from the registry (disconnects if connected).
    """
    name = "remove_mcp_server"
    display_name = "Remove MCP Server"
    description = "Remove an MCP server from the registry, disconnecting if currently connected"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "The unique identifier of the MCP server to remove"
            }
        },
        "required": ["server_id"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the remove MCP server tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        server_id = parameters.get("server_id")
        
        if not server_id:
            error_msg = "Missing required parameter: server_id"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Get the client manager from the kernel
            if not self.kernel or not hasattr(self.kernel, 'mcp_client_manager'):
                error_msg = "MCP client manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Check if server exists in registry
            server_exists = await self.kernel.mcp_client_manager.server_exists(server_id)
            if not server_exists:
                error_msg = f"MCP server with ID '{server_id}' not found in registry"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Remove the server (this disconnects if connected)
            success = await self.kernel.mcp_client_manager.remove_known_server(server_id)
            
            if success:
                # Get the server info to handle tool cleanup
                server_info = self.kernel.mcp_client_manager.server_registry.get_server(server_id)
                
                # Notify the tool discovery service that the server has been removed,
                # which will handle cleaning up all associated tools
                try:
                    if server_info and server_info.capabilities:
                        await self.kernel.tool_discovery_service.handle_server_disconnect(server_id)
                except Exception as e:
                    if self.kernel.logger:
                        self.kernel.logger.error(f"Error notifying tool discovery service of server removal: {e}")

                result = f"Successfully removed MCP server '{server_id}' from registry. Cleaned up associated tools: {', '.join(server_info.capabilities) if server_info and server_info.capabilities else 'None'}"
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    llm_content=result,
                    return_display=result
                )
            else:
                error_msg = f"Failed to remove MCP server '{server_id}' from registry"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
        except Exception as e:
            error_msg = f"Error removing MCP server '{server_id}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


# List of all MCP tools to register
MCP_TOOLS = [
    MCPServerListTool,
    MCPServerStatusTool,
    MCPServerConnectTool,
    MCPServerDisconnectTool,
    MCPServerRemoveTool
]


async def register_mcp_tools(kernel) -> bool:
    """
    Register all MCP-related tools with the kernel registry.
    This should be called after the kernel and registry are initialized.
    
    Args:
        kernel: The GCSKernel instance
        
    Returns:
        True if registration was successful, False otherwise
    """
    import time
    start_time = time.time()
    
    from gcs_kernel.registry import ToolRegistry
    
    # Check if the kernel and registry are available
    if not kernel or not hasattr(kernel, 'registry') or kernel.registry is None:
        if hasattr(kernel, 'logger') and kernel.logger:
            try:
                kernel.logger.error("Kernel registry not available for MCP tool registration")
            except TypeError:
                # Handle case where logger is a MagicMock
                if hasattr(kernel.logger, '_mock_name'):
                    kernel.logger.error("Kernel registry not available for MCP tool registration")
                else:
                    raise
        return False

    registry = kernel.registry
    
    if hasattr(kernel, 'logger') and kernel.logger:
        try:
            kernel.logger.debug("Starting MCP tools registration...")
        except TypeError:
            # Handle case where logger is a MagicMock
            if hasattr(kernel.logger, '_mock_name'):
                kernel.logger.debug("Starting MCP tools registration...")
            else:
                raise
    
    # List of MCP tools to register
    mcp_tools = [
        MCPServerListTool(kernel),
        MCPServerStatusTool(kernel),
        MCPServerConnectTool(kernel),
        MCPServerDisconnectTool(kernel),
        MCPServerRemoveTool(kernel)
    ]
    
    # Register each MCP tool
    for tool in mcp_tools:
        if hasattr(kernel, 'logger') and kernel.logger:
            try:
                kernel.logger.debug(f"Registering MCP tool: {tool.name}")
            except TypeError:
                # Handle case where logger is a MagicMock
                if hasattr(kernel.logger, '_mock_name'):
                    kernel.logger.debug(f"Registering MCP tool: {tool.name}")
                else:
                    raise
        
        success = await registry.register_tool(tool)
        if not success:
            if hasattr(kernel, 'logger') and kernel.logger:
                try:
                    kernel.logger.error(f"Failed to register MCP tool: {tool.name}")
                except TypeError:
                    # Handle case where logger is a MagicMock
                    if hasattr(kernel.logger, '_mock_name'):
                        kernel.logger.error(f"Failed to register MCP tool: {tool.name}")
                    else:
                        raise
            return False
    
    elapsed = time.time() - start_time
    if hasattr(kernel, 'logger') and kernel.logger:
        try:
            kernel.logger.info(f"Successfully registered {len(mcp_tools)} MCP tools (elapsed: {elapsed:.2f}s)")
        except TypeError:
            # Handle case where logger is a MagicMock
            if hasattr(kernel.logger, '_mock_name'):
                kernel.logger.info(f"Successfully registered {len(mcp_tools)} MCP tools (elapsed: {elapsed:.2f}s)")
            else:
                raise
    
    return True


