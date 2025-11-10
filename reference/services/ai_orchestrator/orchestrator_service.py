"""
AI Orchestrator Service implementation for the GCS Kernel.

This module implements the AIOrchestratorService which manages AI interactions,
session management, and provider abstraction following Qwen architecture patterns.
The content generator must be provided separately to maintain clean separation of concerns.
"""

import uuid
from typing import Any, Dict, List, AsyncGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import PromptObject, ToolInclusionConfig
from services.llm_provider.base_generator import BaseContentGenerator
from .system_context_builder import SystemContextBuilder
from .turn_manager import TurnManager, TurnEventType


class AIOrchestratorService:
    """
    AI Orchestrator Service that manages AI interactions and conversation session state.
    Requires a content generator that extends BaseContentGenerator to be provided externally.
    """
    
    def __init__(self, mcp_client: MCPClient, content_generator: 'BaseContentGenerator' = None, kernel=None):
        """
        Initialize the AI orchestrator with a kernel client and optional content generator.
        
        Args:
            mcp_client: MCP client for communicating with the kernel server
            content_generator: Optional content generator. If not provided, must be set 
                              before using the orchestrator
            kernel: Optional direct reference to the kernel instance for direct access to registry
        """
        # Accept MCP client to communicate with kernel server
        self.mcp_client = mcp_client
        self.content_generator = content_generator
        self.kernel = kernel  # Direct access to kernel for registry access if provided
        
        # Initialize kernel services (will be set via set_kernel_services)
        self.registry = None
        self.scheduler = None
        
        # Initialize components based on Qwen architecture
        self.turn_manager = TurnManager(mcp_client, content_generator)

        
        # Initialize system context builder for creating system context with prompts
        self.system_context_builder = SystemContextBuilder(self.mcp_client, self.kernel)
        
        # Initialize conversation history to maintain context across interactions
        self.conversation_history = []

    def set_kernel_services(self, registry=None, scheduler=None, tool_execution_manager=None):
        """
        Set direct references to kernel services for streamlined operations.
        
        Args:
            registry: Kernel registry for tool access
            scheduler: Kernel scheduler for tool execution (deprecated)
            tool_execution_manager: Kernel's ToolExecutionManager for all tool execution scenarios
        """
        self.registry = registry
        # Use the ToolExecutionManager for new architecture
        self.tool_execution_manager = tool_execution_manager
        # We're fully committing to the new architecture - not maintaining scheduler compatibility
        
        # Update components with direct kernel services
        if self.turn_manager:
            self.turn_manager.registry = registry
            # Use the new tool execution manager
            self.turn_manager.tool_execution_manager = tool_execution_manager


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

        
        # Also update kernel and MCP client references on the provider directly if available
        if hasattr(provider, 'kernel') and self.kernel:
            provider.kernel = self.kernel
        if hasattr(provider, 'mcp_client') and self.mcp_client:
            provider.mcp_client = self.mcp_client

    async def handle_ai_interaction(self, prompt_obj: PromptObject) -> PromptObject:
        """
        Handle an AI interaction using a prompt object natively.
        This is the primary interface that works directly with PromptObjects.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Returns:
            The updated prompt object with results
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Apply the tool inclusion policy directly to the prompt object
        self._get_tool_inclusion_policy_for_prompt(prompt_obj)
        
        # Fetch and populate tools based on the policy
        if (prompt_obj.tool_policy and 
            prompt_obj.tool_policy.value != "none" and 
            not prompt_obj.custom_tools):  # Only fetch if custom_tools isn't already populated
            available_tools = await self._get_available_tools()
            if available_tools:
                prompt_obj.custom_tools = available_tools
        
        # Apply system context to the prompt object
        success = await self.system_context_builder.build_and_apply_system_context(prompt_obj)
        if not success:
            # If building system context failed, we can still continue with the interaction
            # but log the issue
            import logging
            logging.warning("Failed to build and apply system context, continuing with interaction")
        
        # Use the turn manager to properly handle the interaction with potential tool calls
        # Create an abort signal for the turn
        import asyncio
        abort_signal = asyncio.Event()
        
        # Process the interaction using turn manager which handles the streaming/non-streaming
        # transition for tool execution
        final_response = ""
        
        try:
            async for event in self.turn_manager.run_turn(
                prompt_obj,
                abort_signal
            ):
                if event.type == TurnEventType.CONTENT:
                    if prompt_obj.streaming_enabled:
                        # In streaming mode, accumulate content events
                        final_response += event.value
                    # In non-streaming mode, content is handled internally by the turn manager,
                    # and the prompt object will be updated with the final result
                elif event.type == TurnEventType.TOOL_CALL_RESPONSE:
                    # Tool result handled internally by turn manager
                    continue
                elif event.type == TurnEventType.ERROR:
                    if prompt_obj.streaming_enabled:
                        # Only accumulate error messages in streaming mode
                        final_response += f"\nError: {event.error}"
                    # Update prompt object with error
                    prompt_obj.mark_error(str(event.error))
                    return prompt_obj
                elif event.type == TurnEventType.FINISHED:
                    break
        except Exception as e:
            prompt_obj.mark_error(str(e))
            return prompt_obj
        
        # Update the result content in the prompt object
        if prompt_obj.streaming_enabled and final_response:
            # In streaming mode, use accumulated response
            prompt_obj.result_content = final_response
            prompt_obj.mark_completed(final_response)
        else:
            # In non-streaming mode, the prompt object should have been updated internally
            # by the content generator and turn manager after the complete turn
            if not prompt_obj.result_content:
                # Fallback to mark as completed with some default content if no content was generated
                prompt_obj.result_content = "Interaction completed"
            prompt_obj.mark_completed(prompt_obj.result_content)
        
        # Update conversation history from result
        self.conversation_history = prompt_obj.conversation_history
        
        # Return the result
        return prompt_obj

    async def stream_ai_interaction(self, prompt_obj: PromptObject) -> AsyncGenerator[str, None]:
        """
        Stream an AI interaction using a prompt object natively.
        This is the primary interface that works directly with PromptObjects.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Yields:
            Partial response strings as they become available
        """
        # Apply the tool inclusion policy directly to the prompt object
        self._get_tool_inclusion_policy_for_prompt(prompt_obj)
        
        # Fetch and populate tools based on the policy
        if (prompt_obj.tool_policy and 
            prompt_obj.tool_policy.value != "none" and 
            not prompt_obj.custom_tools):  # Only fetch if custom_tools isn't already populated
            available_tools = await self._get_available_tools()
            if available_tools:
                prompt_obj.custom_tools = available_tools
        
        # Apply system context to the prompt object
        success = await self.system_context_builder.build_and_apply_system_context(prompt_obj)
        if not success:
            # If building system context failed, we can still continue with the interaction
            # but log the issue
            import logging
            logging.warning("Failed to build and apply system context, continuing with interaction")
        
        # Ensure the content generator has access to the kernel and kernel client
        if hasattr(self.content_generator, 'kernel'):
            self.content_generator.kernel = self.kernel
        if hasattr(self.content_generator, 'kernel_client'):
            self.content_generator.mcp_client = self.mcp_client
        
        # Stream using the turn manager which handles potential tool calls during interaction
        import asyncio
        abort_signal = asyncio.Event()
        
        async for event in self.turn_manager.run_turn(
            prompt_obj,
            abort_signal
        ):
            if event.type == TurnEventType.CONTENT:
                yield event.value
        
        # Update conversation history from result (for compatibility with get_conversation_history)
        self.conversation_history = prompt_obj.conversation_history



    def _get_tool_inclusion_policy_for_prompt(self, prompt_obj: 'PromptObject') -> 'ToolInclusionConfig':
        """
        Determine the appropriate tool inclusion policy for a given prompt object.
        Sets the policy directly on the prompt object and returns the config.
        
        Args:
            prompt_obj: The prompt object to analyze and set the policy for
            
        Returns:
            A ToolInclusionConfig object with the appropriate policy
        """
        from gcs_kernel.models import ToolInclusionPolicy, ToolInclusionConfig
        
        # Analyze the prompt content to determine the appropriate policy
        content = prompt_obj.content.lower()
        
        # Simple heuristic approach - you can make this more sophisticated
        # For now, we'll default to ALL_AVAILABLE for most prompts
        # In a more advanced system, this would analyze the prompt content
        policy = ToolInclusionPolicy.ALL_AVAILABLE
        
        # Example of more sophisticated policy determination:
        if any(keyword in content for keyword in ["no tools", "without tools", "no function", "no functions"]):
            policy = ToolInclusionPolicy.NONE
        elif "use specific tools" in content:
            # Could return a custom set of tools here
            policy = ToolInclusionPolicy.CUSTOM
        elif "contextual tools" in content:
            policy = ToolInclusionPolicy.CONTEXTUAL_SUBSET
        
        # Set the policy directly on the prompt object
        prompt_obj.tool_policy = policy

        return ToolInclusionConfig(
            prompt_id=prompt_obj.prompt_id,
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
            tools_response = await self.mcp_client.list_tools()
            
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