"""
AI Orchestrator Service implementation for the GCS Kernel.

This module implements the AIOrchestratorService which manages AI interactions,
session management, and provider abstraction following Qwen architecture patterns.
The content generator must be provided separately to maintain clean separation of concerns.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult
from services.llm_provider.base_generator import BaseContentGenerator
from .system_context_builder import SystemContextBuilder
from .turn_manager import TurnManager, TurnEvent, TurnEventType
from .tool_executor import ToolExecutor
from .streaming_handler import StreamingHandler


class AIOrchestratorService:
    """
    AI Orchestrator Service that manages AI interactions and conversation session state.
    Requires a content generator that extends BaseContentGenerator to be provided externally.
    """
    
    def __init__(self, kernel_client: MCPClient, content_generator: 'BaseContentGenerator' = None, kernel=None):
        """
        Initialize the AI orchestrator with a kernel client and optional content generator.
        
        Args:
            kernel_client: MCP client for communicating with the kernel server
            content_generator: Optional content generator. If not provided, must be set 
                              before using the orchestrator
            kernel: Optional direct reference to the kernel instance for direct access to registry
        """
        # Accept MCP client to communicate with kernel server
        self.kernel_client = kernel_client
        self.content_generator = content_generator
        self.kernel = kernel  # Direct access to kernel for registry access if provided
        
        # Initialize kernel services (will be set via set_kernel_services)
        self.registry = None
        self.scheduler = None
        
        # Initialize components based on Qwen architecture
        self.turn_manager = TurnManager(kernel_client, content_generator, kernel)
        self.tool_executor = ToolExecutor(kernel_client, kernel)
        self.streaming_handler = StreamingHandler(kernel_client, content_generator, kernel)
        
        # Initialize system context builder for creating system context with prompts
        self.system_context_builder = SystemContextBuilder(kernel_client, kernel)
        
        # Initialize conversation history to maintain context across interactions
        self.conversation_history = []

    def set_kernel_services(self, registry=None, scheduler=None):
        """
        Set direct references to kernel services for streamlined operations.
        
        Args:
            registry: Kernel registry for tool access
            scheduler: Kernel scheduler for tool execution
        """
        self.registry = registry
        self.scheduler = scheduler
        # Update components with direct kernel services
        if self.turn_manager:
            self.turn_manager.registry = registry
            self.turn_manager.scheduler = scheduler
        if self.tool_executor:
            self.tool_executor.registry = registry
            self.tool_executor.scheduler = scheduler
        if self.streaming_handler:
            self.streaming_handler.registry = registry
            self.streaming_handler.scheduler = scheduler

    def set_content_generator(self, provider: 'BaseContentGenerator'):
        """
        Set the content generator for this orchestrator.
        The provider should extend BaseContentGenerator.
        
        Args:
            provider: The content generator to use for AI interactions
        """
        self.content_generator = provider
        # Also update the components
        if self.turn_manager:
            self.turn_manager.content_generator = provider
        if self.streaming_handler:
            self.streaming_handler.content_generator = provider

    async def handle_ai_interaction(self, prompt: str) -> str:
        """
        Handle an AI interaction, managing the transition between streaming and non-streaming
        for tool execution following Qwen architecture patterns.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The AI response string
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Reset conversation history for new interaction
        self.conversation_history = []
        
        # Build system context with available tools
        system_context = await self.system_context_builder.build_system_context()
        available_tools = await self._get_available_tools()
        
        # Process the interaction using turn manager which handles the streaming/non-streaming
        # transition for tool execution
        final_response = ""
        
        # Create an abort signal for the turn
        abort_signal = asyncio.Event()
        
        try:
            async for event in self.turn_manager.run_turn(
                prompt, 
                system_context, 
                available_tools, 
                abort_signal
            ):
                if event.type == TurnEventType.CONTENT:
                    final_response += event.value
                elif event.type == TurnEventType.TOOL_CALL_RESPONSE:
                    # Tool result handled internally by turn manager
                    continue
                elif event.type == TurnEventType.ERROR:
                    final_response += f"\nError: {event.error}"
                elif event.type == TurnEventType.FINISHED:
                    break
        except Exception as e:
            return f"Error during AI interaction: {str(e)}"
        
        return final_response

    async def stream_ai_interaction(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Stream an AI interaction, managing the transition between streaming and non-streaming
        for tool execution following Qwen architecture patterns.
        
        Args:
            prompt: The user's input prompt
            
        Yields:
            Partial response strings as they become available
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Reset conversation history for new interaction
        self.conversation_history = []
        
        # Build system context with available tools
        system_context = await self.system_context_builder.build_system_context()
        available_tools = await self._get_available_tools()
        
        # Create an abort signal for the turn
        abort_signal = asyncio.Event()
        
        try:
            async for event in self.turn_manager.run_turn(
                prompt, 
                system_context, 
                available_tools, 
                abort_signal
            ):
                if event.type == TurnEventType.CONTENT:
                    yield event.value
                elif event.type == TurnEventType.TOOL_CALL_REQUEST:
                    # For streaming, we'll report that a tool call is being processed
                    yield f"\n[Processing tool call: {event.value.get('name', 'unknown')}]\n"
                elif event.type == TurnEventType.TOOL_CALL_RESPONSE:
                    # Tool result handled internally by turn manager
                    yield f"\n[Tool call completed]\n"
                elif event.type == TurnEventType.ERROR:
                    yield f"\nError: {event.value or str(event.error)}\n"
                elif event.type == TurnEventType.FINISHED:
                    break
        except Exception as e:
            yield f"\nError during streaming interaction: {str(e)}\n"

    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get available tools from the system context builder or kernel registry.
        
        Returns:
            List of available tools in the format expected by the LLM
        """
        # Get available tools to provide to the LLM natively
        if self.kernel and hasattr(self.kernel, 'registry'):
            tools = self.kernel.registry.get_all_tools()
            # Convert tool objects to dictionary format
            tools_dict = {}
            for tool_name, tool_obj in tools.items():
                tools_dict[tool_name] = {
                    "name": getattr(tool_obj, 'name', tool_name),
                    "description": getattr(tool_obj, 'description', ''),
                    "parameters": getattr(tool_obj, 'parameters', {}),  # Using OpenAI-compatible format
                    "display_name": getattr(tool_obj, 'display_name', tool_name)
                }
            tools = tools_dict
        else:
            # Fallback to MCP client if kernel isn't available
            tools_response = await self.kernel_client.list_tools()
            
            # Handle different response formats
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



    async def reset_conversation(self):
        """
        Reset the conversation history.
        """
        self.conversation_history = []

    def get_conversation_history(self) -> list:
        """
        Get the current conversation history.
        
        Returns:
            List of conversation messages
        """
        return self.conversation_history

    def add_message_to_history(self, role: str, content: str, **kwargs):
        """
        Add a properly formatted message to the conversation history.
        
        Args:
            role: The role of the message ('user', 'assistant', 'tool')
            content: The content of the message
            **kwargs: Additional message properties (like tool_call_id)
        """
        message = {
            "role": role,
            "content": content
        }
        message.update(kwargs)  # Add any additional properties like tool_call_id
        self.conversation_history.append(message)