"""
Improved tool calling functionality for the GCS Kernel.

This module provides enhanced tool call processing with proper validation and error handling.
"""
from typing import Any, Dict, List


import json

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


def process_tool_calls_in_response(response_content: str, raw_tool_calls: List[Dict[str, Any]]):
    """
    Process raw tool calls from LLM response and convert them to proper ToolCall objects.
    Now expects raw_tool_calls in OpenAI format with 'function' field.
    
    Args:
        response_content: The content from the LLM response
        raw_tool_calls: Raw tool call dictionaries from the LLM response in OpenAI format
        
    Returns:
        Tuple of (content, processed_tool_calls)
    """
    # Convert raw tool call dictionaries to ToolCall objects (OpenAI format)
    processed_tool_calls = []
    for tool_call_data in raw_tool_calls:
        # Check if this is already in OpenAI format with 'function' key
        if "function" in tool_call_data:
            # Already in OpenAI format - check if arguments are JSON string or dict
            function_data = tool_call_data.get("function", {})
            args = function_data.get("arguments", "{}")
            
            # Normalize to ensure arguments are JSON strings as per OpenAI spec
            if isinstance(args, dict):
                # Convert dict to JSON string to match OpenAI format
                normalized_function = {
                    "name": function_data.get("name", ""),
                    "arguments": json.dumps(args)
                }
            else:
                # Already a string, keep as-is
                normalized_function = function_data.copy()
            
            tool_call = ToolCall(
                id=tool_call_data.get("id", ""),
                function=normalized_function,
                type=tool_call_data.get("type", "function")
            )
        else:
            # Not in OpenAI format, create using compatibility method
            args = tool_call_data.get("arguments", {})
            # Convert to JSON string if it's a dict to match OpenAI format
            if isinstance(args, dict):
                args = json.dumps(args)
            
            tool_call = ToolCall(
                id=tool_call_data.get("id", ""),
                function={
                    "name": tool_call_data.get("name", ""),
                    "arguments": args
                }
            )
        processed_tool_calls.append(tool_call)
    
    return response_content, processed_tool_calls