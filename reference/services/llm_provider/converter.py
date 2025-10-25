"""
Content Converter for GCS Kernel LLM Provider Backend.

This module implements content conversion following Qwen Code's OpenAIContentConverter patterns.
"""

from typing import Dict, Any, List
from gcs_kernel.models import ToolResult
import json


class ContentConverter:
    """
    Converter for transforming data between kernel format and LLM provider format
    following Qwen Code's OpenAIContentConverter implementation patterns.
    """
    
    def __init__(self, model: str):
        self.model = model

    def convert_kernel_request_to_provider(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert kernel request format to provider-specific format.
        
        Args:
            request: Request in kernel format
            
        Returns:
            Request in provider-specific format
        """
        # Check if the request already contains a messages array (e.g., for continuing conversation)
        if "messages" in request:
            # Use the existing messages array
            messages = request["messages"]
        else:
            # Extract prompt from request and create a user message
            prompt = request.get("prompt", "")
            
            # Convert to provider message format (e.g., OpenAI format)
            messages = [{"role": "user", "content": prompt}]
        
        # Add system message if present
        if "system_prompt" in request:
            messages.insert(0, {"role": "system", "content": request["system_prompt"]})
        
        # Prepare the request payload
        provider_request = {
            "model": request.get("model", self.model),
            "messages": messages,
            "temperature": request.get("temperature", 0.7),
            "max_tokens": request.get("max_tokens", 1000),
        }
        
        # Add tools if present in request
        if "tools" in request:
            provider_request["tools"] = self.convert_kernel_tools_to_provider(request["tools"])
        
        return provider_request

    def convert_provider_response_to_kernel(self, provider_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert provider response format to kernel format.
        
        Args:
            provider_response: Response from LLM provider (as dictionary)
            
        Returns:
            Response in kernel format
        """
        # Extract content and potential tool calls from provider response
        choices = provider_response.get("choices", [])
        if not choices:
            return {"content": "", "tool_calls": []}
        
        choice = choices[0]
        message = choice.get("message", {})
        
        result = {
            "content": message.get("content", ""),
            "tool_calls": []
        }
        
        # Process tool calls if present
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                # Get the tool name
                tool_name = tool_call.get("function", {}).get("name")
                
                # Only include tool calls with valid names (non-empty)
                if tool_name and tool_name.strip():
                    # For the kernel, arguments should be parsed from JSON string to object
                    # but in the response back to kernel, keep as string for proper format
                    arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                    arguments_obj = arguments_str
                    try:
                        # Try to parse if it's a JSON string, otherwise keep as is
                        if isinstance(arguments_str, str):
                            arguments_obj = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        # If parsing fails, keep the original value
                        pass
                    
                    result["tool_calls"].append({
                        "id": tool_call.get("id"),
                        "name": tool_name,
                        "arguments": arguments_obj
                    })
        
        return result

    def convert_kernel_tools_to_provider(self, kernel_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert kernel tool format to provider tool format.
        
        Args:
            kernel_tools: Tools in kernel format
            
        Returns:
            Tools in provider format
        """
        provider_tools = []
        for tool in kernel_tools:
            provider_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("parameters", {})
                }
            }
            provider_tools.append(provider_tool)
        
        return provider_tools

    def convert_kernel_tool_result_to_provider(self, tool_result: ToolResult) -> Dict[str, Any]:
        """
        Convert kernel ToolResult to provider format for continuing conversation.
        
        Args:
            tool_result: Tool result in kernel format
            
        Returns:
            Tool result in provider format
        """
        return {
            "role": "tool",
            "content": tool_result.return_display,
            "tool_call_id": tool_result.tool_name
        }