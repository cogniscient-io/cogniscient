"""
Base Converter for GCS Kernel LLM Provider Backend.

This module defines the base converter with common functionality
using OpenAI API standards as the default format.
"""

import logging
from typing import Dict, Any, List
from gcs_kernel.models import ToolResult
from services.config import settings

# Set up logging
logger = logging.getLogger(__name__)


class BaseConverter:
    """
    Base class for content converters that transform data
    between kernel format and LLM provider format,
    using OpenAI API as the standard.
    """

    def __init__(self, model: str):
        self.model = model

    def convert_kernel_request_to_provider(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert kernel request to provider format.
        Optimized for OpenAI-native requests that are already mostly in the correct format.
        
        Args:
            request: Request in kernel format
            
        Returns:
            Request in provider format
        """
        # Start with the incoming request - it's likely already mostly in OpenAI format
        provider_request = request.copy()
        
        # Ensure required fields are set
        provider_request.setdefault("model", self.model)
        provider_request.setdefault("temperature", settings.llm_temperature)
        provider_request.setdefault("max_tokens", settings.llm_max_tokens)
        
        # Handle legacy format conversion if needed
        if "prompt" in request and "messages" not in request:
            # Convert legacy prompt format to messages
            prompt = request.get("prompt", "")
            messages = [{"role": "user", "content": prompt}]
            
            # Add system message if present
            if "system_prompt" in request:
                messages.insert(0, {"role": "system", "content": request["system_prompt"]})
            
            provider_request["messages"] = messages
            
            # Remove legacy fields
            provider_request.pop("prompt", None)
            provider_request.pop("system_prompt", None)
        
        # Convert tools if present
        if "tools" in request:
            provider_request["tools"] = self.convert_kernel_tools_to_provider(request["tools"])
        
        logger.debug(f"BaseConverter convert_kernel_request_to_provider - provider_request: {provider_request}")
        
        return provider_request

    def convert_provider_response_to_kernel(self, provider_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert provider response to kernel format.
        Uses passthrough for OpenAI-compatible responses.
        
        Args:
            provider_response: Response from LLM provider

        Returns:
            Response in kernel format
        """
        # Extract content and tool calls from provider response
        choices = provider_response.get("choices", [])
        if not choices:
            return {"content": "", "tool_calls": []}
        
        choice = choices[0]
        message = choice.get("message", {})
        
        return {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", [])
        }

    def convert_kernel_tools_to_provider(self, kernel_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert kernel tools to provider format.
        Passthrough for OpenAI-compatible tools.
        
        Args:
            kernel_tools: Tools in kernel format

        Returns:
            Tools in provider format
        """
        # The kernel tools should already be in OpenAI format, convert if needed
        from gcs_kernel.models import ToolDefinition
        
        provider_tools = []
        for tool in kernel_tools:
            if isinstance(tool, ToolDefinition):
                # Convert ToolDefinition to OpenAI format
                provider_tools.append({
                    "type": tool.type,
                    "function": tool.function
                })
            elif isinstance(tool, dict):
                # Handle dict format conversion if needed
                if "function" in tool and "type" in tool:
                    # Already in OpenAI format
                    provider_tools.append(tool)
                elif "name" in tool and "parameters" in tool:
                    # Convert legacy format
                    provider_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool["parameters"]
                        }
                    })
                else:
                    # Unknown format, return as-is
                    provider_tools.append(tool)
            else:
                # For any other format, return as-is
                provider_tools.append(tool)
        
        return provider_tools

    def convert_kernel_tool_result_to_provider(self, tool_result: ToolResult) -> Dict[str, Any]:
        """
        Convert kernel ToolResult to provider format.
        Uses OpenAI format.
        
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