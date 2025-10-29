"""
System tools for the GCS Kernel.

This module implements system-level tools that provide access to kernel functionality
through the same interface as other tools.
"""

from typing import Dict, Any
from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class ListToolsTool:
    """
    System tool to list all available tools in the kernel.
    """
    name = "list_tools"
    display_name = "List Tools"
    description = "List all available tools in the kernel"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the list tools tool.
        
        Args:
            parameters: The parameters for tool execution (none required)
            
        Returns:
            A ToolResult containing the execution result
        """
        try:
            if not self.kernel or not self.kernel.registry:
                result = "No tools available - kernel registry not initialized"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    llm_content=result,
                    return_display=result
                )
            
            tools = self.kernel.registry.get_all_tools()
            if not tools:
                result = "No tools are currently registered in the system"
            else:
                tool_list = []
                for name, tool in tools.items():
                    description = getattr(tool, 'description', 'No description')
                    tool_list.append(f"  - {name}: {description}")
                
                result = "Available tools:\n" + "\n".join(tool_list)
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error listing tools: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class GetToolInfoTool:
    """
    System tool to get information about a specific tool.
    """
    name = "get_tool_info"
    display_name = "Get Tool Info"
    description = "Get detailed information about a specific tool"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "The name of the tool to get information for"
            }
        },
        "required": ["tool_name"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the get tool info tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        tool_name = parameters.get("tool_name")
        
        if not tool_name:
            error_msg = "Missing required parameter: tool_name"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            if not self.kernel or not self.kernel.registry:
                error_msg = "Kernel registry not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            tool = await self.kernel.registry.get_tool(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Get tool information
            name = getattr(tool, 'name', tool_name)
            description = getattr(tool, 'description', 'No description')
            display_name = getattr(tool, 'display_name', name)
            schema = getattr(tool, 'parameters', {})
            
            result = f"Tool Information for '{tool_name}':\n"
            result += f"  Name: {name}\n"
            result += f"  Display Name: {display_name}\n"
            result += f"  Description: {description}\n"
            result += f"  Parameters Schema: {schema}"
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error getting tool info for '{tool_name}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )