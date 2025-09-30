"""MCP Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) for both client and server roles,
enabling standardized tool integration in the Adaptive Control System.
The GCS acts as both an MCP server (exposing its tools to upstream orchestrators)
and an MCP client (connecting to external agent MCP servers).
"""

import asyncio
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context
from mcp.client.session import ClientSession
from mcp import stdio_client
from mcp.types import Tool

from cogniscient.engine.gcs_runtime import GCSRuntime


class MCPService:
    """MCP service for handling both client and server roles in tool integration."""

    def __init__(self, gcs_runtime: GCSRuntime):
        """Initialize the MCP service with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        # MCP Server: Expose GCS tools to upstream orchestrators
        self.mcp_server = FastMCP(
            name="cogniscient-mcp-server",
            instructions="MCP server for Cogniscient Adaptive Control System, providing access to local agents and system functions.",
        )
        self.gcs_runtime = gcs_runtime
        
        # MCP Client: Connect to external agent MCP servers
        self.clients: Dict[str, ClientSession] = {}
        
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
                    self._register_method_as_tool(agent_name, method_name)
    
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
                "active_clients": len(self.clients)
            }
        
        self.mcp_server.tool(
            name="system.status",
            description="Get the current status of the GCS system"
        )(system_status_tool)
    
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
    
    def _register_method_as_tool(self, agent_name: str, method_name: str):
        """Register an agent method as an MCP tool (server role).
        
        Args:
            agent_name: Name of the agent.
            method_name: Name of the method to register.
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
        
        # Register the tool with the MCP server using the @self.mcp_server.tool decorator
        # This creates a tool that can be called by upstream MCP clients
        self.mcp_server.tool(
            name=tool_name,
            description=f"Execute {method_name} method on {agent_name} agent"
        )(agent_method_tool)
    
    # Client functionality for connecting to external agent MCP servers
    async def connect_to_external_agent(self, agent_id: str, connection_params: Dict[str, Any]) -> bool:
        """Connect to an external agent as an MCP client.
        
        Args:
            agent_id: Unique identifier for the external agent
            connection_params: Parameters for connecting to the external agent
                              (e.g., command, args, etc.)
        
        Returns:
            True if connection was successful, False otherwise
        """
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
            else:
                raise ValueError(f"Unsupported connection type: {conn_type}")
            
            # Store the client session
            self.clients[agent_id] = client_session
            
            # Initialize the client
            await client_session.initialize()
            
            return True
        except Exception as e:
            print(f"Failed to connect to external agent {agent_id}: {e}")
            return False
    
    async def disconnect_from_external_agent(self, agent_id: str) -> bool:
        """Disconnect from an external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            True if disconnection was successful, False otherwise
        """
        if agent_id in self.clients:
            try:
                client_session = self.clients[agent_id]
                await client_session.close()
                del self.clients[agent_id]
                return True
            except Exception as e:
                print(f"Error disconnecting from external agent {agent_id}: {e}")
                return False
        return False
    
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
    
    def start_server(self):
        """Start the MCP server (so GCS can be used by upstream orchestrators)."""
        return self.mcp_server.run()

    def get_connected_agents(self) -> List[str]:
        """Get list of connected external agents.
        
        Returns:
            List of agent IDs for connected external agents
        """
        return list(self.clients.keys())


async def create_mcp_service(gcs_runtime: GCSRuntime):
    """Create and return an MCP service instance that supports both client and server roles.
    
    Args:
        gcs_runtime: The GCS runtime instance.
        
    Returns:
        MCPService instance.
    """
    return MCPService(gcs_runtime)