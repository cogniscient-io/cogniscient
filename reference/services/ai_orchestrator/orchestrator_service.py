"""
AI Orchestrator Service implementation for the GCS Kernel.

This module implements the AIOrchestratorService which manages AI interactions,
session management, and provider abstraction. The content generator must be
provided separately to maintain clean separation of concerns.
"""

import asyncio
import json
import time
import random
from typing import Any, Dict, Optional
from enum import Enum
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult, ToolDefinition
from services.llm_provider.base_generator import BaseContentGenerator


class ToolCallStatus(str, Enum):
    """Enum representing different states of tool calls"""
    VALIDATING = "validating"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class ToolCallState:
    """Class to track the state of a single tool call"""
    def __init__(self, call_id: str, tool_name: str, parameters: Dict[str, Any]):
        self.call_id = call_id
        self.tool_name = tool_name
        self.parameters = parameters
        self.status = ToolCallStatus.VALIDATING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None
        self.result: Optional[ToolResult] = None
        self.outcome: Optional[str] = None  # For approval outcomes


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
        
        # Initialize system context builder
        from .system_context_builder import SystemContextBuilder
        self.system_context_builder = SystemContextBuilder(kernel_client, kernel)
        
        # Initialize conversation history to maintain context across tool calls
        self.conversation_history = []
        # Track active tool calls for proper state management using the new ToolCallState
        self.active_tool_calls = {}  # Maps call_id to ToolCallState
        self.completed_tool_calls = {}  # Maps call_id to ToolCallState

    def set_content_generator(self, provider: 'BaseContentGenerator'):
        """
        Set the content generator for this orchestrator.
        The provider should extend BaseContentGenerator.
        
        Args:
            provider: The content generator to use for AI interactions
        """
        self.content_generator = provider

    async def handle_ai_interaction(self, prompt: str) -> str:
        """
        Handle an AI interaction and process any tool calls.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The AI response string
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Reset conversation history for new interaction
        self.conversation_history = []
        
        # Add the user's prompt to the conversation history
        user_message = {
            "role": "user", 
            "content": prompt
        }
        self.conversation_history.append(user_message)
        
        # Get system context with available tools information
        system_context = await self.system_context_builder.build_system_context()
        
        # Get available tools to provide to the LLM natively
        available_tools = await self.system_context_builder.get_available_tools()
        
        # Convert available tools to kernel tool format to pass to LLM
        kernel_tools = []
        for tool_name, tool_info in available_tools.items():
            kernel_tool = {
                "name": tool_info.get("name", tool_name),
                "description": tool_info.get("description", ""),
                "parameters": tool_info.get("parameter_schema", {})
            }
            kernel_tools.append(kernel_tool)
        
        # Use AI client to generate response with potential tool calls
        # Pass both system context and tools to enable native tool calling
        # Wrap with retry logic in case of transient errors
        async def _generate_response():
            return await self.content_generator.generate_response(
                prompt, 
                system_context=system_context,
                tools=kernel_tools
            )
        
        try:
            response = await self._retry_with_backoff(
                _generate_response,
                max_retries=3,
                base_delay=1.0,
                allowed_exceptions=(Exception,)
            )
        except Exception as e:
            # Handle error with context
            error_context = self._create_error_context(
                "generate_response", 
                {"prompt": prompt, "tools_count": len(kernel_tools)}
            )
            await self._handle_error_with_context(e, error_context)
            
            # Return an error response instead of failing completely
            class ErrorResponseObj:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls if tool_calls else []
            
            response = ErrorResponseObj(
                content=f"Error generating response: {str(e)}",
                tool_calls=[]
            )
        
        # Check if the response contains tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Add the assistant's message (with tool calls) to the conversation history
            assistant_message = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": []
            }
            
            # Format the tool calls for the conversation history
            for tool_call in response.tool_calls:
                assistant_message["tool_calls"].append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.parameters)
                    }
                })
            
            self.conversation_history.append(assistant_message)
            
            # Process each tool call
            for tool_call in response.tool_calls:
                try:
                    # Validate the tool call before execution
                    validation_result = self._validate_tool_call(tool_call.name, tool_call.parameters, available_tools)
                    
                    if not validation_result['valid']:
                        # Handle validation error by returning it to the LLM
                        error_result = ToolResult(
                            tool_name=tool_call.name,
                            success=False,
                            error=validation_result['error'],
                            llm_content=validation_result['error'],
                            return_display=validation_result['error']
                        )
                        response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                        # Update the conversation history in the orchestrator with the error response from the LLM
                        if hasattr(response, 'content') and response.content:
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": response.content
                            })
                        continue  # Skip to the next tool call

                    # Check if tool exists in local kernel registry
                    local_tool = None
                    if self.kernel and hasattr(self.kernel, 'registry'):
                        local_tool = await self.kernel.registry.get_tool(tool_call.name)
                    
                    if local_tool:
                        # Execute tool directly from local registry
                        tool_result = await local_tool.execute(tool_call.parameters)
                        
                        # Add the tool's result to the conversation history
                        tool_message = {
                            "role": "tool",
                            "content": tool_result.llm_content,
                            "tool_call_id": tool_call.id  # Use the tool call ID from assistant message
                        }
                        self.conversation_history.append(tool_message)
                        
                        # Process the result and continue interaction
                        response = await self.content_generator.process_tool_result(tool_result, self.conversation_history)
                        # Update the conversation history in the orchestrator with the new response from the LLM
                        if hasattr(response, 'content') and response.content:
                            assistant_message = {
                                "role": "assistant",
                                "content": response.content
                            }
                            self.conversation_history.append(assistant_message)
                    else:
                        # Submit tool execution through MCP for remote tools
                        execution_id = await self.kernel_client.submit_tool_execution(
                            tool_call.name,
                            tool_call.parameters
                        )
                        
                        # Wait for tool execution to complete with timeout
                        result = await self._wait_for_execution_result(execution_id, timeout=60)
                        
                        if result:
                            # Add the tool's result to the conversation history
                            tool_message = {
                                "role": "tool",
                                "content": result.llm_content,
                                "tool_call_id": tool_call.id  # Use the tool call ID from assistant message
                            }
                            self.conversation_history.append(tool_message)
                            
                            # Process the result and continue interaction
                            response = await self.content_generator.process_tool_result(result, self.conversation_history)
                            # Update the conversation history in the orchestrator with the new response from the LLM
                            if hasattr(response, 'content') and response.content:
                                assistant_message = {
                                    "role": "assistant",
                                    "content": response.content
                                }
                                self.conversation_history.append(assistant_message)
                        else:
                            # Handle the case where no result was returned
                            error_result = ToolResult(
                                tool_name=tool_call.name,
                                success=False,
                                error=f"Tool execution {execution_id} did not return a result within timeout",
                                llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                                return_display=f"Tool execution {execution_id} did not return a result within timeout"
                            )
                            
                            # Add the error result to the conversation history
                            tool_message = {
                                "role": "tool",
                                "content": error_result.llm_content,
                                "tool_call_id": tool_call.id
                            }
                            self.conversation_history.append(tool_message)
                            
                            response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                            # Update the conversation history in the orchestrator with the error response from the LLM
                            if hasattr(response, 'content') and response.content:
                                assistant_message = {
                                    "role": "assistant",
                                    "content": response.content
                                }
                                self.conversation_history.append(assistant_message)
                        
                except Exception as e:
                    # Handle exception when executing tool
                    error_result = ToolResult(
                        tool_name=tool_call.name,
                        success=False,
                        error=f"Error executing tool: {str(e)}",
                        llm_content=f"Error executing tool {tool_call.name}: {str(e)}",
                        return_display=f"Error executing tool {tool_call.name}: {str(e)}"
                    )
                    
                    # Add the error result to the conversation history
                    tool_message = {
                        "role": "tool",
                        "content": error_result.llm_content,
                        "tool_call_id": tool_call.id
                    }
                    self.conversation_history.append(tool_message)
                    
                    response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                    # Update the conversation history in the orchestrator with the error response from the LLM
                    if hasattr(response, 'content') and response.content:
                        assistant_message = {
                            "role": "assistant",
                            "content": response.content
                        }
                        self.conversation_history.append(assistant_message)
        
        return getattr(response, 'content', str(response))
    
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

    def _validate_tool_call(self, tool_name: str, parameters: Dict[str, Any], available_tools: Dict[str, Any]):
        """
        Validate a tool call before execution.
        
        Args:
            tool_name: The name of the tool to call
            parameters: The parameters to pass to the tool
            available_tools: Dictionary of available tools from the registry
            
        Returns:
            Validation result dictionary
        """
        from services.llm_provider.tool_call_validator import validate_tool_call
        return validate_tool_call(tool_name, parameters, available_tools)

    async def reset_conversation(self):
        """
        Reset the conversation history and active tool calls.
        """
        self.conversation_history = []
        self.active_tool_calls = {}
        self.completed_tool_calls = {}

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

    def create_tool_call_state(self, call_id: str, tool_name: str, parameters: Dict[str, Any]) -> ToolCallState:
        """
        Create and track a new tool call state.
        
        Args:
            call_id: The unique ID for the tool call
            tool_name: The name of the tool being called
            parameters: The parameters for the tool call
            
        Returns:
            The created ToolCallState object
        """
        tool_call_state = ToolCallState(
            call_id=call_id,
            tool_name=tool_name,
            parameters=parameters
        )
        tool_call_state.status = ToolCallStatus.VALIDATING
        tool_call_state.start_time = asyncio.get_event_loop().time()
        self.active_tool_calls[call_id] = tool_call_state
        return tool_call_state

    def update_tool_call_status(self, call_id: str, status: ToolCallStatus, result: Optional[ToolResult] = None, error: Optional[str] = None):
        """
        Update the status of a tool call.
        
        Args:
            call_id: The ID of the tool call to update
            status: The new status
            result: Optional result if the tool completed successfully
            error: Optional error message if the tool failed
        """
        if call_id in self.active_tool_calls:
            tool_call_state = self.active_tool_calls[call_id]
            tool_call_state.status = status
            tool_call_state.result = result
            tool_call_state.error = error
            tool_call_state.end_time = asyncio.get_event_loop().time()
            
            # Move from active to completed
            self.completed_tool_calls[call_id] = self.active_tool_calls[call_id]
            del self.active_tool_calls[call_id]

    def get_active_tool_status(self):
        """
        Get the status of active tool calls.
        
        Returns:
            Dictionary of active tool calls and their status
        """
        return self.active_tool_calls

    def get_completed_tool_calls(self):
        """
        Get all completed tool calls.
        
        Returns:
            Dictionary of completed tool calls and their states
        """
        return self.completed_tool_calls

    def get_all_tool_call_status(self):
        """
        Get the status of all tool calls (both active and completed).
        
        Returns:
            Tuple of (active_tool_calls, completed_tool_calls)
        """
        return self.active_tool_calls, self.completed_tool_calls

    async def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, 
                                  backoff_factor: float = 2.0, jitter: bool = True, 
                                  allowed_exceptions: tuple = (Exception,)):
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: The async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Multiplier applied to delay between attempts
            jitter: Whether to add randomness to delay to prevent thundering herd
            allowed_exceptions: Tuple of exceptions that trigger a retry
            
        Returns:
            Result of the function call
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 to include initial attempt
            try:
                return await func()
            except allowed_exceptions as e:
                last_exception = e
                
                if attempt == max_retries:  # Last attempt (all retries exhausted)
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                
                # Add jitter to prevent thundering herd
                if jitter:
                    delay = delay * random.uniform(0.5, 1.0)
                
                if self.kernel and hasattr(self.kernel, 'logger'):
                    self.kernel.logger.warning(
                        f"Attempt {attempt + 1} failed: {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                else:
                    print(f"Attempt {attempt + 1} failed: {type(e).__name__}: {e}. "
                          f"Retrying in {delay:.2f} seconds...")
                
                await asyncio.sleep(delay)
        
        # Re-raise the last exception after all retries are exhausted
        if last_exception:
            raise last_exception

    def _categorize_error(self, error: Exception) -> str:
        """
        Categorize an error based on its type and content.
        
        Args:
            error: The exception to categorize
            
        Returns:
            String category of the error
        """
        error_str = str(error).lower()
        
        # Check for network-related errors
        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            return "NETWORK_ERROR"
        
        # Check for authentication errors
        if "auth" in error_str or "unauthorized" in error_str or "401" in error_str:
            return "AUTH_ERROR"
        
        # Check for rate limiting errors
        if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            return "RATE_LIMIT_ERROR"
        
        # Check for resource not found errors
        if "not found" in error_str or "404" in error_str:
            return "NOT_FOUND_ERROR"
        
        # Check for server errors
        if "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
            return "SERVER_ERROR"
        
        # Check for validation errors
        if "validation" in error_str or "invalid" in error_str:
            return "VALIDATION_ERROR"
        
        # Default category
        return "UNKNOWN_ERROR"

    def _create_error_context(self, operation: str, context: dict = None) -> dict:
        """
        Create a context dictionary with relevant information for error reporting.
        
        Args:
            operation: Name of the operation that failed
            context: Additional context information
            
        Returns:
            Dictionary with error context information
        """
        error_context = {
            "operation": operation,
            "timestamp": time.time(),
            "conversation_length": len(self.conversation_history) if hasattr(self, 'conversation_history') else 0,
            "active_tools": len(self.active_tool_calls) if hasattr(self, 'active_tool_calls') else 0,
            "completed_tools": len(self.completed_tool_calls) if hasattr(self, 'completed_tool_calls') else 0,
        }
        
        if context:
            error_context.update(context)
        
        return error_context

    async def _handle_error_with_context(self, error: Exception, context: dict) -> dict:
        """
        Handle an error with additional context and categorization.
        
        Args:
            error: The exception that occurred
            context: Context information about when the error occurred
            
        Returns:
            Dictionary with error handling result
        """
        error_category = self._categorize_error(error)
        error_context = {
            **context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_category": error_category,
        }
        
        if self.kernel and hasattr(self.kernel, 'logger'):
            self.kernel.logger.error(f"Error in {context.get('operation', 'unknown operation')}: {error}", extra=error_context)
        else:
            print(f"Error in {context.get('operation', 'unknown operation')}: {error} - Context: {error_context}")
        
        return error_context

    def _validate_tool_call(self, tool_name: str, parameters: Dict[str, Any], available_tools: Dict[str, Any]):
        """
        Validate a tool call before execution.
        
        Args:
            tool_name: The name of the tool to call
            parameters: The parameters to pass to the tool
            available_tools: Dictionary of available tools from the registry
            
        Returns:
            Validation result dictionary
        """
        from services.llm_provider.tool_call_validator import validate_tool_call
        return validate_tool_call(tool_name, parameters, available_tools)

    
    async def stream_ai_interaction(self, prompt: str):
        """
        Stream an AI interaction and process any tool calls.
        
        Args:
            prompt: The user's input prompt
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Reset conversation history for new interaction
        self.conversation_history = []
        
        # Add the user's prompt to the conversation history
        user_message = {
            "role": "user", 
            "content": prompt
        }
        self.conversation_history.append(user_message)
        
        # Get system context with available tools information
        system_context = await self.system_context_builder.build_system_context()
        
        # Get available tools to provide to the LLM natively
        available_tools = await self.system_context_builder.get_available_tools()
        
        # Convert available tools to kernel tool format to pass to LLM
        kernel_tools = []
        for tool_name, tool_info in available_tools.items():
            kernel_tool = {
                "name": tool_info.get("name", tool_name),
                "description": tool_info.get("description", ""),
                "parameters": tool_info.get("parameter_schema", {})
            }
            kernel_tools.append(kernel_tool)
        
        # Get initial response from the content generator (this may contain tool calls)
        # Note: If the LLM returns tool calls, we can't truly stream in this implementation
        # as we need to execute tools first before we can continue the conversation
        response = await self.content_generator.generate_response(
            prompt, 
            system_context=system_context,
            tools=kernel_tools
        )
        
        # Check if the response contains tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Add the assistant's message (with tool calls) to the conversation history
            assistant_message = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": []
            }
            
            # Format the tool calls for the conversation history
            for tool_call in response.tool_calls:
                assistant_message["tool_calls"].append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.parameters)
                    }
                })
            
            self.conversation_history.append(assistant_message)
            
            # Process each tool call (synchronously in this implementation)
            final_response = None
            for tool_call in response.tool_calls:
                try:
                    # Validate the tool call before execution
                    validation_result = self._validate_tool_call(tool_call.name, tool_call.parameters, available_tools)
                    
                    if not validation_result['valid']:
                        # Handle validation error by returning it to the LLM
                        error_result = ToolResult(
                            tool_name=tool_call.name,
                            success=False,
                            error=validation_result['error'],
                            llm_content=validation_result['error'],
                            return_display=validation_result['error']
                        )
                        final_response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                        continue  # Skip to the next tool call

                    # Check if tool exists in local kernel registry
                    local_tool = None
                    if self.kernel and hasattr(self.kernel, 'registry'):
                        local_tool = await self.kernel.registry.get_tool(tool_call.name)
                    
                    if local_tool:
                        # Execute tool directly from local registry
                        tool_result = await local_tool.execute(tool_call.parameters)
                        
                        # Add the tool's result to the conversation history
                        tool_message = {
                            "role": "tool",
                            "content": tool_result.llm_content,
                            "tool_call_id": tool_call.id  # Use the tool call ID from assistant message
                        }
                        self.conversation_history.append(tool_message)
                        
                        # Process the result and continue interaction
                        final_response = await self.content_generator.process_tool_result(tool_result, self.conversation_history)
                        # Update the conversation history in the orchestrator with the new response from the LLM
                        if hasattr(final_response, 'content') and final_response.content:
                            assistant_message = {
                                "role": "assistant",
                                "content": final_response.content
                            }
                            self.conversation_history.append(assistant_message)
                    else:
                        # Submit tool execution through MCP for remote tools
                        execution_id = await self.kernel_client.submit_tool_execution(
                            tool_call.name,
                            tool_call.parameters
                        )
                        
                        # Wait for tool execution to complete with timeout
                        result = await self._wait_for_execution_result(execution_id, timeout=60)
                        
                        if result:
                            # Add the tool's result to the conversation history
                            tool_message = {
                                "role": "tool",
                                "content": result.llm_content,
                                "tool_call_id": tool_call.id  # Use the tool call ID from assistant message
                            }
                            self.conversation_history.append(tool_message)
                            
                            # Process the result and continue interaction
                            final_response = await self.content_generator.process_tool_result(result, self.conversation_history)
                            # Update the conversation history in the orchestrator with the new response from the LLM
                            if hasattr(final_response, 'content') and final_response.content:
                                assistant_message = {
                                    "role": "assistant",
                                    "content": final_response.content
                                }
                                self.conversation_history.append(assistant_message)
                        else:
                            # Handle the case where no result was returned
                            error_result = ToolResult(
                                tool_name=tool_call.name,
                                success=False,
                                error=f"Tool execution {execution_id} did not return a result within timeout",
                                llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                                return_display=f"Tool execution {execution_id} did not return a result within timeout"
                            )
                            
                            # Add the error result to the conversation history
                            tool_message = {
                                "role": "tool",
                                "content": error_result.llm_content,
                                "tool_call_id": tool_call.id
                            }
                            self.conversation_history.append(tool_message)
                            
                            final_response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                            # Update the conversation history in the orchestrator with the error response from the LLM
                            if hasattr(final_response, 'content') and final_response.content:
                                assistant_message = {
                                    "role": "assistant",
                                    "content": final_response.content
                                }
                                self.conversation_history.append(assistant_message)
                        
                except Exception as e:
                    # Handle exception when executing tool
                    error_result = ToolResult(
                        tool_name=tool_call.name,
                        success=False,
                        error=f"Error executing tool: {str(e)}",
                        llm_content=f"Error executing tool {tool_call.name}: {str(e)}",
                        return_display=f"Error executing tool {tool_call.name}: {str(e)}"
                    )
                    
                    # Add the error result to the conversation history
                    tool_message = {
                        "role": "tool",
                        "content": error_result.llm_content,
                        "tool_call_id": tool_call.id
                    }
                    self.conversation_history.append(tool_message)
                    
                    final_response = await self.content_generator.process_tool_result(error_result, self.conversation_history)
                    # Update the conversation history in the orchestrator with the error response from the LLM
                    if hasattr(final_response, 'content') and final_response.content:
                        assistant_message = {
                            "role": "assistant",
                            "content": final_response.content
                        }
                        self.conversation_history.append(assistant_message)
            
            # Yield the final response after all tool calls are processed
            if final_response:
                yield getattr(final_response, 'content', str(final_response))
            else:
                # Fallback if no final response was generated
                yield "Tool processing completed."
        else:
            # If there are no tool calls, we can stream the initial response
            # For now, just yield the initial content if it exists
            yield getattr(response, 'content', str(response))