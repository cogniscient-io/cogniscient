"""
Content Converter for GCS Kernel LLM Provider Backend.

This module implements content conversion following Qwen Code's OpenAIContentConverter patterns.
"""

from typing import Dict, Any, List
from gcs_kernel.models import ToolResult
from services.llm_provider.base_converter import BaseConverter


class OpenAIConverter(BaseConverter):
    """
    OpenAI-compatible converter for transforming data between kernel format and OpenAI provider format.
    This converter minimizes transformations since kernel formats are aligned with OpenAI format.
    """
    
    def __init__(self, model: str):
        super().__init__(model)

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
        Since we're standardizing on OpenAI format, this is now a minimal transformation.
        
        Args:
            provider_response: Response from LLM provider (as dictionary) in OpenAI format
            
        Returns:
            Response in kernel format (which is now OpenAI-compatible)
        """
        # Extract content and potential tool calls from provider response (OpenAI format)
        choices = provider_response.get("choices", [])
        if not choices:
            return {"content": "", "tool_calls": []}
        
        choice = choices[0]
        message = choice.get("message", {})
        
        # Return in OpenAI-compatible format with minimal transformation
        result = {
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", [])  # Already in OpenAI format
        }
        
        return result

    def convert_kernel_tools_to_provider(self, kernel_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert kernel tool format to provider tool format.
        Since kernel tools are already in OpenAI format, this is now essentially a passthrough.
        
        Args:
            kernel_tools: Tools in kernel format (now in OpenAI format)
            
        Returns:
            Tools in provider format (same as input - already OpenAI format)
        """
        # The kernel tools should already be in OpenAI format, so just return them as-is
        # If they're ToolDefinition objects, convert them to dictionaries in OpenAI format
        from gcs_kernel.models import ToolDefinition
        
        provider_tools = []
        for tool in kernel_tools:
            if isinstance(tool, ToolDefinition):
                # ToolDefinition is already in OpenAI format, just extract the dict representation
                provider_tools.append({
                    "type": tool.type,
                    "function": tool.function
                })
            elif isinstance(tool, dict):
                # For backward compatibility with dict format, return as-is if already in OpenAI format
                if "function" in tool and "type" in tool:
                    # Already in full OpenAI format
                    provider_tools.append(tool)
                elif "name" in tool and "parameters" in tool:
                    # Old kernel format, convert to OpenAI format
                    provider_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool["parameters"]
                        }
                    })
                else:
                    # Unknown format, return as-is with a default
                    provider_tools.append(tool)
            else:
                # For any other format, return as-is
                provider_tools.append(tool)
        
        return provider_tools

    def convert_kernel_tool_result_to_provider(self, tool_result: ToolResult) -> Dict[str, Any]:
        """
        Convert kernel ToolResult to provider format for continuing conversation.
        This maps kernel execution result fields to the OpenAI message format.
        OpenAI expects a message with role='tool', content, and tool_call_id.
        
        Args:
            tool_result: Tool result in kernel format (execution result)
            
        Returns:
            Tool result in OpenAI message format for conversation history
        """
        return {
            "role": "tool",
            "content": tool_result.return_display,
            "tool_call_id": tool_result.tool_name  # OpenAI format uses tool_call_id
        }

# Maintain backward compatibility
ContentConverter = OpenAIConverter