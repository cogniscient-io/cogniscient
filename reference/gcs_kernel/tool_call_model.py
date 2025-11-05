"""
Tool Call Model for the GCS Kernel.

This module defines the ToolCall class which represents a tool call from an LLM response.
It follows OpenAI-compatible format and provides methods for executing the tool calls.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List

from gcs_kernel.models import ToolResult


class ToolCall:
    """
    Represents a tool call from the LLM response.
    Uses OpenAI-compatible format to minimize conversion.
    The arguments field is stored as JSON string as per OpenAI API format.
    """
    def __init__(self, id: str = "", function: dict = None, type: str = "function"):
        """
        Initialize a ToolCall instance with OpenAI-compatible format.
        
        Args:
            id: The ID of the tool call
            function: Dict with 'name' and 'arguments' keys (OpenAI format)
                     Arguments should be a JSON string as per OpenAI format
            type: The type of tool call (default: "function")
        """
        self.id = id
        self.function = function or {"name": "", "arguments": "{}"}
        self.type = type
        
        # Maintain backward compatibility properties
        self.name = self.function.get("name", "")
        
        # Arguments in OpenAI format are JSON strings, but we'll provide 
        # a parsed property for convenience
        raw_arguments = self.function.get("arguments", "{}")
        if isinstance(raw_arguments, str):
            try:
                self.arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                # If parsing fails, keep as original string value
                self.arguments = raw_arguments
        else:
            # If arguments are already a dict, store as-is and also as JSON string
            self.arguments = raw_arguments
            self.function["arguments"] = json.dumps(raw_arguments)
        
        self.parameters = self.arguments  # For compatibility
    
    @property
    def arguments_json(self) -> str:
        """
        Get arguments as JSON string (the OpenAI format).
        """
        if isinstance(self.function.get("arguments"), str):
            return self.function["arguments"]
        else:
            # Convert dict to JSON string if needed
            return json.dumps(self.arguments)
    
    @classmethod
    def from_dict_arguments(cls, id: str = "", name: str = "", arguments: Dict[str, Any] = None):
        """
        Create a ToolCall from name and arguments dict (common use case).
        Converts the dict arguments to JSON string as per OpenAI format.
        
        Args:
            id: The ID of the tool call
            name: The name of the tool to call
            arguments: The arguments to pass to the tool as a dict
        """
        return cls(
            id=id,
            function={
                "name": name,
                "arguments": json.dumps(arguments or {})
            }
        )
    
    @classmethod
    def from_json_arguments(cls, id: str = "", name: str = "", arguments_json: str = "{}"):
        """
        Create a ToolCall from name and arguments JSON string (OpenAI format).
        
        Args:
            id: The ID of the tool call
            name: The name of the tool to call
            arguments_json: The arguments to pass to the tool as a JSON string
        """
        return cls(
            id=id,
            function={
                "name": name,
                "arguments": arguments_json
            }
        )
    
    @classmethod
    def from_openai_format(cls, openai_tool_call: dict):
        """
        Create a ToolCall from OpenAI format dictionary.
        
        Args:
            openai_tool_call: Dictionary in OpenAI format: 
                             {"id": "...", "function": {"name": "...", "arguments": "..."}, "type": "..."}
        
        Returns:
            ToolCall instance
        """
        return cls(
            id=openai_tool_call.get("id", ""),
            function={
                "name": openai_tool_call.get("function", {}).get("name", ""),
                "arguments": openai_tool_call.get("function", {}).get("arguments", "{}")
            },
            type=openai_tool_call.get("type", "function")  # Default to "function" if not provided
        )
    
    def to_openai_format(self) -> dict:
        """
        Convert this ToolCall to OpenAI format dictionary.
        
        Returns:
            Dictionary in OpenAI format: {"id": "...", "function": {"name": "...", "arguments": "..."}, "type": "function"}
        """
        return {
            "id": self.id,
            "function": {
                "name": self.function.get("name", ""),
                "arguments": self.function.get("arguments", "{}")
            },
            "type": self.type
        }
    
    @staticmethod
    def ensure_openai_format(tool_call) -> dict:
        """
        Ensure a tool call is in OpenAI format, converting if necessary.
        
        Args:
            tool_call: Either a dictionary in OpenAI format or a ToolCall object
            
        Returns:
            Dictionary in OpenAI format: {"id": "...", "function": {"name": "...", "arguments": "..."}, "type": "function"}
        """
        if isinstance(tool_call, dict):
            # Already in OpenAI format
            return {
                "id": tool_call.get("id", ""),
                "function": {
                    "name": tool_call.get("function", {}).get("name", ""),
                    "arguments": tool_call.get("function", {}).get("arguments", "{}")
                },
                "type": tool_call.get("type", "function")  # Default to "function" if not provided
            }
        elif isinstance(tool_call, ToolCall):
            # Convert ToolCall object to OpenAI format
            return tool_call.to_openai_format()
        else:
            # If it's some other format, try to extract what we can
            return {
                "id": getattr(tool_call, 'id', ""),
                "function": {
                    "name": getattr(tool_call, 'name', ""),
                    "arguments": getattr(tool_call, 'arguments_json', "{}") 
                                 if hasattr(tool_call, 'arguments_json') 
                                 else getattr(tool_call, 'function', {}).get("arguments", "{}")
                },
                "type": getattr(tool_call, 'type', 'function')  # Default to "function" if not provided
            }

    async def execute_with_manager(self, tool_execution_manager) -> Dict[str, Any]:
        """
        Execute the tool call using the ToolExecutionManager to determine the appropriate execution path.
        
        Args:
            tool_execution_manager: The ToolExecutionManager to handle the actual execution
            
        Returns:
            Dictionary containing the result of the tool execution
        """
        if not tool_execution_manager:
            error_result = ToolResult(
                tool_name=self.name,
                llm_content="No ToolExecutionManager available to execute tools",
                return_display="No ToolExecutionManager available to execute tools",
                success=False,
                error="No ToolExecutionManager available to execute tools"
            )
            return {
                "tool_call_id": self.id,
                "tool_name": self.name,
                "result": error_result,
                "success": False
            }
        
        # Check if the tool exists in the registry (either local or external)
        if not (tool_execution_manager.registry and 
                hasattr(tool_execution_manager.registry, 'has_tool') and 
                await tool_execution_manager.registry.has_tool(self.name)):
            # Tool is not registered, return error
            error_result = ToolResult(
                tool_name=self.name,
                llm_content=f"Tool '{self.name}' is not registered and cannot be executed",
                return_display=f"Tool '{self.name}' is not registered and cannot be executed",
                success=False,
                error=f"Tool '{self.name}' is not registered"
            )
            return {
                "tool_call_id": self.id,
                "tool_name": self.name,
                "result": error_result,
                "success": False
            }
        
        # Tool is registered, determine if it's local or external
        server_config = await tool_execution_manager.registry.get_tool_server_config(self.name)
        if server_config:
            # This is an external tool registered with an MCP server, use execute_external_tool_via_mcp method
            try:
                result = await tool_execution_manager.execute_external_tool_via_mcp(
                    self.name,
                    self.arguments
                )
                
                return {
                    "tool_call_id": self.id,
                    "tool_name": self.name,
                    "result": result,
                    "success": result.success,
                    "execution_id": f"external_{self.id}"
                }
            except Exception as e:
                error_result = ToolResult(
                    tool_name=self.name,
                    llm_content=f"External tool execution failed: {str(e)}",
                    return_display=f"External tool execution failed: {str(e)}",
                    success=False,
                    error=str(e)
                )
                return {
                    "tool_call_id": self.id,
                    "tool_name": self.name,
                    "result": error_result,
                    "success": False,
                    "execution_id": f"external_{self.id}"
                }
        else:
            # This is a local tool, use execute_internal_tool method
            try:
                result = await tool_execution_manager.execute_internal_tool(
                    self.name, 
                    self.arguments
                )
                
                return {
                    "tool_call_id": self.id,
                    "tool_name": self.name,
                    "result": result,
                    "success": result.success,
                    "execution_id": f"internal_{self.id}"
                }
            except Exception as e:
                error_result = ToolResult(
                    tool_name=self.name,
                    llm_content=f"Internal tool execution failed: {str(e)}",
                    return_display=f"Internal tool execution failed: {str(e)}",
                    success=False,
                    error=str(e)
                )
                return {
                    "tool_call_id": self.id,
                    "tool_name": self.name,
                    "result": error_result,
                    "success": False,
                    "execution_id": f"internal_{self.id}"
                }