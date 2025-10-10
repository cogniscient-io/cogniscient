"""MCP Server Service Implementation for Adaptive Control System.

This module implements the Model Context Protocol (MCP) server role,
enabling the system to expose its tools to upstream orchestrators.
"""

from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context
import logging

from typing import TYPE_CHECKING

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
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Register all agents as MCP tools (server role)
        self._register_agent_tools()
        
        # Register system-level tools
        self._register_system_tools()
    
    def _register_agent_tools(self):
        """Dynamically register all agents as MCP tools (server role)."""
        # Skip agent tool registration since agents property is removed
        # In a complete implementation, this would use the agent service to get registered agents
        pass
    
    def _register_system_tools(self):
        """Register system-level tools that provide access to GCS functionality."""
        # Tool to list available agents
        @self.mcp_server.tool(
            name="system.list_agents",
            description="List all available agents in the GCS system"
        )
        async def list_agents_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing available agents")
            try:
                # Return empty list since agents property is removed
                # In a complete implementation, this would use the agent service
                result = {
                    "agents": [],
                    "count": 0
                }
                await ctx.info(f"Successfully listed {len(result['agents'])} agents")
                return result
            except Exception as e:
                await ctx.error(f"Error listing agents: {str(e)}")
                raise
        
        # Tool to list all available system tools
        @self.mcp_server.tool(
            name="system.list_tools",
            description="List all available system tools and connected agent tools"
        )
        async def list_system_tools_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing available system tools")
            try:
                # Get all registered tools from the server
                tools_result = await ctx.session.list_tools()
                tools = tools_result.get('tools', [])
                
                # Also include MCP client tools if available
                client_tools = {}
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    # Get tools from connected external agents
                    client_tools = self.gcs_runtime.mcp_client_service.get_registered_external_tools()
                
                result = {
                    "system_tools": [
                        {"name": tool.get("name"), "description": tool.get("description", "")}
                        for tool in tools
                    ],
                    "connected_agent_tools": client_tools,  # Note: Keeping for backward compatibility in response format
                    "total_tools": len(tools)
                }
                await ctx.info(f"Successfully listed {len(tools)} system tools")
                return result
            except Exception as e:
                await ctx.error(f"Error listing system tools: {str(e)}")
                raise
        
        # Tool to get GCS system status
        @self.mcp_server.tool(
            name="system.status",
            description="Get the current status of the GCS system"
        )
        async def system_status_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Getting system status")
            try:
                active_clients = 0
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    active_clients = len(self.gcs_runtime.mcp_client_service.clients)
                    
                result = {
                    "status": "operational",
                    "agent_count": 0,  # Return 0 since agents property is removed
                    "active_clients": active_clients,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
                await ctx.info("Successfully retrieved system status")
                return result
            except Exception as e:
                await ctx.error(f"Error getting system status: {str(e)}")
                raise
        
        # Config Service Tools
        @self.mcp_server.tool(
            name="config.list_configurations",
            description="List all available system configurations"
        )
        async def config_list_configurations_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing configurations")
            try:
                # Access the config service through GCS runtime
                if hasattr(self.gcs_runtime, 'config_service'):
                    result = self.gcs_runtime.config_service.list_configurations()
                    await ctx.info(f"Successfully listed {len(result.get('configurations', []))} configurations")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "Config service not available"
                    }
                    await ctx.error("Config service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error listing configurations: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="config.load_configuration",
            description="Load a specific system configuration by name"
        )
        async def config_load_configuration_tool(ctx: Context[ServerSession, None], config_name: str):
            await ctx.info(f"Loading configuration {config_name}")
            try:
                # Access the config service through GCS runtime
                if hasattr(self.gcs_runtime, 'config_service'):
                    result = self.gcs_runtime.config_service.load_configuration(config_name)
                    if result.get("status") == "success":
                        await ctx.info(f"Successfully loaded configuration {config_name}")
                    else:
                        await ctx.warn(f"Failed to load configuration {config_name}: {result.get('message')}")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "Config service not available"
                    }
                    await ctx.error("Config service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error loading configuration {config_name}: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="config.get_configuration",
            description="Get a specific system configuration from cache or file"
        )
        async def config_get_configuration_tool(ctx: Context[ServerSession, None], config_name: str):
            await ctx.info(f"Getting configuration {config_name}")
            try:
                # Access the config service through GCS runtime
                if hasattr(self.gcs_runtime, 'config_service'):
                    result = self.gcs_runtime.config_service.get_configuration(config_name)
                    await ctx.info(f"Successfully retrieved configuration {config_name}")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "Config service not available"
                    }
                    await ctx.error("Config service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error getting configuration {config_name}: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="config.get_all_cached_configs",
            description="Get all currently cached configurations"
        )
        async def config_get_all_cached_configs_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Getting all cached configurations")
            try:
                # Access the config service through GCS runtime
                if hasattr(self.gcs_runtime, 'config_service'):
                    result = self.gcs_runtime.config_service.get_all_cached_configs()
                    await ctx.info(f"Successfully retrieved cached configurations")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "Config service not available"
                    }
                    await ctx.error("Config service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error getting cached configurations: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="config.clear_config_cache",
            description="Clear the configuration cache"
        )
        async def config_clear_config_cache_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Clearing configuration cache")
            try:
                # Access the config service through GCS runtime
                if hasattr(self.gcs_runtime, 'config_service'):
                    self.gcs_runtime.config_service.clear_config_cache()
                    result = {
                        "status": "success",
                        "message": "Configuration cache cleared successfully"
                    }
                    await ctx.info("Successfully cleared configuration cache")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "Config service not available"
                    }
                    await ctx.error("Config service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error clearing configuration cache: {str(e)}")
                raise

        # System Parameters Service Tools
        @self.mcp_server.tool(
            name="system.get_parameters",
            description="Get current system parameter values"
        )
        async def system_get_parameters_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Getting system parameters")
            try:
                # Access the system parameters service through GCS runtime
                if hasattr(self.gcs_runtime, 'system_parameters_service'):
                    result = self.gcs_runtime.system_parameters_service.get_system_parameters()
                    await ctx.info("Successfully retrieved system parameters")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "System parameters service not available"
                    }
                    await ctx.error("System parameters service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error getting system parameters: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="system.set_parameter",
            description="Set a system parameter value"
        )
        async def system_set_parameter_tool(ctx: Context[ServerSession, None], parameter_name: str, parameter_value: str):
            await ctx.info(f"Setting system parameter {parameter_name}")
            try:
                # Access the system parameters service through GCS runtime
                if hasattr(self.gcs_runtime, 'system_parameters_service'):
                    result = self.gcs_runtime.system_parameters_service.set_system_parameter(parameter_name, parameter_value)
                    if result.get("status") == "success":
                        await ctx.info(f"Successfully set parameter {parameter_name}")
                    else:
                        await ctx.warn(f"Failed to set parameter {parameter_name}: {result.get('message')}")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "System parameters service not available"
                    }
                    await ctx.error("System parameters service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error setting parameter {parameter_name}: {str(e)}")
                raise
        
        @self.mcp_server.tool(
            name="system.get_parameter_descriptions",
            description="Get descriptions of all system parameters"
        )
        async def system_get_parameter_descriptions_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Getting parameter descriptions")
            try:
                # Access the system parameters service through GCS runtime
                if hasattr(self.gcs_runtime, 'system_parameters_service'):
                    result = self.gcs_runtime.system_parameters_service.get_parameter_descriptions()
                    await ctx.info("Successfully retrieved parameter descriptions")
                    return result
                else:
                    error_result = {
                        "status": "error",
                        "message": "System parameters service not available"
                    }
                    await ctx.error("System parameters service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error getting parameter descriptions: {str(e)}")
                raise
        
        # Tool to connect to external agents via MCP protocol - this will need access to MCP client service
        @self.mcp_server.tool(
            name="system.connect_external_agent",
            description="Connect to an external agent using MCP protocol with specified connection parameters (type can be 'stdio' or 'http')"
        )
        async def connect_external_agent_tool(ctx: Context[ServerSession, None], agent_id: str, connection_params: Dict[str, Any]):
            await ctx.info(f"Connecting to external agent {agent_id}")
            try:
                # Note: We'll need access to the MCP client service to make this call
                # This will be resolved when the services are properly integrated
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    result = await self.gcs_runtime.mcp_client_service.connect_to_external_agent(agent_id, connection_params)
                    if result.get("success"):
                        await ctx.info(f"Successfully connected to external agent {agent_id}")
                    else:
                        await ctx.warn(f"Failed to connect to external agent {agent_id}: {result.get('message')}")
                    return result
                else:
                    error_result = {
                        "success": False,
                        "message": "MCP client service not available"
                    }
                    await ctx.error("MCP client service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error connecting to external agent {agent_id}: {str(e)}")
                raise
        
        # Tool to get list of connected external agents
        @self.mcp_server.tool(
            name="system.list_connected_agents",
            description="Get a list of currently connected external agents"
        )
        async def list_connected_agents_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing connected external agents")
            try:
                # Note: We'll need access to the MCP client service to make this call
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    result = self.gcs_runtime.mcp_client_service.get_connected_agents()
                    await ctx.info(f"Successfully retrieved {result.get('count', 0)} connected agents")
                    return result
                else:
                    error_result = {
                        "success": False,
                        "connected_agents": [],
                        "count": 0,
                        "message": "MCP client service not available"
                    }
                    await ctx.error("MCP client service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error listing connected agents: {str(e)}")
                raise
        
        # Tool to disconnect from an external agent
        @self.mcp_server.tool(
            name="system.disconnect_external_agent",
            description="Disconnect from an external agent by its ID"
        )
        async def disconnect_external_agent_tool(ctx: Context[ServerSession, None], agent_id: str):
            await ctx.info(f"Disconnecting from external agent {agent_id}")
            try:
                # Note: We'll need access to the MCP client service to make this call
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    result = await self.gcs_runtime.mcp_client_service.disconnect_from_external_agent(agent_id)
                    if result.get("success"):
                        await ctx.info(f"Successfully disconnected from external agent {agent_id}")
                    else:
                        await ctx.warn(f"Failed to disconnect from external agent {agent_id}: {result.get('message')}")
                    return result
                else:
                    error_result = {
                        "success": False,
                        "message": "MCP client service not available"
                    }
                    await ctx.error("MCP client service not available")
                    return error_result
            except Exception as e:
                await ctx.error(f"Error disconnecting from external agent {agent_id}: {str(e)}")
                raise


        
        # Tool to list all available system tools
        @self.mcp_server.tool(
            name="system.list_all_tools",
            description="List all available tools in the system including system services, MCP tools, and agent methods"
        )
        async def list_all_tools_tool(ctx: Context[ServerSession, None]):
            await ctx.info("Listing all available system tools")
            try:
                # Build comprehensive list of all tools available in the system
                tools_info = {
                    "mcp_server_tools": {
                        "name": "MCP Server Tools",
                        "description": "Tools provided by the MCP server functionality",
                        "tools": {}
                    },
                    "mcp_client_tools": {
                        "name": "MCP Client Tools", 
                        "description": "Tools for connecting to external MCP agents",
                        "tools": {}
                    },
                    "system_services": {
                        "name": "System Services",
                        "description": "Core system services available",
                        "tools": {}
                    },
                    "agent_methods": {
                        "name": "Agent Methods",
                        "description": "Methods available on registered agents",
                        "tools": {}
                    }
                }
                
                # Add tools registered in the MCP server
                tools_result = await ctx.session.list_tools()
                server_tools = {}
                for tool in tools_result.get('tools', []):
                    name = tool.get("name")
                    if name:
                        server_tools[name] = {
                            "description": tool.get("description", ""),
                            "input_schema": tool.get("inputSchema", {})
                        }
                
                tools_info["mcp_server_tools"]["tools"] = server_tools
                
                # Add MCP client tools info if available
                if hasattr(self.gcs_runtime, 'mcp_client_service'):
                    client_tools_info = self.gcs_runtime.mcp_client_service.get_registered_external_tools()
                    tools_info["mcp_client_tools"]["tools"] = client_tools_info.get("external_agent_tools", {})
                
                # Add system service tools (config and system parameters)
                # Add config service tools
                config_service_methods = self._get_config_service_methods()
                if config_service_methods:
                    tools_info["system_services"]["tools"]["ConfigService"] = config_service_methods
                
                # Add system parameters service tools
                system_params_service_methods = self._get_system_parameters_service_methods()
                if system_params_service_methods:
                    tools_info["system_services"]["tools"]["SystemParametersService"] = system_params_service_methods
                
                # Add agent methods - skip since agents property is removed
                # In a complete implementation, this would use the agent service
                
                result = {
                    "status": "success",
                    "tools": tools_info,
                    "total_tools_count": sum(len(cat.get("tools", {})) for cat in tools_info.values()) + 
                                    sum(len(methods) for agent_tools in tools_info["system_services"]["tools"].values() for methods in agent_tools.values())
                }
                await ctx.info(f"Successfully listed all tools: {result['total_tools_count']} total")
                return result
            except Exception as e:
                await ctx.error(f"Error listing all tools: {str(e)}")
                error_result = {
                    "status": "error",
                    "message": f"Error retrieving tool list: {str(e)}"
                }
                return error_result
    
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
    
    def _get_config_service_methods(self) -> Dict[str, Any]:
        """Get methods from the config service that should be exposed as tools.
        
        Returns:
            Dict of method names with their schemas and descriptions.
        """
        methods = {}
        # Define config service methods with proper schemas
        methods["config.list_configurations"] = {
            "description": "List all available system configurations",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
        
        methods["config.load_configuration"] = {
            "description": "Load a specific system configuration by name",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "config_name": {
                        "type": "string", 
                        "description": "Name of the configuration to load", 
                        "required": True
                    }
                }, 
                "required": ["config_name"]
            }
        }
        
        methods["config.get_configuration"] = {
            "description": "Get a specific system configuration from cache or file",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "config_name": {
                        "type": "string", 
                        "description": "Name of the configuration to get", 
                        "required": True
                    }
                }, 
                "required": ["config_name"]
            }
        }
        
        methods["config.get_all_cached_configs"] = {
            "description": "Get all currently cached configurations",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
        
        methods["config.clear_config_cache"] = {
            "description": "Clear the configuration cache",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
        
        return methods
    
    def _get_system_parameters_service_methods(self) -> Dict[str, Any]:
        """Get methods from the system parameters service that should be exposed as tools.
        
        Returns:
            Dict of method names with their schemas and descriptions.
        """
        methods = {}
        # Define system parameters service methods with proper schemas
        methods["system.get_parameters"] = {
            "description": "Get current system parameter values",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
        
        methods["system.set_parameter"] = {
            "description": "Set a system parameter value",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "parameter_name": {
                        "type": "string", 
                        "description": "Name of the parameter to set", 
                        "required": True
                    },
                    "parameter_value": {
                        "type": "string", 
                        "description": "New value for the parameter", 
                        "required": True
                    }
                }, 
                "required": ["parameter_name", "parameter_value"]
            }
        }
        
        methods["system.get_parameter_descriptions"] = {
            "description": "Get descriptions of all system parameters",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
        
        return methods
    
    def _register_method_as_tool(self, agent_name: str, method_name: str, is_system_tool: bool = False):
        """Register an agent method as an MCP tool (server role).
        
        Args:
            agent_name: Name of the agent.
            method_name: Name of the method to register.
            is_system_tool: Flag to indicate if this is a system tool vs dynamic agent.
        """
        # Skip registration since agents property is removed
        # In a complete implementation, this would use the agent service
        pass
    
    def start_server(self, transport: str = "stdio"):
        """Start the MCP server (so GCS can be used by upstream orchestrators).
        
        Args:
            transport: Transport protocol to use - 'stdio', 'sse', or 'streamable-http'
        """
        if transport == "stdio":
            return self.mcp_server.run()
        elif transport == "streamable-http":
            return self.mcp_server.run_streamable_http()
        elif transport == "sse":
            return self.mcp_server.run_sse()
        else:
            raise ValueError(f"Unsupported transport: {transport}. Use 'stdio', 'streamable-http', or 'sse'")
    
    async def start_server_async(self, transport: str = "stdio"):
        """Start the MCP server asynchronously.
        
        Args:
            transport: Transport protocol to use - 'stdio', 'sse', or 'streamable-http'
        """
        if transport == "stdio":
            return await self.mcp_server.run_async()
        elif transport == "streamable-http":
            return await self.mcp_server.run_streamable_http_async()
        elif transport == "sse":
            return await self.mcp_server.run_sse_async()
        else:
            raise ValueError(f"Unsupported transport: {transport}. Use 'stdio', 'streamable-http', or 'sse'")

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