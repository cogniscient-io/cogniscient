"""Refactored MCP Service Implementation for Adaptive Control System.

This module now delegates to separate MCP client and server services,
enabling standardized tool integration in the Adaptive Control System.
The GCS acts as both an MCP server (exposing its tools to upstream orchestrators)
and an MCP client (connecting to external agent MCP servers).
"""

from typing import List, Dict, Any
from typing import TYPE_CHECKING
from typing import List, Dict, Any

if TYPE_CHECKING:
    from cogniscient.engine.gcs_runtime import GCSRuntime
from .mcp_client_service import MCPClientService
from .mcp_server_service import MCPServerService


class MCPService:
    """MCP service for handling both client and server roles in tool integration through separated services."""

    def __init__(self, gcs_runtime: 'GCSRuntime'):
        """Initialize the MCP service with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        self.gcs_runtime = gcs_runtime
        
        # Initialize separated MCP client and server services
        self.mcp_client = MCPClientService(gcs_runtime)
        self.mcp_server = MCPServerService(gcs_runtime)
        
        # For backward compatibility, we'll also expose the client and server properties
        # directly on this class so existing code continues to work
        self.clients = self.mcp_client.clients  # This now refers to the alias in MCPClientService
        self.tool_registry = self.mcp_client.tool_registry
        self.mcp_registry = self.mcp_client.mcp_registry
        self.mcp_server_instance = self.mcp_server.mcp_server
    
    # Client functionality methods - delegate to MCPClientService
    async def connect_to_external_agent(self, agent_id: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to an external agent as an MCP client."""
        return await self.mcp_client.connect_to_external_agent(agent_id, connection_params)
    
    async def _get_external_agent_capabilities(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get capabilities of an external agent."""
        return await self.mcp_client._get_external_agent_capabilities(agent_id)
    
    async def get_external_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get capabilities of an external agent as structured response."""
        return await self.mcp_client.get_external_agent_capabilities(agent_id)
    
    async def disconnect_from_external_agent(self, agent_id: str) -> Dict[str, Any]:
        """Disconnect from an external agent."""
        return await self.mcp_client.disconnect_from_external_agent(agent_id)
    
    async def call_external_agent_tool(self, agent_id: str, tool_name: str, **kwargs) -> Any:
        """Call a tool on an external agent."""
        return await self.mcp_client.call_external_agent_tool(agent_id, tool_name, **kwargs)
    
    def get_connected_agents(self) -> Dict[str, Any]:
        """Get list of connected external agents."""
        return self.mcp_client.get_connected_agents()
    
    def get_registered_external_tools(self) -> Dict[str, Any]:
        """Get all registered tools from connected external agents."""
        return self.mcp_client.get_registered_external_tools()
    
    def get_tool_type(self, tool_name: str) -> bool:
        """Check if a tool is a system tool or dynamic agent tool.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            bool: True if the tool is a system tool, False if it's a dynamic agent tool
        """
        return self.mcp_client.get_tool_type(tool_name)
    
    def get_all_tool_types(self) -> Dict[str, bool]:
        """Get all registered tool types.
        
        Returns:
            Dict mapping tool names to whether they are system tools
        """
        return self.mcp_client.get_all_tool_types()
    
    # Server functionality methods - delegate to MCPServerService
    def start_server(self):
        """Start the MCP server (so GCS can be used by upstream orchestrators)."""
        return self.mcp_server.start_server()
    
    def describe_mcp_service(self) -> Dict[str, Any]:
        """Describe the capabilities of the MCP service for LLM consumption."""
        # Combine both client and server descriptions
        client_description = {
            "name": "MCPClientService",
            "description": "Model Context Protocol client service for connecting to external tools and agents",
            "methods": {
                "connect_to_external_agent": {
                    "description": "Connect to an external agent via MCP protocol",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent", 
                            "required": True
                        },
                        "connection_params": {
                            "type": "object", 
                            "description": "Connection parameters including type, command, args, and env", 
                            "required": True
                        }
                    }
                },
                "get_connected_agents": {
                    "description": "Get list of currently connected external agents",
                    "parameters": {}
                },
                "get_external_agent_capabilities": {
                    "description": "Get capabilities (tools) of a connected external agent",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent", 
                            "required": True
                        }
                    }
                },
                "call_external_agent_tool": {
                    "description": "Call a specific tool on a connected external agent",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent", 
                            "required": True
                        },
                        "tool_name": {
                            "type": "string", 
                            "description": "Name of the tool to call", 
                            "required": True
                        }
                    }
                },
                "disconnect_from_external_agent": {
                    "description": "Disconnect from an external agent",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent", 
                            "required": True
                        }
                    }
                },
                "get_registered_external_tools": {
                    "description": "Get all registered tools from connected external agents",
                    "parameters": {}
                }
            }
        }
        
        server_description = self.mcp_server.describe_mcp_service()
        
        # For backward compatibility, combine all methods at the top level
        # but also provide structured access
        all_methods = {}
        all_methods.update(client_description["methods"])
        all_methods.update(server_description["methods"])
        
        # Combine both descriptions
        combined_description = {
            "name": "MCPService",
            "description": "Model Context Protocol service for connecting to external tools and agents (client) and exposing local tools (server)",
            "methods": all_methods,  # For backward compatibility
            "client_methods": client_description["methods"],
            "server_methods": server_description["methods"]
        }
        
        return combined_description


async def create_mcp_service(gcs_runtime: 'GCSRuntime'):
    """Create and return an MCP service instance that supports both client and server roles.
    
    Args:
        gcs_runtime: The GCS runtime instance.
        
    Returns:
        MCPService instance.
    """
    return MCPService(gcs_runtime)