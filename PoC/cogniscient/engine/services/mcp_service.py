"""MCP Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) server for standardized
tool integration in the Adaptive Control System.
"""

from typing import List

from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context

from cogniscient.engine.gcs_runtime import GCSRuntime


class MCPServer:
    """MCP server for handling tool registration and orchestration."""

    def __init__(self, gcs_runtime: GCSRuntime):
        """Initialize the MCP server with GCS runtime access.
        
        Args:
            gcs_runtime: The GCS runtime instance to access agents.
        """
        self.mcp = FastMCP(
            name="cogniscient-mcp-server",
            instructions="MCP server for Cogniscient Adaptive Control System",
        )
        self.gcs_runtime = gcs_runtime
        
        # Register all agents as MCP tools
        self._register_agent_tools()
    
    def _register_agent_tools(self):
        """Dynamically register all agents as MCP tools."""
        # Iterate through all loaded agents in GCS runtime
        for agent_name in self.gcs_runtime.agents.keys():
            # Get methods from the agent that should be exposed as tools
            agent_instance = self.gcs_runtime.agents.get(agent_name)
            if agent_instance:
                # For each method, create an MCP tool
                for method_name in self._get_agent_methods(agent_instance):
                    self._register_method_as_tool(agent_name, method_name)
    
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
        """Register an agent method as an MCP tool.
        
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
        
        # Register the tool with the MCP server using the @self.mcp.tool decorator
        # This creates a tool that can be called by MCP clients
        self.mcp.tool(
            name=tool_name,
            description=f"Execute {method_name} method on {agent_name} agent"
        )(agent_method_tool)
    
    def start(self):
        """Start the MCP server."""
        return self.mcp.run()


async def create_mcp_server(gcs_runtime: GCSRuntime):
    """Create and return an MCP server instance.
    
    Args:
        gcs_runtime: The GCS runtime instance.
        
    Returns:
        MCPServer instance.
    """
    return MCPServer(gcs_runtime)