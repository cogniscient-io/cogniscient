#!/usr/bin/env python3
"""
MCP Client Agent - Agent wrapper for MCP client functionality.
"""

from typing import Dict, Any, Optional
import asyncio
from cogniscient.engine.gcs_runtime import GCSRuntime


class MCPClientAgent:
    """Agent wrapper for MCP client functionality."""
    
    def __init__(self, gcs_runtime: GCSRuntime):
        """Initialize the MCP client agent.
        
        Args:
            gcs_runtime: GCS runtime instance for accessing MCP services
        """
        self.gcs_runtime = gcs_runtime
        self.name = "MCPClient"
        self.description = "Agent for managing MCP client connections and external agent interactions"
        
    def self_describe(self) -> Dict[str, Any]:
        """Describe this agent's capabilities.
        
        Returns:
            Dict describing agent capabilities
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": "1.0.0",
            "methods": {
                "connect_external_agent": {
                    "description": "Connect to an external agent using MCP protocol",
                    "parameters": {
                        "agent_id": {
                            "type": "string",
                            "description": "Unique identifier for the external agent",
                            "required": True
                        },
                        "connection_params": {
                            "type": "object",
                            "description": "Connection parameters including type, url/command, headers, and authorization",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["stdio", "http"],
                                    "description": "Type of connection ('stdio' or 'http')"
                                },
                                "url": {
                                    "type": "string",
                                    "description": "URL for HTTP connections (required if type is 'http')"
                                },
                                "command": {
                                    "type": "string",
                                    "description": "Command for stdio connections (required if type is 'stdio')"
                                },
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
                "list_connected_agents": {
                    "description": "Get a list of currently connected external agents",
                    "parameters": {}
                },
                "disconnect_external_agent": {
                    "description": "Disconnect from an external agent by its ID",
                    "parameters": {
                        "agent_id": {
                            "type": "string",
                            "description": "Unique identifier for the external agent to disconnect",
                            "required": True
                        }
                    }
                },
                "list_external_agent_capabilities": {
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
                        },
                        "tool_parameters": {
                            "type": "object",
                            "description": "Parameters to pass to the tool",
                            "required": False
                        }
                    }
                }
            }
        }
    
    async def connect_external_agent(self, agent_id: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to an external agent using MCP protocol.
        
        Args:
            agent_id: Unique identifier for the external agent
            connection_params: Connection parameters including type, url/command, headers, and authorization
            
        Returns:
            Dict with success status and connection information
        """
        if not hasattr(self.gcs_runtime, 'mcp_service') or not hasattr(self.gcs_runtime.mcp_service, 'mcp_client'):
            return {
                "success": False,
                "message": "MCP client service not available"
            }
        
        try:
            result = await self.gcs_runtime.mcp_service.mcp_client.connect_to_external_agent(
                agent_id=agent_id,
                connection_params=connection_params
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect to external agent {agent_id}: {str(e)}"
            }
    
    def list_connected_agents(self) -> Dict[str, Any]:
        """Get a list of currently connected external agents.
        
        Returns:
            Dict with success status and list of connected agents
        """
        if not hasattr(self.gcs_runtime, 'mcp_service') or not hasattr(self.gcs_runtime.mcp_service, 'mcp_client'):
            return {
                "success": False,
                "message": "MCP client service not available"
            }
        
        try:
            result = self.gcs_runtime.mcp_service.mcp_client.get_connected_agents()
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list connected agents: {str(e)}"
            }
    
    async def disconnect_external_agent(self, agent_id: str) -> Dict[str, Any]:
        """Disconnect from an external agent by its ID.
        
        Args:
            agent_id: Unique identifier for the external agent to disconnect
            
        Returns:
            Dict with success status and disconnection information
        """
        if not hasattr(self.gcs_runtime, 'mcp_service') or not hasattr(self.gcs_runtime.mcp_service, 'mcp_client'):
            return {
                "success": False,
                "message": "MCP client service not available"
            }
        
        try:
            result = await self.gcs_runtime.mcp_service.mcp_client.disconnect_from_external_agent(agent_id)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to disconnect from external agent {agent_id}: {str(e)}"
            }
    
    async def list_external_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get capabilities (tools) of a connected external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            
        Returns:
            Dict with success status and agent capabilities
        """
        if not hasattr(self.gcs_runtime, 'mcp_service') or not hasattr(self.gcs_runtime.mcp_service, 'mcp_client'):
            return {
                "success": False,
                "message": "MCP client service not available"
            }
        
        try:
            result = await self.gcs_runtime.mcp_service.mcp_client.get_external_agent_capabilities(agent_id)
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get capabilities for external agent {agent_id}: {str(e)}"
            }
    
    async def call_external_agent_tool(self, agent_id: str, tool_name: str, tool_parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on a connected external agent.
        
        Args:
            agent_id: Unique identifier for the external agent
            tool_name: Name of the tool to call
            tool_parameters: Parameters to pass to the tool
            
        Returns:
            Result from the tool call
        """
        if not hasattr(self.gcs_runtime, 'mcp_service') or not hasattr(self.gcs_runtime.mcp_service, 'mcp_client'):
            return {
                "success": False,
                "message": "MCP client service not available"
            }
        
        try:
            result = await self.gcs_runtime.mcp_service.mcp_client.call_external_agent_tool(
                agent_id=agent_id,
                tool_name=tool_name,
                **(tool_parameters or {})
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to call tool {tool_name} on external agent {agent_id}: {str(e)}"
            }