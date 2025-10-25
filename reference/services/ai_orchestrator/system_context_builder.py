"""
System Context Builder for the GCS Kernel AI Orchestrator.

This module implements the SystemContextBuilder which constructs
system-level context for AI interactions, including available tools,
capabilities, and relevant context information.
"""

import asyncio
from typing import Dict, Any, List
from gcs_kernel.mcp.client import MCPClient


class SystemContextBuilder:
    """
    Builder for system context that provides the AI model with
    information about its environment, capabilities, and available tools.
    """
    
    def __init__(self, kernel_client: MCPClient, kernel=None):
        """
        Initialize the system context builder.
        
        Args:
            kernel_client: MCP client for communicating with the kernel server
            kernel: Optional direct reference to the kernel instance for direct access to registry
        """
        self.kernel_client = kernel_client
        self.kernel = kernel

    async def get_available_tools(self) -> Dict[str, Any]:
        """
        Get all available tools from the kernel.
        
        Returns:
            A dictionary of available tools
        """
        try:
            # Try to use direct kernel access first (for efficiency)
            if self.kernel and hasattr(self.kernel, 'registry') and self.kernel.registry:
                tools = self.kernel.registry.get_all_tools()
                # Format tools to match the expected response structure
                formatted_tools = {}
                for name, tool in tools.items():
                    formatted_tools[name] = {
                        'name': getattr(tool, 'name', name),
                        'description': getattr(tool, 'description', 'No description'),
                        'parameter_schema': getattr(tool, 'parameter_schema', {}),
                        'display_name': getattr(tool, 'display_name', name)
                    }
                return formatted_tools
            else:
                # Fall back to getting tools via MCP client
                response = await self.kernel_client.list_tools()
                # If response is a coroutine (e.g., from AsyncMock in testing), await it
                if asyncio.iscoroutine(response):
                    response = await response
                # The MCP server returns tools in the format {"tools": [...]}
                # Convert to the expected format {name: tool_info}
                if "tools" in response:
                    formatted_tools = {}
                    for tool_info in response["tools"]:
                        name = tool_info.get("name", "unknown")
                        formatted_tools[name] = tool_info
                    return formatted_tools
                elif isinstance(response, dict) and all(isinstance(k, str) for k in response.keys()):
                    # If response is already in the format {name: tool_info}, return as is
                    return response
                else:
                    # Otherwise return an empty dict
                    return {}
        except Exception:
            # Return empty dict if tools can't be retrieved
            return {}

    async def build_system_context(self, additional_context: str = None) -> str:
        """
        Build system context with information about available tools and capabilities.
        
        Args:
            additional_context: Optional additional context to include
            
        Returns:
            System context string with tool information and other capabilities
        """
        # Get available tools from the kernel
        available_tools = await self.get_available_tools()
        
        # Start building the system context
        if available_tools:
            # Include explicit tool names in the initial system message to make them prominent
            tool_names = ', '.join([tool_name for tool_name in available_tools.keys()])
            system_context = f"You are an AI assistant with specific capabilities in the GCS Kernel system. You have access to these tools: {tool_names}.\\n\\n"
            
            system_context += "Available tools:\\n\\n"
            
            for tool_name, tool_info in available_tools.items():
                description = tool_info.get('description', 'No description')
                schema = tool_info.get('parameter_schema', {})
                system_context += f"- {tool_name}: {description}\\n"
                if schema:
                    system_context += f"  Parameters: {schema}\\n"
                system_context += "\\n"
        else:
            system_context = "You are an AI assistant with specific capabilities in the GCS Kernel system.\\n\\n"
            system_context += "No tools are currently available.\\n\\n"
        
        # Add instructions for using tools
        system_context += (
            "When you need to use a tool, respond in JSON format with a tool_call object:\\n"
            "{\\n"
            '  "name": "tool_name",\\n'
            '  "arguments": {\\n'
            '    "param1": "value1",\\n'
            '    "param2": "value2"\\n'
            "  }\\n"
            "}\\n\\n"
        )
        
        system_context += (
            "Only use tools when necessary to fulfill the user's request. "
            "If a tool can help answer the user's question or perform a task, "
            "use it appropriately. Otherwise, respond directly to the user.\\n\\n"
        )
        
        # Add any additional context if provided
        if additional_context:
            system_context += f"{additional_context}\\n\\n"
        
        # Add general guidance
        system_context += (
            "You are operating within the GCS Kernel system. Follow best practices for "
            "safety, security, and efficiency when executing tasks or using tools."
        )
        
        return system_context