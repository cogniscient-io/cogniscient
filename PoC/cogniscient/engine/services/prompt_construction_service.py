"""
Prompt Construction Service for Adaptive Control System that handles
the construction of system messages, domain context, agent capabilities
and other contextual information that was previously embedded in the
Contextual LLM service.
"""
import logging
from typing import Dict, Any, Optional, List
from cogniscient.engine.services.mcp_client_service import MCPClientService
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class PromptConstructionService:
    """
    Service that handles the construction of prompts with contextual information,
    including system messages, domain context, agent capabilities, and system services.
    This separates the prompt construction logic from the LLM communication logic.
    """
    
    def __init__(self, agent_registry: Optional[Dict[str, Any]] = None, 
                 system_services: Optional[Dict[str, Any]] = None, 
                 mcp_client_service: Optional[MCPClientService] = None):
        """
        Initialize the prompt construction service.
        
        Args:
            agent_registry: Agent registry information
            system_services: System services information  
            mcp_client_service: MCP client service for external agent connections
        """
        self.agent_registry = agent_registry
        self.system_services = system_services or {}
        self.mcp_client_service = mcp_client_service
        
    def construct_contextual_messages(
        self,
        user_input: str,
        domain: Optional[str] = None,
        agent_registry: Optional[Dict[str, Any]] = None,
        include_agent_capabilities: bool = True,
        include_system_services: bool = True
    ) -> List[Dict[str, str]]:
        """
        Construct messages with contextual information.
        
        Args:
            user_input: The user's input to include in the messages
            domain: Domain context to add to the system message
            agent_registry: Optional agent registry to override the default
            include_agent_capabilities: Whether to include agent capabilities
            include_system_services: Whether to include system service information
            
        Returns:
            List of message dictionaries ready to send to the LLM
        """
        messages = []
        system_content = ""
        
        # Add domain context if provided
        if domain:
            system_content += (f"You are an expert in the {domain} domain. "
                              f"Please explain the error with information specific "
                              f"to this domain and provide options to resolve it.\n")
        
        # Use provided agent registry or fall back to instance agent registry
        registry_to_use = agent_registry or self.agent_registry
        
        # Include agent capabilities if requested and available
        if include_agent_capabilities and registry_to_use:
            agent_capabilities = self._format_agent_capabilities(registry_to_use)
            if agent_capabilities:
                system_content += agent_capabilities
        
        # Include system service capabilities if requested
        if include_system_services:
            system_service_capabilities = self._format_system_service_capabilities()
            if system_service_capabilities:
                system_content += system_service_capabilities
        
        # Add system message if there's content
        if system_content.strip():
            messages.append({"role": "system", "content": system_content})
        
        # Add the user input as a user message
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _format_agent_capabilities(self, agent_registry: Dict[str, Any]) -> str:
        """
        Format agent capabilities for inclusion in system prompt.
        
        Args:
            agent_registry: Agent registry information
            
        Returns:
            Formatted agent capabilities string
        """
        if not agent_registry:
            return ""
        
        capabilities_str = "\n[AGENT_REGISTRY]\n"
        for name, agent in agent_registry.items():
            # Try to get agent description
            desc = getattr(agent, "description", f"Agent {name}")
            
            # Try to get agent capabilities/methods if available
            capabilities_str += f"- {name}: {desc}\n"
            
            # If agent has a self_describe method, use it for more detailed info
            if hasattr(agent, "self_describe"):
                try:
                    agent_info = agent.self_describe()
                    methods = agent_info.get("methods", {})
                    if methods:
                        capabilities_str += "  Available methods:\n"
                        for method_name, method_info in methods.items():
                            method_desc = method_info.get("description", "")
                            capabilities_str += f"  - {method_name}: {method_desc}\n"
                            parameters = method_info.get("parameters", {})
                            if parameters:
                                capabilities_str += "    Parameters:\n"
                                for param_name, param_info in parameters.items():
                                    param_type = param_info.get("type", "any")
                                    param_desc = param_info.get("description", "")
                                    required = " (required)" if param_info.get("required", False) else ""
                                    capabilities_str += f"    - {param_name}: {param_type} - {param_desc}{required}\n"
                except Exception:
                    # If self_describe fails, continue with basic info
                    pass
        
        capabilities_str += "[/AGENT_REGISTRY]\n"
        return capabilities_str
    
    def _format_system_service_capabilities(self) -> str:
        """
        Format system service capabilities for inclusion in system prompt.
        
        Returns:
            Formatted system service capabilities string
        """
        # With MCP integration, system service capabilities should be discovered dynamically
        # through the MCP client instead of having them statically provided here
        capabilities_str = "\n[SYSTEM_SERVICES]\n"
        capabilities_str += "Note: System services are available via MCP (Model Context Protocol).\n"
        capabilities_str += "Use MCP client tools to discover and invoke system service capabilities dynamically:\n"
        capabilities_str += "- config.list_configurations: List all available system configurations\n"
        capabilities_str += "- config.load_configuration: Load a specific system configuration by name\n"
        capabilities_str += "- config.get_configuration: Get a specific system configuration\n"
        capabilities_str += "- config.get_all_cached_configs: Get all cached configurations\n"
        capabilities_str += "- config.clear_config_cache: Clear the configuration cache\n"
        capabilities_str += "- system.get_parameters: Get current system parameter values\n"
        capabilities_str += "- system.set_parameter: Set a system parameter value\n"
        capabilities_str += "- system.get_parameter_descriptions: Get descriptions of all system parameters\n"
        
        capabilities_str += "[/SYSTEM_SERVICES]\n"
        
        # Include MCP client capabilities if available
        if self.mcp_client_service:
            capabilities_str += self._format_mcp_client_capabilities()
        
        return capabilities_str
    
    def _format_mcp_client_capabilities(self) -> str:
        """
        Format MCP client service capabilities for inclusion in system prompt.
        
        Returns:
            Formatted MCP client service capabilities string
        """
        # Since MCP functionality is now properly exposed as the MCPClient agent,
        # we don't need to present standalone mcp_* tools in the system capabilities.
        # The LLM can access all MCP functionality through the MCPClient agent methods.
        return ""
    
    def get_all_available_tools(self) -> Dict[str, Any]:
        """
        Get a comprehensive list of all available tools in the system.
        
        Returns:
            Dict containing all available tools organized by type
        """
        tools_info = {
            "system_services": {},
            "mcp_tools": {},
            "agent_methods": {},
            "connected_external_agent_tools": {}
        }
        
        # 1. System services - now available via MCP, so we'll keep an empty dict
        # The actual tools are available through the MCP client service
        tools_info["system_services"] = {}
        
        # 2. MCP client tools for LLM control (using internal mcp. namespace, not system. namespace)
        if self.mcp_client_service:
            tools_info["mcp_tools"] = {
                "mcp.connect_external_agent": {
                    "description": "Connect to an external agent using MCP protocol",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True},
                        "connection_params": {"type": "object", "description": "Connection parameters including type, url/command, etc.", "required": True}
                    }
                },
                "mcp.list_connected_agents": {
                    "description": "Get a list of currently connected external agents",
                    "parameters": {}
                },
                "mcp.disconnect_external_agent": {
                    "description": "Disconnect from an external agent by its ID",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent to disconnect", "required": True}
                    }
                },
                "mcp.list_external_agent_capabilities": {
                    "description": "Get capabilities (tools) of a connected external agent",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True}
                    }
                },
                "mcp.call_external_agent_tool": {
                    "description": "Call a specific tool on a connected external agent",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True},
                        "tool_name": {"type": "string", "description": "Name of the tool to call", "required": True},
                        "tool_parameters": {"type": "object", "description": "Parameters to pass to the tool", "required": False}
                    }
                }
            }
            
            # Also include tools from connected external agents
            connected_tools = self.mcp_client_service.get_registered_external_tools()
            if connected_tools.get("success"):
                tools_info["connected_external_agent_tools"] = connected_tools.get("external_agent_tools", {})
        
        # 3. Agent methods (if agent registry is available)
        if self.agent_registry:
            for agent_name, agent_instance in self.agent_registry.items():
                agent_methods = {}
                if hasattr(agent_instance, "self_describe"):
                    try:
                        agent_info = agent_instance.self_describe()
                        agent_methods = agent_info.get("methods", {})
                    except Exception:
                        # If self_describe fails, try to extract methods using introspection
                        for attr_name in dir(agent_instance):
                            if not attr_name.startswith('_') and callable(getattr(agent_instance, attr_name)):
                                agent_methods[attr_name] = {
                                    "description": f"Method {attr_name} on agent {agent_name}",
                                    "parameters": {}
                                }
                
                if agent_methods:
                    tools_info["agent_methods"][agent_name] = agent_methods
        
        return tools_info
    
    def close(self):
        """Close any resources held by the prompt construction service."""
        # Currently, the prompt construction service doesn't hold any async resources
        # But we include this for consistency with other services
        pass