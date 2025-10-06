"""MCP Server Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) server role,
enabling the system to expose its tools to upstream orchestrators.
"""

from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context

from typing import TYPE_CHECKING
from typing import List, Dict, Any

if TYPE_CHECKING:
    from cogniscient.engine.gcs_runtime import GCSRuntime
from .mcp_client_service import MCPClientService


class MCPServerService:
    """MCP server service for exposing GCS tools to upstream orchestrators."""

    def __init__(self, gcs_runtime: 'GCSRuntime'):
        """Initialize the MCP server service with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        # MCP Server: Expose GCS tools to upstream orchestrators
        self.mcp_server = FastMCP(
            name="cogniscient-mcp-server",
            instructions="MCP server for Cogniscient Adaptive Control System, providing access to local agents and system functions.",
        )
        self.gcs_runtime = gcs_runtime
        
        # Register all agents as MCP tools (server role)
        self._register_agent_tools()
        
        # Register system-level tools
        self._register_system_tools()
    
    def _register_agent_tools(self):
        """Dynamically register all agents as MCP tools (server role)."""
        # Iterate through all loaded agents in GCS runtime
        for agent_name in self.gcs_runtime.agents.keys():
            # Get methods from the agent that should be exposed as tools
            agent_instance = self.gcs_runtime.agents.get(agent_name)
            if agent_instance:
                # For each method, create an MCP tool
                for method_name in self._get_agent_methods(agent_instance):
                    self._register_method_as_tool(agent_name, method_name, is_system_tool=False)
    
    def _register_system_tools(self):
        """Register system-level tools that provide access to GCS functionality."""
        # Tool to list available agents
        async def list_agents_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing available agents")
            return {
                "agents": list(self.gcs_runtime.agents.keys()),
                "count": len(self.gcs_runtime.agents)
            }
        
        self.mcp_server.tool(
            name="system.list_agents",
            description="List all available agents in the GCS system"
        )(list_agents_tool)
        
        # Tool to get GCS system status
        async def system_status_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Getting system status")
            return {
                "status": "operational",
                "agent_count": len(self.gcs_runtime.agents),
                "active_clients": len(self.gcs_runtime.mcp_client_service.clients) if hasattr(self.gcs_runtime, 'mcp_client_service') else 0
            }
        
        self.mcp_server.tool(
            name="system.status",
            description="Get the current status of the GCS system"
        )(system_status_tool)
        
        # Tool to connect to external agents via MCP protocol - this will need access to MCP client service
        async def connect_external_agent_tool(ctx: Context[ServerSession, None], agent_id: str, connection_params: Dict[str, Any]):
            await ctx.info(f"Connecting to external agent {agent_id}")
            # Note: We'll need access to the MCP client service to make this call
            # This will be resolved when the services are properly integrated
            if hasattr(self.gcs_runtime, 'mcp_client_service'):
                result = await self.gcs_runtime.mcp_client_service.connect_to_external_agent(agent_id, connection_params)
                return result
            else:
                return {
                    "success": False,
                    "message": "MCP client service not available"
                }
        
        self.mcp_server.tool(
            name="system.connect_external_agent",
            description="Connect to an external agent using MCP protocol with specified connection parameters (type can be 'stdio' or 'http')"
        )(connect_external_agent_tool)
        
        # Tool to get list of connected external agents
        async def list_connected_agents_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing connected external agents")
            # Note: We'll need access to the MCP client service to make this call
            if hasattr(self.gcs_runtime, 'mcp_client_service'):
                result = self.gcs_runtime.mcp_client_service.get_connected_agents()
                return result
            else:
                return {
                    "success": False,
                    "connected_agents": [],
                    "count": 0
                }
        
        self.mcp_server.tool(
            name="system.list_connected_agents",
            description="Get a list of currently connected external agents"
        )(list_connected_agents_tool)
        
        # Tool to disconnect from an external agent
        async def disconnect_external_agent_tool(ctx: Context[ServerSession, None], agent_id: str):
            await ctx.info(f"Disconnecting from external agent {agent_id}")
            # Note: We'll need access to the MCP client service to make this call
            if hasattr(self.gcs_runtime, 'mcp_client_service'):
                result = await self.gcs_runtime.mcp_client_service.disconnect_from_external_agent(agent_id)
                return result
            else:
                return {
                    "success": False,
                    "message": "MCP client service not available"
                }
        
        self.mcp_server.tool(
            name="system.disconnect_external_agent",
            description="Disconnect from an external agent by its ID"
        )(disconnect_external_agent_tool)
    
    def _get_agent_methods(self, agent_instance) -> List[str]:
        """Get methods from an agent that should be exposed as tools.
        
        Args:
            agent_instance: The agent instance to analyze.
            
        Returns:
            List of method names that should be MCP tools.
        """
        # Get all public methods from the agent instance
        methods = []
        for attr_name in dir(agent_instance):
            if not attr_name.startswith('_'):  # Skip private methods
                attr = getattr(agent_instance, attr_name)
                if callable(attr) and not isinstance(attr, type):
                    methods.append(attr_name)
        return methods
    
    def _register_method_as_tool(self, agent_name: str, method_name: str, is_system_tool: bool = False):
        """Register an agent method as an MCP tool (server role).
        
        Args:
            agent_name: Name of the agent.
            method_name: Name of the method to register.
            is_system_tool: Flag to indicate if this is a system tool vs dynamic agent.
        """
        # Create a wrapper function that calls the agent method through GCS
        async def agent_method_tool(ctx: Context[ServerSession, None], **kwargs):
            try:
                # Execute the agent method through the GCS runtime
                result = self.gcs_runtime.run_agent(agent_name, method_name, **kwargs)
                await ctx.info(f"Successfully executed {agent_name}.{method_name}")
                return result
            except Exception as e:
                await ctx.error(f"Error executing {agent_name}.{method_name}: {str(e)}")
                raise
        
        # Create a tool name using the agent and method name
        tool_name = f"{agent_name}.{method_name}"
        
        # Prepare tool options including the is_system_tool flag
        tool_options = {
            "name": tool_name,
            "description": f"Execute {method_name} method on {agent_name} agent (system tool: {is_system_tool})"
        }
        
        # Register the tool with the MCP server using the @self.mcp_server.tool decorator
        # This creates a tool that can be called by upstream MCP clients
        self.mcp_server.tool(**tool_options)(agent_method_tool)
    
    def start_server(self):
        """Start the MCP server (so GCS can be used by upstream orchestrators)."""
        return self.mcp_server.run()

    def describe_mcp_service(self) -> Dict[str, Any]:
        """Describe the capabilities of the MCP service for LLM consumption.
        
        Returns:
            Dict describing all MCP service capabilities
        """
        return {
            "name": "MCPServerService",
            "description": "Model Context Protocol server service for exposing local tools and agents",
            "methods": {
                "system.connect_external_agent": {
                    "description": "Connect to an external agent using MCP protocol with specified connection parameters (type can be 'stdio' or 'http')",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent", 
                            "required": True
                        },
                        "connection_params": {
                            "type": "object", 
                            "properties": {
                                "type": {"type": "string", "enum": ["stdio", "http"], "description": "Type of connection"},
                                "url": {"type": "string", "description": "URL for HTTP connections (required if type is 'http')"},
                                "command": {"type": "string", "description": "Command for stdio connections (required if type is 'stdio')"},
                                "args": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Arguments for stdio command (optional)"
                                },
                                "headers": {
                                    "type": "object",
                                    "description": "HTTP headers for HTTP connections (optional)"
                                },
                                "authorization": {
                                    "type": "string",
                                    "description": "Authorization header for HTTP connections (optional)"
                                },
                                "env": {
                                    "type": "object",
                                    "description": "Environment variables for stdio processes (optional)"
                                }
                            },
                            "required": ["type"],
                            "description": "Connection parameters including type, url/command, headers, and authorization"
                        }
                    }
                },
                "system.list_connected_agents": {
                    "description": "Get a list of currently connected external agents",
                    "parameters": {}
                },
                "system.disconnect_external_agent": {
                    "description": "Disconnect from an external agent by its ID",
                    "parameters": {
                        "agent_id": {
                            "type": "string", 
                            "description": "Unique identifier for the external agent to disconnect", 
                            "required": True
                        }
                    }
                }
            }
        }