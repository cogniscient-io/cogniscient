"""
Turn Manager for GCS Kernel AI Orchestrator.

This module implements the TurnManager which handles the turn-based AI interaction,
managing the flow between streaming content and tool execution as per Qwen architecture.
"""

import asyncio
import logging
from typing import Any, Optional, AsyncGenerator
from enum import Enum
from datetime import datetime

from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult, PromptObject
from services.llm_provider.base_generator import BaseContentGenerator

# Set up logging
logger = logging.getLogger(__name__)


class TurnEventType(str, Enum):
    """Event types for turn-based processing."""
    CONTENT = "content"
    TOOL_CALL_REQUEST = "tool_call_request"
    TOOL_CALL_RESPONSE = "tool_call_response"
    FINISHED = "finished"
    ERROR = "error"


class TurnEvent:
    """Represents an event in a turn of interaction."""

    def __init__(self, type: TurnEventType, value: Any = None, error: Optional[Exception] = None):
        self.type = type
        self.value = value
        self.error = error


class TurnManager:
    """
    Manages the turn-based interaction between streaming and non-streaming operations.
    Handles the flow where LLM generates content, detects tool calls, executes tools,
    and continues the conversation.
    """

    def __init__(self,
                 mcp_client: MCPClient,
                 content_generator: BaseContentGenerator):
        """
        Initialize the turn manager.

        Args:
            mcp_client: MCP client for communicating with the MCP server
            content_generator: Content generator for LLM interactions
        """
        self.mcp_client = mcp_client
        self.content_generator = content_generator
        self.registry = None  # Will be set via set_kernel_services
        # We're fully committing to the new architecture - removing scheduler
        self.tool_execution_manager = None  # Will be set via set_kernel_services (new architecture)
        self.conversation_history = []

    def get_conversation_history(self) -> list:
        """
        Get the current conversation history for this turn.

        Returns:
            List of conversation messages
        """
        return self.conversation_history

    def initialize_conversation_history(self, history: list):
        """
        Initialize the conversation history for this turn.

        Args:
            history: Initial list of conversation messages
        """
        self.conversation_history = history if history is not None else []

    async def run_turn(self,
                      prompt_obj: PromptObject,
                      signal: Optional[asyncio.Event] = None) -> AsyncGenerator[TurnEvent, None]:
        """
        Run a single turn of interaction with streaming events using a prompt object.

        Args:
            prompt_obj: The prompt object containing all necessary information
            signal: Optional abort signal
        """
        # Add the new user prompt to the conversation history in the prompt object
        prompt_obj.add_user_message(prompt_obj.content)

        # Get the initial response (streaming or non-streaming)
        if prompt_obj.streaming_enabled:
            # Stream the response from LLM using the content generator's streaming method
            async for chunk in self.content_generator.stream_response(prompt_obj):
                yield TurnEvent(TurnEventType.CONTENT, chunk)
        else:
            # Generate a complete response without streaming
            # Content generator operates on the live prompt object in place
            await self.content_generator.generate_response(prompt_obj)

        # After processing completes, get the complete response from the prompt object
        # since the content generator has already processed the response (with or without streaming)
        # The content generator operates on the live prompt object in place
        current_tool_calls = prompt_obj.tool_calls
        full_response_content = prompt_obj.result_content

        # Process any tool calls in a loop - handles initial calls and any recursive calls
        # Add max iterations to prevent infinite loops
        max_tool_call_iterations = 10
        iteration_count = 0

        while current_tool_calls:
            iteration_count += 1
            if iteration_count > max_tool_call_iterations:
                # Prevent infinite loops by limiting the number of tool call iterations
                break
            # Add assistant message with tool calls to the prompt object's conversation history
            prompt_obj.add_assistant_message(
                full_response_content or prompt_obj.result_content,
                tool_calls=current_tool_calls
            )

            # Process each tool call - handle both OpenAI format dictionaries and ToolCall objects
            for tool_call in current_tool_calls:
                # Use ToolCall utility to ensure proper format handling and create ToolCall object
                from gcs_kernel.tool_call_model import ToolCall
                openai_tool_call = ToolCall.ensure_openai_format(tool_call)
                tool_call_obj = ToolCall.from_openai_format(openai_tool_call)

                # Extract information from the ToolCall object for events
                tool_call_name = tool_call_obj.name
                tool_call_id = tool_call_obj.id
                tool_call_arguments = tool_call_obj.arguments_json

                if tool_call_name and tool_call_name.strip():
                    try:
                        if signal and signal.is_set():
                            yield TurnEvent(TurnEventType.ERROR, error=Exception("Turn cancelled by user\n"))
                            return

                        # Provide user feedback that a tool is being executed (only for streaming mode)
                        if prompt_obj.streaming_enabled:
                            yield TurnEvent(TurnEventType.CONTENT, f"[{tool_call_name}: {tool_call_arguments}]\n")

                        # Yield tool call request event for internal processing (in both streaming and non-streaming modes)
                        yield TurnEvent(TurnEventType.TOOL_CALL_REQUEST, {
                            "call_id": tool_call_id,
                            "name": tool_call_name,
                            "arguments": tool_call_arguments
                        })

                        # Execute the tool using the unified method from ToolExecutionManager
                        tool_execution_result = await self.tool_execution_manager.execute_tool_call(tool_call_obj)
                        tool_result = tool_execution_result['result']

                        # Add tool result to the prompt object's conversation history
                        prompt_obj.add_tool_message(tool_result.llm_content, tool_call_id)

                        # Yield tool call response event (in both streaming and non-streaming modes)
                        yield TurnEvent(TurnEventType.TOOL_CALL_RESPONSE, {
                            "call_id": tool_call_id,
                            "result": tool_result
                        })

                    except Exception as e:
                        error_result = ToolResult(
                            tool_name=tool_call_name,
                            success=False,
                            error=f"Error executing tool: {str(e)}",
                            llm_content=f"Error executing tool {tool_call_name}: {str(e)}",
                            return_display=f"Error executing tool {tool_call_name}: {str(e)}"
                        )

                        if prompt_obj.streaming_enabled:
                            yield TurnEvent(TurnEventType.ERROR, error_result.error)
                        return
                else:
                    # Add a message to the conversation history to inform about the invalid tool call
                    prompt_obj.add_tool_message(
                        "Error: Invalid tool call detected - tool name is empty or malformed. Please try rephrasing your request.",
                        tool_call_id if 'tool_call_id' in locals() else "unknown"
                    )

            # Clear the processed tool calls from the prompt object before generating a new response
            # The content generator will add new tool calls to prompt_obj if needed
            logger.debug(f"TurnManager run_turn - Cleared processed tool calls, prompt_obj.tool_calls before clearing: {prompt_obj.tool_calls}")
            prompt_obj.tool_calls = []
            logger.debug(f"TurnManager run_turn - After clearing tool calls, prompt_obj.tool_calls: {prompt_obj.tool_calls}")

            # After executing tool calls, get the next response from the content generator
            # using the updated prompt object which now includes tool results in the conversation history
            # Always use non-streaming for responses after tool execution to avoid complications
            # Create a temporary prompt object with streaming disabled for this internal call
            was_streaming = prompt_obj.streaming_enabled
            prompt_obj.streaming_enabled = False  # Temporarily disable streaming for internal call

            logger.debug(f"TurnManager run_turn - Calling generate_response, prompt_obj.tool_calls before: {prompt_obj.tool_calls}")
            await self.content_generator.generate_response(prompt_obj)
            logger.debug(f"TurnManager run_turn - After generate_response, prompt_obj.tool_calls: {prompt_obj.tool_calls}, result_content: '{prompt_obj.result_content}'")

            prompt_obj.streaming_enabled = was_streaming  # Restore original streaming setting

            # Get the new tool calls for the next iteration (if any)
            current_tool_calls = prompt_obj.tool_calls
            full_response_content = prompt_obj.result_content
            logger.debug(f"TurnManager run_turn - End of loop iteration, current_tool_calls: {current_tool_calls}, full_response_content: '{full_response_content}'")

        # Yield final content in non-streaming mode or when tool calls were processed in streaming mode
        if (not prompt_obj.streaming_enabled) or (prompt_obj.streaming_enabled and iteration_count > 0):
            yield TurnEvent(TurnEventType.CONTENT, full_response_content)
        # In streaming mode with no tool calls, content was already streamed chunk by chunk,
        # so we don't send it again to avoid duplication

        # Update the prompt object with the final result content
        # The result content was already updated during the tool call processing loop
        # If tool calls were processed, the prompt object will have the final response after all processing
        prompt_obj.result_content = full_response_content

        # Clean up the prompt object after the turn is completed
        try:
            # Mark the prompt object as completed if not already marked
            if prompt_obj.status.value != "completed" and prompt_obj.status.value != "error":
                prompt_obj.mark_completed(prompt_obj.result_content or "Interaction completed")

            # Update the prompt object's metadata for cleanup
            prompt_obj.updated_at = datetime.now()

        except Exception:
            # If cleanup fails, just continue - this is not critical for functionality
            pass

        yield TurnEvent(TurnEventType.FINISHED)

    async def _wait_for_execution_result(self, execution_id: str, timeout: int = 60):
        """
        Wait for an execution to complete and return its result.

        Args:
            execution_id: The ID of the execution to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            The execution result or None if timeout occurs
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            result = await self.mcp_client.get_execution_result(execution_id)
            if result:
                return result
            await asyncio.sleep(0.5)  # Check every 0.5 seconds

        return None