"""
Turn Manager for GCS Kernel AI Orchestrator.

This module implements the TurnManager which handles the turn-based AI interaction,
managing the flow between streaming content and tool execution.
"""

import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from enum import Enum

from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult
from services.llm_provider.base_generator import BaseContentGenerator


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
                 kernel_client: MCPClient, 
                 content_generator: BaseContentGenerator, 
                 kernel=None):
        """
        Initialize the turn manager.
        
        Args:
            kernel_client: MCP client for communicating with the kernel
            content_generator: Content generator for LLM interactions
            kernel: Optional direct reference to kernel for registry access
        """
        self.kernel_client = kernel_client
        self.content_generator = content_generator
        self.kernel = kernel
        self.registry = None  # Will be set via set_kernel_services
        self.scheduler = None  # Will be set via set_kernel_services
        self.conversation_history = []

    async def run_turn(self, 
                      prompt: str, 
                      system_context: str, 
                      signal: Optional[asyncio.Event] = None) -> AsyncGenerator[TurnEvent, None]:
        """
        Run a single turn of interaction with streaming events.
        
        Args:
            prompt: User's input prompt
            system_context: System context to provide to the LLM
            signal: Optional abort signal
            
        Yields:
            TurnEvent objects representing different stages of the interaction
        """
        # Reset conversation history to OpenAI format for this turn
        self.conversation_history = []
        
        # Initialize conversation in OpenAI format
        messages = [{"role": "user", "content": prompt}]
        if system_context:
            messages.insert(0, {"role": "system", "content": system_context})
        
        # Use the conversation history directly
        self.conversation_history = messages
        
        # Get initial response from LLM (potentially with tool calls)
        initial_response = await self.content_generator.generate_response(
            prompt,  # This will be ignored in favor of conversation history
            system_context=system_context
        )
        
        # Process the response based on whether it contains tool calls
        if hasattr(initial_response, 'tool_calls') and initial_response.tool_calls:
            # The response contains tool calls, so we need to execute them
            
            # Add assistant message with tool calls to conversation history
            assistant_message = {
                "role": "assistant",
                "content": initial_response.content,
                "tool_calls": []
            }
            
            for tool_call in initial_response.tool_calls:
                # Only add valid tool calls (with non-empty names)
                if tool_call.name and tool_call.name.strip():
                    assistant_message["tool_calls"].append({
                        "id": tool_call.id,
                        "type": "function",  # Keeping 'function' type for compatibility
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments_json  # Now directly uses the JSON string format
                        }
                    })
            
            # Only add the assistant message if it has valid tool calls
            if assistant_message["tool_calls"]:
                self.conversation_history.append(assistant_message)
            
            # Process each tool call
            for tool_call in initial_response.tool_calls:
                # Only process valid tool calls (with non-empty names)
                if tool_call.name and tool_call.name.strip():
                    try:
                        if signal and signal.is_set():
                            yield TurnEvent(TurnEventType.ERROR, error=Exception("Turn cancelled by user"))
                            return
                        
                        # Yield tool call request event
                        yield TurnEvent(TurnEventType.TOOL_CALL_REQUEST, {
                            "call_id": tool_call.id,
                            "name": tool_call.name,
                            "arguments": tool_call.arguments
                        })
                        
                        # Execute the tool
                        tool_result = await self._execute_tool_call(tool_call)
                        
                        # Add tool result to conversation history
                        tool_message = {
                            "role": "tool",
                            "content": tool_result.llm_content,
                            "tool_call_id": tool_call.id
                        }
                        self.conversation_history.append(tool_message)
                        

                        
                        # Yield tool call response event
                        yield TurnEvent(TurnEventType.TOOL_CALL_RESPONSE, {
                            "call_id": tool_call.id,
                            "result": tool_result
                        })
                        
                    except Exception as e:
                        error_result = ToolResult(
                            tool_name=tool_call.name,
                            success=False,
                            error=f"Error executing tool: {str(e)}",
                            llm_content=f"Error executing tool {tool_call.name}: {str(e)}",
                            return_display=f"Error executing tool {tool_call.name}: {str(e)}"
                        )
                        
                        yield TurnEvent(TurnEventType.ERROR, error=error_result.error)
                        return
                else:
                    # Add a message to the conversation history to inform about the invalid tool call
                    invalid_tool_message = {
                        "role": "tool",
                        "content": "Error: Invalid tool call detected - tool name is empty or malformed. Please try rephrasing your request.",
                        "tool_call_id": tool_call.id
                    }
                    self.conversation_history.append(invalid_tool_message)
        
        # After processing tool calls (or if there were none), get final response
        if hasattr(initial_response, 'tool_calls') and initial_response.tool_calls:
            # Continue the conversation to get new response based on tool results
            # Process recursively until there are no more tool calls
            continue_conversation = True
            max_turns = 10  # Prevent infinite loops
            turns = 0
            
            while continue_conversation and turns < max_turns:
                turns += 1
                
                # Generate new response based on updated conversation history
                current_response = await self.content_generator.generate_response(
                    prompt="",  # We're continuing from the conversation history
                    system_context=system_context
                )
                
                # Check if there are more tool calls
                if hasattr(current_response, 'tool_calls') and current_response.tool_calls:
                    # Add assistant message with tool calls to conversation history
                    assistant_message = {
                        "role": "assistant",
                        "content": current_response.content,
                        "tool_calls": []
                    }
                    
                    for tool_call in current_response.tool_calls:
                        # Only add valid tool calls (with non-empty names)
                        if tool_call.name and tool_call.name.strip():
                            assistant_message["tool_calls"].append({
                                "id": tool_call.id,
                                "type": "function",  # Keeping 'function' type for compatibility
                                "function": {
                                    "name": tool_call.name,
                                    "arguments": tool_call.arguments_json  # Now directly uses the JSON string format
                                }
                            })
                    
                    # Only add the assistant message if it has valid tool calls
                    if assistant_message["tool_calls"]:
                        self.conversation_history.append(assistant_message)
                    
                    # Process each tool call
                    for tool_call in current_response.tool_calls:
                        # Only process valid tool calls (with non-empty names)
                        if tool_call.name and tool_call.name.strip():
                            try:
                                if signal and signal.is_set():
                                    yield TurnEvent(TurnEventType.ERROR, error=Exception("Turn cancelled by user"))
                                    return
                                
                                # Yield tool call request event
                                yield TurnEvent(TurnEventType.TOOL_CALL_REQUEST, {
                                    "call_id": tool_call.id,
                                    "name": tool_call.name,
                                    "arguments": tool_call.arguments
                                })
                                
                                # Execute the tool
                                tool_result = await self._execute_tool_call(tool_call)
                                
                                # Add tool result to conversation history
                                tool_message = {
                                    "role": "tool",
                                    "content": tool_result.llm_content,
                                    "tool_call_id": tool_call.id
                                }
                                self.conversation_history.append(tool_message)
                                
                                # Yield tool call response event
                                yield TurnEvent(TurnEventType.TOOL_CALL_RESPONSE, {
                                    "call_id": tool_call.id,
                                    "result": tool_result
                                })
                                
                            except Exception as e:
                                error_result = ToolResult(
                                    tool_name=tool_call.name,
                                    success=False,
                                    error=f"Error executing tool: {str(e)}",
                                    llm_content=f"Error executing tool {tool_call.name}: {str(e)}",
                                    return_display=f"Error executing tool {tool_call.name}: {str(e)}"
                                )
                                
                                yield TurnEvent(TurnEventType.ERROR, error=error_result.error)
                                return
                        else:
                            # Add a message to the conversation history to inform about the invalid tool call
                            invalid_tool_message = {
                                "role": "tool",
                                "content": "Error: Invalid tool call detected - tool name is empty or malformed. Please try rephrasing your request.",
                                "tool_call_id": tool_call.id
                            }
                            self.conversation_history.append(invalid_tool_message)
                else:
                    # If there are no more tool calls, break out of the loop
                    continue_conversation = False
                    
                    # Yield the final content from the response
                    if hasattr(current_response, 'content') and current_response.content:
                        yield TurnEvent(TurnEventType.CONTENT, current_response.content)
        else:
            # If there were no tool calls, just return the initial content
            if initial_response.content:
                yield TurnEvent(TurnEventType.CONTENT, initial_response.content)
        
        yield TurnEvent(TurnEventType.FINISHED)

    async def _execute_tool_call(self, tool_call):
        """
        Execute a single tool call using the kernel's scheduler for consistent execution flow.
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            ToolResult from the execution
        """
        # Use the kernel's registry to get the tool definition
        if self.registry:
            tool_def = await self.registry.get_tool(tool_call.name)
            if tool_def:
                # Use the kernel's scheduler for execution
                if self.scheduler:
                    # Submit the tool execution through the scheduler
                    execution_id = await self.scheduler.submit_tool_execution(tool_def, tool_call.arguments)
                    
                    # Wait for the execution to complete using the scheduler
                    max_wait = 60  # seconds
                    start_time = asyncio.get_event_loop().time()
                    
                    while (asyncio.get_event_loop().time() - start_time) < max_wait:
                        result = self.scheduler.get_execution_result(execution_id)
                        if result:
                            return result
                        await asyncio.sleep(0.5)  # Check every 0.5 seconds
                    
                    # Timeout case
                    return ToolResult(
                        tool_name=tool_call.name,
                        success=False,
                        error=f"Tool execution {execution_id} did not return a result within timeout",
                        llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                        return_display=f"Tool execution {execution_id} did not return a result within timeout"
                    )
                else:
                    # Fallback: execute directly if scheduler not available
                    return await tool_def.execute(tool_call.arguments)
            else:
                # Tool not found in registry
                return ToolResult(
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Tool '{tool_call.name}' not found in registry",
                    llm_content=f"Tool '{tool_call.name}' not found in registry",
                    return_display=f"Tool '{tool_call.name}' not found in registry"
                )
        else:
            # Use MCP client as fallback
            execution_id = await self.kernel_client.submit_tool_execution(
                tool_call.name,
                tool_call.arguments
            )
            
            # Wait for tool execution to complete with timeout
            result = await self._wait_for_execution_result(execution_id, timeout=60)
            if result:
                return result
            else:
                # Handle the case where no result was returned
                return ToolResult(
                    tool_name=tool_call.name,
                    success=False,
                    error=f"Tool execution {execution_id} did not return a result within timeout",
                    llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                    return_display=f"Tool execution {execution_id} did not return a result within timeout"
                )

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
            result = await self.kernel_client.get_execution_result(execution_id)
            if result:
                return result
            await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
        return None

    def get_conversation_history(self):
        """
        Get the current conversation history.
        
        Returns:
            The conversation history as a list of message objects
        """
        return self.conversation_history

    def add_message_to_history(self, role: str, content: str):
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message (e.g., "user", "assistant", "tool")
            content: The content of the message
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def reset_conversation(self):
        """
        Reset the conversation history.
        """
        self.conversation_history = []