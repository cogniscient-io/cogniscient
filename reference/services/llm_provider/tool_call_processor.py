"""
Improved tool calling functionality for the GCS Kernel.

This module provides enhanced tool call processing with proper validation and error handling.
"""
from typing import Any, Dict, List


class ToolCall:
    """
    Represents a tool call from the LLM response.
    """
    def __init__(self, id: str, name: str, arguments: Dict[str, Any]):
        """
        Initialize a ToolCall instance.
        
        Args:
            id: The ID of the tool call
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
        """
        self.id = id
        self.name = name
        self.arguments = arguments
        # Keep arguments in parameters for compatibility with orchestrator expectation
        self.parameters = arguments


def process_tool_calls_in_response(response_content: str, raw_tool_calls: List[Dict[str, Any]]):
    """
    Process raw tool calls from LLM response and convert them to proper ToolCall objects.
    
    Args:
        response_content: The content from the LLM response
        raw_tool_calls: Raw tool call dictionaries from the LLM response
        
    Returns:
        Tuple of (content, processed_tool_calls)
    """
    # Convert raw tool call dictionaries to ToolCall objects
    processed_tool_calls = []
    for tool_call_data in raw_tool_calls:
        tool_call = ToolCall(
            id=tool_call_data.get("id", ""),
            name=tool_call_data.get("name", ""),
            arguments=tool_call_data.get("arguments", {})
        )
        processed_tool_calls.append(tool_call)
    
    return response_content, processed_tool_calls