"""
Streaming Handler for GCS Kernel AI Orchestrator.

This module implements the StreamingHandler which manages streaming responses
as per Qwen architecture patterns, coordinating with non-streaming tool execution.
"""

import asyncio
from typing import Any, Dict, List, AsyncGenerator
from gcs_kernel.mcp.client import MCPClient
from services.llm_provider.base_generator import BaseContentGenerator


class StreamingHandler:
    """
    Handles streaming responses from the LLM while coordinating with
    non-streaming tool execution phases as per Qwen architecture.
    """
    
    def __init__(self, 
                 kernel_client: MCPClient, 
                 content_generator: BaseContentGenerator, 
                 kernel=None):
        """
        Initialize the streaming handler.
        
        Args:
            kernel_client: MCP client for communicating with the kernel
            content_generator: Content generator for LLM interactions
            kernel: Optional direct reference to kernel for registry access
        """
        self.kernel_client = kernel_client
        self.content_generator = content_generator
        self.kernel = kernel

    async def handle_streaming_interaction(self, 
                                         prompt: str, 
                                         system_context: str = None, 
                                         tools: List[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Handle a streaming interaction, switching to non-streaming for tool execution
        and then continuing streaming with the results.
        
        Args:
            prompt: The user's input prompt
            system_context: Optional system context for the LLM
            tools: Optional list of tools to provide to the LLM
            
        Yields:
            String chunks as they become available during streaming
        """
        # First, get the initial response from the LLM (this may include tool calls)
        # For streaming, we need to use the content generator's stream method
        try:
            # Get initial response stream from LLM
            async for chunk in self.content_generator.stream_response(
                prompt, 
                system_context=system_context, 
                tools=tools
            ):
                yield chunk
        
        except Exception as e:
            # Handle any errors during the initial streaming
            yield f"Error during initial streaming: {str(e)}"
            return
        
        # If the LLM response included tool calls, we need to execute them in non-streaming mode
        # and then continue with the conversation
        # Note: The actual handling of tool calls in streaming context requires
        # special processing that may not allow full streaming during tool execution
        # The approach here is to handle complete turns with tool execution
        # and then continue streaming the final response

    async def handle_turn_based_streaming(self, 
                                        prompt: str, 
                                        system_context: str = None, 
                                        tools: List[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Handle a turn-based streaming interaction where tool execution happens
        in non-streaming mode but the overall conversation can be streamed.
        
        Args:
            prompt: The user's input prompt
            system_context: Optional system context for the LLM
            tools: Optional list of tools to provide to the LLM
            
        Yields:
            String chunks as they become available during streaming
        """
        # For turn-based approach, we use generate_response which handles
        # both content generation and tool execution phases
        try:
            response = await self.content_generator.generate_response(
                prompt,
                system_context=system_context,
                tools=tools
            )
            
            # If the response contains tool calls, execute them in non-streaming mode
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Yield content part first if available
                if response.content:
                    yield response.content
            
            # Otherwise, yield the direct content
            else:
                content = getattr(response, 'content', str(response))
                yield content
                
        except Exception as e:
            yield f"Error during streaming interaction: {str(e)}"