"""MCP Client Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) client role,
enabling the system to connect to external agent MCP servers.
"""

from typing import List, Dict, Any, Optional
import httpx
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import StreamableHTTPTransport
from mcp import stdio_client
import anyio
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cogniscient.engine.gcs_runtime import GCSRuntime
from .mcp_registry import MCPConnectionRegistry, MCPConnectionData
import asyncio
from contextlib import asynccontextmanager


# Define an interface for connection managers to handle different connection types
class ConnectionManager:
    """Base class for connection managers."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize(self) -> None:
        """Initialize the connection."""
        pass
    
    async def close(self) -> None:
        """Close the connection."""
        pass
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        pass
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool with given arguments."""
        pass


class StdioConnectionManager(ConnectionManager):
    """Connection manager for stdio-based connections."""
    
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__()  # Initialize the logger
        
        self.connection_params = connection_params
        self.client_session: Optional[ClientSession] = None
        
        # Extract timeout from connection parameters (default to 30 seconds)
        self.timeout = connection_params.get("timeout", 30)
        
        # Create server parameters - use the correct constructor
        command = connection_params["command"]
        args = connection_params.get("args", [])
        env = connection_params.get("env", {})
        
        # StdioServerParameters expects command, args, env directly as parameters
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
    
    async def initialize(self) -> None:
        """Initialize the stdio client connection."""
        try:
            from mcp import stdio_client
            # Add timeout handling using asyncio.wait_for
            self.client_session = await asyncio.wait_for(
                stdio_client(server=self.server_params),
                timeout=self.timeout
            )
            await asyncio.wait_for(
                self.client_session.initialize(),
                timeout=self.timeout
            )
            self.logger.info(f"Successfully initialized stdio connection to {self.server_params.command}")
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout during stdio connection initialization to {self.server_params.command} after {self.timeout} seconds")
        except Exception as e:
            error_msg = f"Failed to initialize stdio connection to {self.server_params.command}: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    async def close(self) -> None:
        """Close the stdio client connection."""
        try:
            if self.client_session:
                await self.client_session.close()
                self.logger.info("Successfully closed stdio connection")
        except Exception as e:
            self.logger.error(f"Error closing stdio connection: {str(e)}")
            # Don't raise here as this is a cleanup operation
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        if self.client_session:
            try:
                result = await asyncio.wait_for(
                    self.client_session.list_tools(),
                    timeout=self.timeout
                )
                self.logger.info(f"Successfully listed {len(result.get('tools', []))} tools")
                return result
            except asyncio.TimeoutError:
                raise ConnectionError(f"Timeout while listing tools after {self.timeout} seconds")
            except Exception as e:
                error_msg = f"Error listing tools: {str(e)}"
                self.logger.error(error_msg)
                raise
        else:
            error_msg = "Client session not initialized"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool with given arguments."""
        if self.client_session:
            try:
                self.logger.info(f"Calling tool {name} with arguments keys: {list(arguments.keys()) if arguments else 'none'}")
                result = await asyncio.wait_for(
                    self.client_session.call_tool(name, arguments),
                    timeout=self.timeout
                )
                self.logger.info(f"Successfully called tool {name}")
                return result
            except asyncio.TimeoutError:
                raise ConnectionError(f"Timeout while calling tool '{name}' after {self.timeout} seconds")
            except Exception as e:
                error_msg = f"Error calling tool '{name}': {str(e)}"
                self.logger.error(error_msg)
                raise
        else:
            error_msg = "Client session not initialized"
            self.logger.error(error_msg)
            raise ValueError(error_msg)


class StreamableHttpConnectionManager(ConnectionManager):
    """Connection manager for streamable HTTP-based connections using the official MCP SDK.
    
    Note: For streamable HTTP connections, the connection is established per operation
    rather than maintained as a long-lived connection like stdio.
    """
    
    def __init__(self, connection_params: Dict[str, Any]):
        super().__init__()  # Initialize the logger
        
        self.connection_params = connection_params
        self.url = connection_params["url"]
        
        # Extract timeout from connection parameters (default to 30 seconds)
        self.timeout = connection_params.get("timeout", 30.0)
        self.sse_read_timeout = connection_params.get("sse_read_timeout", 30.0)
        
        # Store headers if provided
        self.headers = connection_params.get("headers", {})
        if "authorization" in connection_params:
            self.headers["Authorization"] = connection_params["authorization"]
        
        # We don't maintain long-lived connections for streamable HTTP
        # Instead, each operation establishes its own connection
    
    async def initialize(self) -> None:
        """For streamable HTTP, we verify we can connect by doing a quick test."""
        try:
            # Test connection by attempting to list tools
            test_result = await self.list_tools()
            # The result from SDK is likely a structured object, not a dict
            tools = getattr(test_result, 'tools', None)
            if tools is None:
                tools = test_result.get('tools', []) if hasattr(test_result, 'get') else []
            self.logger.info(f"Successfully tested streamable HTTP connection to server at {self.url}, found {len(tools)} tools")
        except Exception as e:
            error_msg = f"Failed to verify streamable HTTP connection to {self.url}: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg) from e
    
    async def close(self) -> None:
        """Close any resources if needed."""
        self.logger.info(f"Streamable HTTP connection to {self.url} closed (no persistent resources to close)")
    
    async def _execute_with_session(self, operation_func):
        """Execute an operation within the proper SDK context."""
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession
        
        # Use the correct SDK pattern with async with
        async with streamablehttp_client(
            url=self.url,
            timeout=self.timeout,
            sse_read_timeout=self.sse_read_timeout,
            headers=self.headers
        ) as (read_stream, write_stream, get_session_id_callback):
            
            async with ClientSession(
                read_stream,
                write_stream,
                client_info={"name": "cogniscient-mcp-client", "version": "1.0.0"}
            ) as session:
                # Initialize the session
                init_result = await session.initialize()
                server_info = getattr(init_result, 'serverInfo', getattr(init_result, 'server_info', None))
                self.logger.debug(f"Connected to server! Server info: {server_info}")
                
                # Execute the operation
                return await operation_func(session)
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools using the official SDK."""
        async def operation(session):
            result = await asyncio.wait_for(
                session.list_tools(),
                timeout=self.timeout
            )
            return result
        
        try:
            result = await self._execute_with_session(operation)
            # The result from SDK is likely a structured object, not a dict
            # Try to access the tools attribute, falling back to get() for dict compatibility
            tools = getattr(result, 'tools', None)
            if tools is None:
                tools = result.get('tools', []) if hasattr(result, 'get') else []
            tool_count = len(tools)
            self.logger.info(f"Successfully listed {tool_count} tools from {self.url}")
            return result
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout while listing tools from {self.url} after {self.timeout} seconds")
        except Exception as e:
            error_msg = f"Error listing tools from {self.url}: {str(e)}"
            self.logger.error(error_msg)
            raise
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool with given arguments using the official SDK."""
        async def operation(session):
            self.logger.info(f"Calling tool {name} on {self.url} with arguments keys: {list(arguments.keys()) if arguments else 'none'}")
            result = await asyncio.wait_for(
                session.call_tool(name, arguments),
                timeout=self.timeout
            )
            return result
        
        try:
            result = await self._execute_with_session(operation)
            self.logger.info(f"Successfully called tool {name} on {self.url}")
            return result
        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout while calling tool '{name}' on {self.url} after {self.timeout} seconds")



class MCPClientService:
    """MCP client service for connecting to external agent MCP servers."""

    def __init__(self, gcs_runtime: 'GCSRuntime'):
        """Initialize the MCP client service with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        self.gcs_runtime = gcs_runtime
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Store connection managers instead of direct client sessions
        # This allows us to properly handle both stdio (persistent) and HTTP (context-managed) connections
        self.connection_managers: Dict[str, ConnectionManager] = {}
        
        # For backward compatibility, also provide access via the old 'clients' name
        # Though this should be accessed through connection_managers for new code
        self.clients = self.connection_managers
        
        # Registry for tools from connected external agents with type information
        self.tool_registry: Dict[str, List[Dict[str, Any]]] = {}
        # Registry to track if tools are system tools or dynamic agents
        self.tool_types: Dict[str, bool] = {}  # tool_name -> is_system_tool
        
        # Initialize MCP connection registry
        self.mcp_registry = MCPConnectionRegistry()

    async def connect_to_external_agent(self, agent_id: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to an external agent as an MCP client.
        
        Args:
            agent_id: Unique identifier for the external agent
            connection_params: Parameters for connecting to the external agent
                              (e.g., command, url, etc.) with 'type' field indicating 
                              the connection method ('stdio', 'http', etc.)
        
        Returns:
            Dict with 'success' boolean and 'message' with details
        """
        self.logger.info(f"Attempting to connect to external agent {agent_id} with type: {connection_params.get('type', 'stdio')}")
        
        # First check the registry for existing successful connection
        registry_entry = self.mcp_registry.get_connection(agent_id)
        if registry_entry:
            # Check if connection is still valid before reusing
            if self.mcp_registry.is_connection_valid(agent_id, connection_params):
                # Reuse existing connection if possible
                self.logger.info(f"Reusing existing connection for agent {agent_id}")
                result = {
                    "success": True,
                    "message": f"Reusing existing connection to external agent {agent_id}",
                    "reused_connection": True
                }
                # Update registry with new timestamp
                self.mcp_registry.update_connection_timestamp(agent_id)
                return result

        try:
            conn_type = connection_params.get("type", "stdio")  # Default to stdio

            # Create appropriate connection manager based on connection type
            if conn_type == "stdio":
                connection_manager = StdioConnectionManager(connection_params)
            elif conn_type == "http":
                connection_manager = StreamableHttpConnectionManager(connection_params)
            else:
                error_msg = f"Unsupported connection type: {conn_type}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # Initialize the connection
            await connection_manager.initialize()

            # Store the connection manager
            self.connection_managers[agent_id] = connection_manager

            # Get capabilities from the connected server and register them
            capabilities = await self._get_external_agent_capabilities(agent_id)
            
            # Check if we actually got capabilities
            if not capabilities:
                warning_msg = f"Connected to {agent_id} but no capabilities detected"
                self.logger.warning(warning_msg)

            # Register the external agent's tools so they can be tracked
            self.tool_registry[agent_id] = capabilities

            # On successful connection, save to registry
            connection_data = MCPConnectionData(
                agent_id=agent_id,
                connection_params=connection_params,
                status="connected"
            )
            self.mcp_registry.save_connection(connection_data)
            
            success_msg = f"Successfully connected to external agent {agent_id}"
            self.logger.info(f"{success_msg} - {len(capabilities)} capabilities detected")
            
            return {
                "success": True,
                "message": success_msg,
                "capabilities": capabilities,
                "tools_registered": len(capabilities)
            }
        except Exception as e:
            error_msg = f"Failed to connect to external agent {agent_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            # On failure, remove entry from registry if it exists
            self.mcp_registry.remove_connection(agent_id)
            return {
                "success": False,
                "message": error_msg
            }

    async def _get_external_agent_capabilities(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get capabilities of an external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            List of tool definitions available on the external agent
        """
        if agent_id not in self.connection_managers:
            error_msg = f"No connection to external agent: {agent_id}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        connection_manager = self.connection_managers[agent_id]

        # Get the tools from the external agent
        try:
            self.logger.info(f"Retrieving capabilities from external agent {agent_id}")
            # Get the list of available tools from the external agent
            tools_result = await connection_manager.list_tools()
            tools = tools_result.get('tools', [])

            # Format tools to match the expected structure
            formatted_tools = []
            for tool in tools:
                tool_name = tool.get("name", "")
                tool_info = {
                    "name": tool_name,
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", {})
                }
                
                # Determine if this is a system tool based on naming convention
                # In a real implementation, this might be determined differently
                is_system_tool = tool_name.startswith("system.")
                
                # Store the tool type information
                self.tool_types[tool_name] = is_system_tool
                
                formatted_tools.append(tool_info)
                
            self.logger.info(f"Retrieved {len(formatted_tools)} capabilities from external agent {agent_id}")
            return formatted_tools
        except Exception as e:
            error_msg = f"Error getting capabilities from external agent {agent_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return []

    async def get_external_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get capabilities of an external agent as structured response.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            Dict with success status and capabilities
        """
        try:
            self.logger.info(f"Getting capabilities for agent {agent_id}")
            capabilities = await self._get_external_agent_capabilities(agent_id)
            msg = f"Retrieved {len(capabilities)} capabilities from agent {agent_id}"
            self.logger.info(msg)
            return {
                "success": True,
                "capabilities": capabilities,
                "message": msg
            }
        except Exception as e:
            error_msg = f"Error retrieving capabilities from agent {agent_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }

    async def disconnect_from_external_agent(self, agent_id: str) -> Dict[str, Any]:
        """Disconnect from an external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            Dict with 'success' boolean and 'message' with details
        """
        if agent_id in self.connection_managers:
            try:
                self.logger.info(f"Disconnecting from external agent {agent_id}")
                connection_manager = self.connection_managers[agent_id]
                await connection_manager.close()
                del self.connection_managers[agent_id]

                # Remove the registered tools for this agent
                if agent_id in self.tool_registry:
                    del self.tool_registry[agent_id]

                # Update registry to reflect disconnection
                connection_data = self.mcp_registry.get_connection(agent_id)
                if connection_data:
                    # Update status to disconnected but keep the record
                    connection_data.status = "disconnected"
                    self.mcp_registry.save_connection(connection_data)

                success_msg = f"Successfully disconnected from external agent {agent_id}"
                self.logger.info(success_msg)
                return {
                    "success": True,
                    "message": success_msg
                }
            except Exception as e:
                error_msg = f"Error disconnecting from external agent {agent_id}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return {
                    "success": False,
                    "message": error_msg
                }
        else:
            # Try to remove from registry even if no active connection exists
            self.mcp_registry.remove_connection(agent_id)
            error_msg = f"No connection to external agent: {agent_id}"
            self.logger.warning(error_msg)
            return {
                "success": False,
                "message": error_msg
            }

    async def call_external_agent_tool(self, agent_id: str, tool_name: str, **kwargs) -> Any:
        """Call a tool on an external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
        
        Returns:
            Result from the tool call
        """
        if agent_id not in self.connection_managers:
            error_msg = f"No connection to external agent: {agent_id}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(f"Calling tool '{tool_name}' on external agent {agent_id}")
        connection_manager = self.connection_managers[agent_id]

        # Call the tool on the external agent
        result = await connection_manager.call_tool(tool_name, kwargs)
        self.logger.info(f"Successfully called tool '{tool_name}' on external agent {agent_id}")
        return result

    def get_connected_agents(self) -> Dict[str, Any]:
        """Get list of connected external agents.
        
        Returns:
            Dict with success status and list of connected agents
        """
        return {
            "success": True,
            "connected_agents": list(self.connection_managers.keys()),
            "count": len(self.connection_managers)
        }

    def get_registered_external_tools(self) -> Dict[str, Any]:
        """Get all registered tools from connected external agents.
        
        Returns:
            Dict with success status and mapping of agent IDs to their tools
        """
        return {
            "success": True,
            "external_agent_tools": self.tool_registry,
            "total_tools": sum(len(tools) for tools in self.tool_registry.values())
        }
    
    def get_tool_type(self, tool_name: str) -> bool:
        """Check if a tool is a system tool or dynamic agent tool.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            bool: True if the tool is a system tool, False if it's a dynamic agent tool
        """
        return self.tool_types.get(tool_name, False)
    
    def get_all_tool_types(self) -> Dict[str, bool]:
        """Get all registered tool types.
        
        Returns:
            Dict mapping tool names to whether they are system tools
        """
        return self.tool_types.copy()