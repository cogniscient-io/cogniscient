"""
System tools for the GCS Kernel.

This module implements system-level tools that provide access to kernel functionality
through the same interface as other tools.
"""

import logging
from typing import Dict, Any
from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class SetLogLevelTool:
    """
    System tool to change the current logging level.
    """
    name = "set_log_level"
    display_name = "Set Log Level"
    description = "Change the current application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "description": "The logging level to set"
            }
        },
        "required": ["level"]
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
        Execute the set log level tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        level = parameters.get("level", "").upper()
        
        if not level:
            error_msg = "Missing required parameter: level"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        # Validate the log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            error_msg = f"Invalid log level: {level}. Valid levels are: {', '.join(valid_levels)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Convert the log level string to the corresponding logging constant
            numeric_level = getattr(logging, level, None)
            if not isinstance(numeric_level, int):
                error_msg = f"Invalid log level: {level}"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Update the log level of the root logger
            logging.getLogger().setLevel(numeric_level)
            
            # Update the log level in our config module
            from services.config import settings, configure_logging
            settings.log_level = level
            configure_logging()  # Reconfigure logging with the new level
            
            result = f"Log level successfully changed to {level}"
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error setting log level to {level}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


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