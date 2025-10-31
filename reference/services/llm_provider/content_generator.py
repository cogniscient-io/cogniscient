"""
LLM Content Generator for GCS Kernel LLM Provider Backend.

This module implements the LLM content generator that extends the base generator
and follows Qwen Code patterns for content generation, using Pydantic Settings.
It supports multiple LLM providers through the provider factory.
"""

import logging
from typing import Any, Dict, AsyncIterator
from gcs_kernel.models import ToolResult
from services.config import settings
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.provider_factory import ProviderFactory

# Set up logging
logger = logging.getLogger(__name__)


class LLMContentGenerator(BaseContentGenerator):
    """
    LLM-specific content generator that extends the base generator and follows 
    Qwen Code patterns for content generation, using Pydantic Settings.
    Supports multiple LLM providers through the provider factory.
    """
    
    def __init__(self):
        # Initialize provider components
        # The provider factory will handle all configuration internally from settings
        self.provider_factory = ProviderFactory()
        
        # Let the provider factory create the provider with configuration from settings
        self.provider = self.provider_factory.create_provider_from_settings()
        self.pipeline = ContentGenerationPipeline(self.provider)
        
        # Content generator no longer needs to store or validate configuration
        # The provider handles all configuration concerns internally
        
        # Initialize kernel_client as None, will be set by orchestrator
        self.kernel_client = None
        self.kernel = None  # Will be set by orchestrator
    
    async def generate_response(self, prompt: str, system_context: str = None, prompt_id: str = None) -> Any:
        """
        Generate a response to the given prompt with potential tool calls.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            prompt: The input prompt (deprecated - conversation history should be used instead)
            system_context: Optional system context (deprecated - conversation history should be used instead)
            prompt_id: Optional identifier for the prompt which contains tool inclusion configuration
            
        Returns:
            The generated response with potential tool calls
        """
        # TODO: Remove this method's dependency on prompt and system_context parameters.
        # For now, maintain compatibility by creating messages from parameters,
        # but eventually this method should work with conversation history only.
        
        # Prepare the request with essential content only
        # The provider will handle all configuration parameters internally
        
        # Create messages in OpenAI format
        messages = [{"role": "user", "content": prompt}]
        if system_context:
            messages.insert(0, {"role": "system", "content": system_context})
        
        request = {
            "messages": messages
        }
        
        # Get tools if prompt_id is provided
        if prompt_id:
            from gcs_kernel.models import ToolInclusionConfig
            # In a real implementation, we would fetch the tools based on the prompt_id
            # For now, this is a placeholder
            tools = await self._get_tools_for_prompt(prompt_id)
            if tools:
                request["tools"] = tools
        
        # Generate content using the pipeline with the same prompt_id for provider tracking
        response = await self.generate_content(request, user_prompt_id=prompt_id)
        
        # Use the shared helper method to format the response consistently
        return self._format_response(response)
    
    async def generate_response_from_conversation(self, conversation_history: list, prompt_id: str = None) -> Any:
        """
        Generate a response based on conversation history with potential tool calls.
        This is the preferred method that works with proper conversation history.
        
        Args:
            conversation_history: Full conversation history including system, user, assistant, and tool messages
            prompt_id: Optional identifier for the prompt which contains tool inclusion configuration
            
        Returns:
            The generated response with potential tool calls
        """
        # Prepare the request with essential content only
        # The provider will handle all configuration parameters internally
        
        # Use conversation history directly
        request = {
            "messages": conversation_history
        }
        
        # Get tools if prompt_id is provided
        if prompt_id:
            # In a real implementation, we would fetch the tools based on the prompt_id
            # For now, this is a placeholder
            tools = await self._get_tools_for_prompt(prompt_id)
            if tools:
                request["tools"] = tools
        
        # Generate content using the pipeline with the same prompt_id for provider tracking
        response = await self.generate_content(request, user_prompt_id=prompt_id)
        
        # Use the shared helper method to format the response consistently
        return self._format_response(response)
    
    async def process_tool_result(self, tool_result: Any, conversation_history: list = None, prompt_id: str = None) -> Any:
        """
        Process a tool result and continue the conversation.
        
        Args:
            tool_result: The result from a tool execution
            conversation_history: The conversation history to maintain context
            prompt_id: Optional identifier for the prompt which contains tool inclusion configuration
            
        Returns:
            The updated response after processing the tool result
        """
        # Prepare the request with essential content only
        # The provider will handle all configuration parameters internally
        
        # Use the conversation history directly if provided, otherwise create minimal messages
        if conversation_history:
            messages = conversation_history
        else:
            # Fallback: create minimal message with the tool result
            messages = [{"role": "user", "content": f"Process this tool result: {tool_result}"}]
        
        request = {
            "messages": messages
        }
        
        # Get tools if prompt_id is provided
        if prompt_id:
            # In a real implementation, we would fetch the tools based on the prompt_id
            # For now, this is a placeholder
            tools = await self._get_tools_for_prompt(prompt_id)
            if tools:
                request["tools"] = tools
        
        # Generate content using the pipeline with the same prompt_id for provider tracking
        response = await self.generate_content(request, user_prompt_id=prompt_id)
        
        # Use the shared helper method to format the response consistently
        return self._format_response(response)
    
    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Stream a response to the given prompt.
        This method handles content streaming for UX purposes and also
        processes the complete response with potential tool calls after streaming completes.
        
        Args:
            prompt: The input prompt
            
        Yields:
            Partial response strings as they become available
        """
        # Prepare the request with essential content only for streaming
        # The provider will handle all configuration parameters internally
        
        # Create messages in OpenAI format
        messages = [{"role": "user", "content": prompt}]
        
        request = {
            "messages": messages,
            "stream": True
        }
        
        # Execute streaming content generation through the pipeline
        async for chunk in self.pipeline.execute_stream(request, user_prompt_id=f"stream_{id(prompt)}"):
            yield chunk
        
        # After streaming completes, get the complete response from the pipeline
        complete_response = self.pipeline.get_last_streaming_response()
        
        # If the complete response contains tool calls, we could process them here
        # For now, this ensures the complete response is processed through our standard flow
        if complete_response:
            # Process the complete response through the standard flow to handle potential tool calls
            formatted_response = self._format_response(complete_response)
            
            # NOTE: Since this is an async generator, we can't directly return the complete response.
            # The complete response with tool calls would need to be handled by the caller
            # (e.g., ai orchestrator) through a separate mechanism.
            # The primary purpose of this is to ensure the complete response gets processed
            # through _format_response and tool call processor even after streaming.
    
    async def generate_content(self, request: Dict[str, Any], user_prompt_id: str) -> Any:
        """
        Generate content using the pipeline.
        
        Args:
            request: The content generation request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            The content generation response
        """
        return await self.pipeline.execute(request, user_prompt_id)
    
    def _format_response(self, response: Any) -> Any:
        """
        Format the response consistently.
        Since the response is now in OpenAI format, use the dedicated tool call processor
        to convert tool_calls from dict format to objects with expected attributes 
        for compatibility with turn manager.
        
        Args:
            response: The raw response from the pipeline (in OpenAI format)
            
        Returns:
            The formatted response
        """
        from .tool_call_processor import process_tool_calls_in_response, ToolCall
        
        class ResponseObject:
            def __init__(self, content="", tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls or []
        
        # If the response has content and tool_calls attributes, return an object with these attributes
        if isinstance(response, dict):
            content = response.get("content", "")
            raw_tool_calls = response.get("tool_calls", [])
            
            logger.debug(f"ContentGenerator _format_response - content: '{content}', raw_tool_calls: {raw_tool_calls}")
            
            # Use the dedicated tool call processor to handle conversion properly
            _, processed_tool_calls = process_tool_calls_in_response(content, raw_tool_calls)
            
            return ResponseObject(
                content=content,
                tool_calls=processed_tool_calls
            )
        else:
            # Handle other response formats
            content = getattr(response, 'content', '') or str(response)
            raw_tool_calls = getattr(response, 'tool_calls', [])
            
            logger.debug(f"ContentGenerator _format_response - non-dict response - content: '{content}', raw_tool_calls: {raw_tool_calls}")
            
            # Use the dedicated tool call processor to handle conversion properly
            _, processed_tool_calls = process_tool_calls_in_response(content, raw_tool_calls)
            
            return ResponseObject(
                content=content,
                tool_calls=processed_tool_calls
            )
    
    async def _get_tools_for_prompt(self, prompt_id: str) -> list:
        """
        Get tools for a specific prompt based on the tool inclusion policy.
        
        Args:
            prompt_id: The ID of the prompt
            
        Returns:
            List of tools in the format expected by the LLM
        """
        # Get the kernel instance if available - this assumes content generator has access to kernel
        from gcs_kernel.models import ToolInclusionPolicy
        from gcs_kernel.mcp.client import MCPClient
        
        # First, check if we have access to the kernel to get the prompt config
        if hasattr(self, 'kernel') and self.kernel:
            # Get the tool inclusion config from the kernel
            prompt_config = self.kernel.get_prompt_config(prompt_id)
            
            if prompt_config:
                policy = prompt_config.policy
                if policy == ToolInclusionPolicy.ALL_AVAILABLE:
                    # Get all available tools from the kernel registry
                    tools = self.kernel.registry.get_all_tools()
                    # Convert tool objects to dictionary format expected by LLM
                    llm_tools = []
                    for tool_name, tool_obj in tools.items():
                        llm_tool = {
                            "name": getattr(tool_obj, 'name', tool_name),
                            "description": getattr(tool_obj, 'description', ''),
                            "parameters": getattr(tool_obj, 'parameters', {})  # Using OpenAI-compatible format
                        }
                        llm_tools.append(llm_tool)
                    return llm_tools
                elif policy == ToolInclusionPolicy.CUSTOM:
                    # Return the custom tools specified in the config
                    return prompt_config.custom_tools or []
                elif policy == ToolInclusionPolicy.CONTEXTUAL_SUBSET:
                    # This would require more complex logic to determine which tools to include
                    # based on the context, but for now return all available
                    tools = self.kernel.registry.get_all_tools()
                    # Convert tool objects to dictionary format expected by LLM
                    llm_tools = []
                    for tool_name, tool_obj in tools.items():
                        llm_tool = {
                            "name": getattr(tool_obj, 'name', tool_name),
                            "description": getattr(tool_obj, 'description', ''),
                            "parameters": getattr(tool_obj, 'parameters', {})  # Using OpenAI-compatible format
                        }
                        llm_tools.append(llm_tool)
                    return llm_tools
                elif policy == ToolInclusionPolicy.NONE:
                    # Return empty list as no tools should be available
                    return []
        
        # If we don't have access to the kernel or prompt config, we need to fall back to the MCP client
        # to get available tools, similar to the original _get_available_tools implementation
        if hasattr(self, 'provider') and hasattr(self.provider, 'provider_factory'):
            # Try to get tools through the provider
            try:
                # Use the kernel client from the provider if available
                if hasattr(self, 'kernel_client'):
                    tools_response = await self.kernel_client.list_tools()
                    
                    # Handle different response formats (same logic as the original implementation)
                    if isinstance(tools_response, dict):
                        if "tools" in tools_response:  # MCP response with tools array
                            tools_list = tools_response["tools"]
                            # Convert list of tools to dict format
                            tools = {}
                            for tool_info in tools_list:
                                name = tool_info.get("name", "unknown")
                                tools[name] = tool_info
                        else:  # MCP response with tools as dict {name: info}
                            tools = tools_response
                    elif isinstance(tools_response, list):  # Direct list of tools
                        tools = {}
                        for tool_info in tools_response:
                            name = tool_info.get("name", "unknown")
                            tools[name] = tool_info
                    else:
                        tools = {}
                
                    # Convert available tools to kernel tool format to pass to LLM
                    kernel_tools = []
                    for tool_name, tool_info in tools.items():
                        kernel_tool = {
                            "name": tool_info.get("name", tool_name),
                            "description": tool_info.get("description", ""),
                            "parameters": tool_info.get("parameters", {})
                        }
                        kernel_tools.append(kernel_tool)
                    
                    return kernel_tools
            except:
                # If we can't get tools from the kernel client, return empty list
                pass
        
        # Default to empty list if no method worked
        return []

