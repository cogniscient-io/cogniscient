"""
Enhanced validation for tool calls in the GCS Kernel.

This module provides validation for tool names and parameters before execution.
"""
from typing import Dict, Any, List
import json

def validate_tool_call(tool_name: str, parameters: Dict[str, Any], available_tools: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a tool call against the available tools registry.
    
    Args:
        tool_name: The name of the tool to call
        parameters: The parameters to pass to the tool
        available_tools: Dictionary of available tools from the registry
        
    Returns:
        Dictionary with validation result containing:
        - 'valid': Boolean indicating if the call is valid
        - 'error': Error message if not valid
        - 'suggested_tool': Suggested tool name if there's a close match
    """
    # Check if the tool exists in the registry
    if tool_name not in available_tools:
        # Check for potential typos using simple string similarity
        suggested_tool = _find_closest_tool_name(tool_name, available_tools.keys())
        if suggested_tool:
            return {
                'valid': False,
                'error': f"Tool '{tool_name}' not found. Did you mean '{suggested_tool}'?",
                'suggested_tool': suggested_tool
            }
        else:
            return {
                'valid': False,
                'error': f"Tool '{tool_name}' not found in the registry.",
                'suggested_tool': None
            }
    
    # Get the tool definition
    tool_def = available_tools[tool_name]
    schema = tool_def.get('parameters', {})
    
    # Validate required parameters
    required_params = schema.get('required', [])
    for param in required_params:
        if param not in parameters:
            return {
                'valid': False,
                'error': f"Missing required parameter '{param}' for tool '{tool_name}'",
                'suggested_tool': None
            }
    
    # Validate parameter types
    properties = schema.get('properties', {})
    for param_name, param_value in parameters.items():
        if param_name in properties:
            expected_type = properties[param_name].get('type')
            if expected_type == 'string' and not isinstance(param_value, str):
                return {
                    'valid': False,
                    'error': f"Parameter '{param_name}' for tool '{tool_name}' should be a string, got {type(param_value).__name__}",
                    'suggested_tool': None
                }
            elif expected_type == 'integer' and not isinstance(param_value, int):
                return {
                    'valid': False,
                    'error': f"Parameter '{param_name}' for tool '{tool_name}' should be an integer, got {type(param_value).__name__}",
                    'suggested_tool': None
                }
            elif expected_type == 'number' and not isinstance(param_value, (int, float)):
                return {
                    'valid': False,
                    'error': f"Parameter '{param_name}' for tool '{tool_name}' should be a number, got {type(param_value).__name__}",
                    'suggested_tool': None
                }
            elif expected_type == 'boolean' and not isinstance(param_value, bool):
                return {
                    'valid': False,
                    'error': f"Parameter '{param_name}' for tool '{tool_name}' should be a boolean, got {type(param_value).__name__}",
                    'suggested_tool': None
                }
    
    # If all validations pass
    return {
        'valid': True,
        'error': None,
        'suggested_tool': None
    }


def _find_closest_tool_name(tool_name: str, available_tool_names: List[str], threshold: float = 0.6) -> str:
    """
    Find the closest matching tool name using a simple similarity algorithm.
    
    Args:
        tool_name: The tool name to match
        available_tool_names: List of available tool names
        threshold: Minimum similarity ratio to consider a match (0.0 to 1.0)
        
    Returns:
        The closest matching tool name or None if no match found
    """
    if not available_tool_names:
        return None

    def similarity(s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings"""
        # Simple character-based similarity
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        common_chars = sum((min(s1_lower.count(c), s2_lower.count(c)) for c in set(s1_lower)))
        total_chars = max(len(s1_lower), len(s2_lower))
        
        if total_chars == 0:
            return 1.0  # Both strings are empty
        return common_chars / total_chars

    best_match = None
    best_ratio = 0.0

    for name in available_tool_names:
        ratio = similarity(tool_name, name)
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = name

    return best_match