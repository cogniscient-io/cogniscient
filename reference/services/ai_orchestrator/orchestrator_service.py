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
            # Update kernel reference if available
            if self.kernel:
                self.turn_manager.kernel = self.kernel
        if self.streaming_handler:
            self.streaming_handler.content_generator = provider
            # Update kernel reference if available
            if self.kernel:
                self.streaming_handler.kernel = self.kernel
        
        # Also update kernel and kernel client references on the provider directly if available
        if hasattr(provider, 'kernel') and self.kernel:
            provider.kernel = self.kernel
        if hasattr(provider, 'kernel_client') and self.kernel_client:
            provider.kernel_client = self.kernel_client

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
        # Add system context to conversation history
        system_context = await self.system_context_builder.build_system_context()
        
        # Determine tool inclusion policy for this prompt and register it
        from gcs_kernel.models import ToolInclusionPolicy
        prompt_config = self._get_tool_inclusion_policy_for_prompt(prompt)
        prompt_id = prompt_config.prompt_id
        
        # Register the prompt configuration with the kernel
        if self.kernel:
            self.kernel.register_prompt_config(prompt_id, prompt_config)
        
        # Ensure the content generator has access to the kernel and kernel client
        if hasattr(self.content_generator, 'kernel'):
            self.content_generator.kernel = self.kernel
        if hasattr(self.content_generator, 'kernel_client'):
            self.content_generator.kernel_client = self.kernel_client
        
        # Initialize conversation with system context
        self.conversation_history = [{"role": "system", "content": system_context}]
        
        # Process the interaction using turn manager which handles the streaming/non-streaming
        # transition for tool execution
        final_response = ""
        
        # Create an abort signal for the turn
        abort_signal = asyncio.Event()
        
        try:
            async for event in self.turn_manager.run_turn(
                prompt, 
                prompt_id, 
                abort_signal,
                conversation_history_ref=self.conversation_history
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
        
        # No need to synchronize since turn manager uses direct reference
        # self.conversation_history already contains the updated history
        
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
        
        # Build system context
        system_context = await self.system_context_builder.build_system_context()
        
        # Determine tool inclusion policy for this prompt and register it
        prompt_config = self._get_tool_inclusion_policy_for_prompt(prompt)
        prompt_id = prompt_config.prompt_id
        
        # Register the prompt configuration with the kernel
        if self.kernel:
            self.kernel.register_prompt_config(prompt_id, prompt_config)
        
        # Ensure the content generator has access to the kernel and kernel client
        if hasattr(self.content_generator, 'kernel'):
            self.content_generator.kernel = self.kernel
        if hasattr(self.content_generator, 'kernel_client'):
            self.content_generator.kernel_client = self.kernel_client
        
        # Initialize conversation with system context
        self.conversation_history = [{"role": "system", "content": system_context}]
        
        # Create an abort signal for the turn
        abort_signal = asyncio.Event()
        
        try:
            async for event in self.turn_manager.run_turn(
                prompt, 
                prompt_id, 
                abort_signal,
                conversation_history_ref=self.conversation_history
            ):
                if event.type == TurnEventType.CONTENT:
                    yield event.value
                elif event.type == TurnEventType.TOOL_CALL_REQUEST:
                    # Show more specific information about the command being executed
                    tool_name = event.value.get('name', 'unknown')
                    tool_args = event.value.get('arguments', {})
                    command = tool_args.get('command', 'unknown')
                    yield f"\n[{tool_name}: {command}]\n"
                elif event.type == TurnEventType.TOOL_CALL_RESPONSE:
                    # Remove the "completed" message as requested for cleaner UX
                    # The result will be shown naturally in the content response
                    continue
                elif event.type == TurnEventType.ERROR:
                    yield f"\nError: {event.value or str(event.error)}\n"
                elif event.type == TurnEventType.FINISHED:
                    break
        except Exception as e:
            yield f"\nError during streaming interaction: {str(e)}\n"
        
        # No need to synchronize since turn manager uses direct reference
        # self.conversation_history already contains the updated history

    def _get_tool_inclusion_policy_for_prompt(self, prompt: str) -> 'ToolInclusionConfig':
        """
        Determine the appropriate tool inclusion policy for a given prompt.
        
        Args:
            prompt: The input prompt that determines the policy
            
        Returns:
            A ToolInclusionConfig object with the appropriate policy
        """
        from gcs_kernel.models import ToolInclusionPolicy, ToolInclusionConfig
        import uuid
        
        # Create a unique prompt ID
        prompt_id = f"prompt_{str(uuid.uuid4())}"
        
        # Simple heuristic approach - you can make this more sophisticated
        # For now, we'll default to ALL_AVAILABLE for most prompts
        # In a more advanced system, this would analyze the prompt content
        policy = ToolInclusionPolicy.ALL_AVAILABLE
        
        # Example of more sophisticated policy determination:
        # if any(keyword in prompt.lower() for keyword in ["no tools", "without tools", "no function", "no functions"]):
        #     policy = ToolInclusionPolicy.NONE
        # elif "use specific tools" in prompt.lower():
        #     # Could return a custom set of tools here
        #     policy = ToolInclusionPolicy.CUSTOM
        # elif "contextual tools" in prompt.lower():
        #     policy = ToolInclusionPolicy.CONTEXTUAL_SUBSET
        
        return ToolInclusionConfig(
            prompt_id=prompt_id,
            policy=policy
        )
    
    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get available tools from the system context builder or kernel registry.
        This method is now primarily kept for backward compatibility and testing.
        
        Returns:
            List of available tools in the format expected by the LLM
        """
        # Get available tools to provide to the LLM natively
        if self.kernel and hasattr(self.kernel, 'registry'):
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