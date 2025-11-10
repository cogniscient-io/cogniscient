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
        Execute the tool call using the ToolExecutionManager's unified execution interface.

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

        # Use the unified execute_tool_call method which handles routing internally
        execution_result = await tool_execution_manager.execute_tool_call(self)
        # Ensure the result has the expected format, particularly the tool_call_id
        tool_call_result = execution_result.get('result', execution_result)
        
        return {
            "tool_call_id": self.id,
            "tool_name": self.name,
            "result": tool_call_result if isinstance(tool_call_result, ToolResult) else ToolResult(
                tool_name=self.name,
                success=False,
                error="Invalid result format from execution",
                llm_content="Invalid result format from execution",
                return_display="Invalid result format from execution"
            ),
            "success": getattr(tool_call_result, 'success', False)
        }