"""MCP Client Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) client role,
enabling the system to connect to external agent MCP servers.
"""

from typing import List, Dict, Any
from mcp.client.session import ClientSession
from mcp import stdio_client

from typing import TYPE_CHECKING
from typing import List, Dict, Any

if TYPE_CHECKING:
    from cogniscient.engine.gcs_runtime import GCSRuntime
from .mcp_registry import MCPConnectionRegistry, MCPConnectionData


class MCPClientService:
    """MCP client service for connecting to external agent MCP servers."""

    def __init__(self, gcs_runtime: 'GCSRuntime'):
        """Initialize the MCP client service with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        self.gcs_runtime = gcs_runtime
        
        # MCP Client: Connect to external agent MCP servers
        self.clients: Dict[str, ClientSession] = {}
        
        # Registry for tools from connected external agents with type information
        self.connected_agent_tools: Dict[str, List[Dict[str, Any]]] = {}
        # Registry to track if tools are system tools or dynamic agents
        self.tool_types: Dict[str, bool] = {}  # tool_name -> is_system_tool
        
        # Initialize MCP connection registry
        self.mcp_registry = MCPConnectionRegistry()

    async def connect_to_external_agent(self, agent_id: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to an external agent as an MCP client.
        
        Args:
            agent_id: Unique identifier for the external agent
            connection_params: Parameters for connecting to the external agent
                              (e.g., command, args, etc.) with 'type' field indicating 
                              the connection method ('stdio', 'http', etc.)
        
        Returns:
            Dict with 'success' boolean and 'message' with details
        """
        # First check the registry for existing successful connection
        registry_entry = self.mcp_registry.get_connection(agent_id)
        if registry_entry:
            # Check if connection is still valid before reusing
            if self.mcp_registry.is_connection_valid(agent_id, connection_params):
                # Reuse existing connection if possible
                print(f"Reusing existing connection for agent {agent_id}")
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

            if conn_type == "stdio":
                # For stdio, we need parameters for the process to connect to
                from mcp.client.stdio import StdioServerParameters
                from mcp.client.stdio import Process

                # Create process parameters
                server_params = StdioServerParameters(
                    process=Process(
                        command=connection_params["command"],
                        args=connection_params.get("args", []),
                        env=connection_params.get("env", {})
                    )
                )

                # Connect using stdio client
                client_session = await stdio_client(server=server_params)
            elif conn_type == "http":
                # For HTTP connections, we need the endpoint URL
                try:
                    from mcp.client.http import HttpClientParameters
                except ImportError:
                    raise ValueError("HTTP client support not available. The 'mcp.client.http' module is not available.")

                # Create HTTP client parameters
                server_params = HttpClientParameters(
                    url=connection_params["url"],
                    headers=connection_params.get("headers", {}),
                    authorization=connection_params.get("authorization", None)
                )

                # Connect using HTTP client
                try:
                    from mcp.client.http import http_client
                    client_session = await http_client(server=server_params)
                except ImportError:
                    raise ValueError("HTTP client support not available. The 'http_client' function is not available.")
            else:
                raise ValueError(f"Unsupported connection type: {conn_type}")

            # Store the client session
            self.clients[agent_id] = client_session

            # Initialize the client
            await client_session.initialize()

            # Get capabilities from the connected server and register them
            capabilities = await self._get_external_agent_capabilities(agent_id)

            # Register the external agent's tools so they can be tracked
            self.connected_agent_tools[agent_id] = capabilities

            # On successful connection, save to registry
            connection_data = MCPConnectionData(
                agent_id=agent_id,
                connection_params=connection_params,
                status="connected"
            )
            self.mcp_registry.save_connection(connection_data)

            return {
                "success": True,
                "message": f"Successfully connected to external agent {agent_id}",
                "capabilities": capabilities,
                "tools_registered": len(capabilities)
            }
        except Exception as e:
            error_msg = f"Failed to connect to external agent {agent_id}: {str(e)}"
            print(error_msg)
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
        if agent_id not in self.clients:
            raise ValueError(f"No connection to external agent: {agent_id}")

        client_session = self.clients[agent_id]

        # Get the tools from the external agent
        try:
            # Get the list of available tools from the external agent
            tools_result = await client_session.list_tools()
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

            return formatted_tools
        except Exception as e:
            print(f"Error getting capabilities from external agent {agent_id}: {str(e)}")
            return []

    async def get_external_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get capabilities of an external agent as structured response.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            Dict with success status and capabilities
        """
        try:
            capabilities = await self._get_external_agent_capabilities(agent_id)
            return {
                "success": True,
                "capabilities": capabilities,
                "message": f"Retrieved {len(capabilities)} capabilities from agent {agent_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving capabilities from agent {agent_id}: {str(e)}"
            }

    async def disconnect_from_external_agent(self, agent_id: str) -> Dict[str, Any]:
        """Disconnect from an external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            Dict with 'success' boolean and 'message' with details
        """
        if agent_id in self.clients:
            try:
                client_session = self.clients[agent_id]
                await client_session.close()
                del self.clients[agent_id]

                # Remove the registered tools for this agent
                if agent_id in self.connected_agent_tools:
                    del self.connected_agent_tools[agent_id]

                # Update registry to reflect disconnection
                connection_data = self.mcp_registry.get_connection(agent_id)
                if connection_data:
                    # Update status to disconnected but keep the record
                    connection_data.status = "disconnected"
                    self.mcp_registry.save_connection(connection_data)

                return {
                    "success": True,
                    "message": f"Successfully disconnected from external agent {agent_id}"
                }
            except Exception as e:
                error_msg = f"Error disconnecting from external agent {agent_id}: {str(e)}"
                print(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
        else:
            # Try to remove from registry even if no active connection exists
            self.mcp_registry.remove_connection(agent_id)
            return {
                "success": False,
                "message": f"No connection to external agent: {agent_id}"
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
        if agent_id not in self.clients:
            raise ValueError(f"No connection to external agent: {agent_id}")

        client_session = self.clients[agent_id]

        # Call the tool on the external agent
        result = await client_session.call_tool(tool_name, kwargs)
        return result

    def get_connected_agents(self) -> Dict[str, Any]:
        """Get list of connected external agents.
        
        Returns:
            Dict with success status and list of connected agents
        """
        return {
            "success": True,
            "connected_agents": list(self.clients.keys()),
            "count": len(self.clients)
        }

    def get_registered_external_tools(self) -> Dict[str, Any]:
        """Get all registered tools from connected external agents.
        
        Returns:
            Dict with success status and mapping of agent IDs to their tools
        """
        return {
            "success": True,
            "external_agent_tools": self.connected_agent_tools,
            "total_tools": sum(len(tools) for tools in self.connected_agent_tools.values())
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