"""
Mock Implementations for Testing LLM Provider Components

This module provides centralized mock implementations of various LLM provider
components that can be used across different test modules to avoid duplication
and ensure consistency.

The MockProvider implementation has been moved to the main providers directory
where it can be enhanced and maintained as part of the core codebase.
This file now focuses on higher-level content generator mocks that work with
the pipeline and content generation layers.
"""

from typing import Any, Dict, AsyncIterator, List, TYPE_CHECKING
from services.llm_provider.base_generator import BaseContentGenerator
# Import the enhanced main MockProvider for use in tests
from services.llm_provider.providers.mock_provider import MockProvider as MainMockProvider

if TYPE_CHECKING:
    from gcs_kernel.models import PromptObject


class MockContentGenerator(BaseContentGenerator):
    """
    Standard mock implementation of BaseContentGenerator for testing purposes.
    
    This mock provides configurable behavior for different test scenarios.
    """
    
    def __init__(self, 
                 config: Dict[str, Any] = None,
                 response_content: str = "Mock response content",
                 tool_calls: List[Dict] = None,
                 should_stream: bool = True,
                 should_fail: bool = False,
                 fail_count: int = 0):
        """
        Initialize the mock content generator.
        
        Args:
            config: Configuration dictionary for testing
            response_content: Content to return in responses
            tool_calls: Mock tool calls to return (if any)
            should_stream: Whether to support streaming functionality
            should_fail: Whether this generator should fail for error testing
            fail_count: How many times to fail before succeeding
        """
        # Store the config as an attribute for testing
        self.config = config or {}
        # Set up any attributes needed for testing from the config
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout")
        self.max_retries = self.config.get("max_retries")
        
        # Mock response configuration
        self.response_content = response_content
        self.tool_calls = tool_calls or []
        self.should_stream = should_stream
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fail_count = 0
        self.generate_response_calls = []  # Track calls for testing
        self.stream_response_calls = []  # Track streaming calls for testing
        self.process_tool_result_calls = []  # Track calls for testing
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Mock implementation of generate_response taking a prompt object.
        Operates on the live prompt object in place.
        """
        # Track the call for testing purposes - extract content from prompt object
        self.generate_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Check if we should fail based on configuration (for error testing)
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        # Update the prompt object with result
        prompt_obj.result_content = f"{self.response_content} to: {prompt_obj.content}"
        prompt_obj.mark_completed(prompt_obj.result_content)
    
    async def process_tool_result(self, tool_result: Any, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of process_tool_result taking a prompt object.
        """
        # Track the call for testing purposes
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'prompt_obj': prompt_obj
        })
        
        # Update the prompt object with the result of processing the tool
        prompt_obj.result_content = f"Processed tool result: {tool_result}"
        prompt_obj.mark_completed(prompt_obj.result_content)
        
        return prompt_obj
    
    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Mock implementation of stream_response taking a prompt object.
        """
        # Track the call for testing purposes
        self.stream_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Stream the response content
        if self.should_stream:
            yield f"Streaming {self.response_content} to: {prompt_obj.content}"
        else:
            yield f"{self.response_content} to: {prompt_obj.content}"
    
    async def generate_response_from_conversation(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response_from_conversation taking a prompt object.
        """
        # Track the call for testing purposes
        last_user_message = None
        for msg in reversed(prompt_obj.conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Fail the first few calls if configured to do so
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        # Update the prompt object with response
        prompt_obj.result_content = f"{self.response_content} to conversation with {len(prompt_obj.conversation_history)} messages"
        prompt_obj.mark_completed(prompt_obj.result_content)
        
        return prompt_obj

    def process_streaming_chunks(self, chunks: list):
        """
        Mock implementation of process_streaming_chunks.
        """
        # For testing purposes, just return an empty response structure
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Mock processed content from chunks"
                },
                "finish_reason": "stop"
            }]
        }


class ToolCallingMockContentGenerator(MockContentGenerator):
    """
    Mock content generator that specifically returns tool calls for testing
    tool execution flows.
    """
    
    def __init__(self, 
                 config: Dict[str, Any] = None,
                 tool_calls: List[Dict] = None,
                 response_content: str = "I'll help you with that using a tool."):
        """
        Initialize the tool-calling mock content generator.
        
        Args:
            config: Configuration dictionary for testing
            tool_calls: Mock tool calls to return
            response_content: Content to return when no tools are called
        """
        super().__init__(
            config=config,
            response_content=response_content,
            tool_calls=tool_calls or []
        )
    
    async def process_tool_result(self, tool_result, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Override process_tool_result to return a natural response incorporating the tool result.
        """
        # Track the call for testing purposes
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'prompt_obj': prompt_obj
        })
        
        # Create a natural response that incorporates the tool result
        # If the tool result contains time/date information, create a relevant response
        tool_content = getattr(tool_result, 'llm_content', 'No content provided')
        
        # Determine the type of response based on the tool result content
        tool_content_lower = tool_content.lower()
        if "time" in tool_content_lower or "date" in tool_content_lower or \
           any(time_indicator in tool_content_lower for time_indicator in ["utc", "gmt", "am", "pm", 
             ":00", ":15", ":30", ":45", ":60"]):
            response_content = f"The current time is: {tool_content.strip()}"
        else:
            response_content = f"Based on the tool results: {tool_content.strip()}"
        
        # Update the prompt object with the response
        prompt_obj.result_content = response_content
        prompt_obj.mark_completed(response_content)
        
        return prompt_obj
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Mock implementation that returns tool calls for specific prompts or responses based on tool results.
        Operates on the live prompt object in place.
        """
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Check if we should fail based on configuration (for error testing)
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")

        # Check if there are already tool results in the conversation history to respond to
        has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)
        
        if has_tool_result:
            # Create final response when tool results are present
            # Find the tool result content to include in the response
            tool_content = None
            for msg in reversed(prompt_obj.conversation_history):  # Look from most recent backwards
                if msg.get("role") == "tool":
                    tool_content = msg.get("content", "")
                    break
            
            if tool_content:
                # Determine the type of response based on the tool result content
                tool_content_lower = tool_content.lower()
                if "time" in tool_content_lower or "date" in tool_content_lower or \
                   any(time_indicator in tool_content_lower for time_indicator in ["utc", "gmt", "am", "pm", 
                     ":00", ":15", ":30", ":45", ":60"]):
                    response_content = f"The current time is: {tool_content.strip()}"
                else:
                    response_content = f"Based on the tool results: {tool_content.strip()}"
                
                prompt_obj.result_content = response_content
            else:
                # Fallback response if we can't find the tool content
                prompt_obj.result_content = "Based on the tool results, I've completed your request."
        elif "system status" in prompt_obj.content.lower() or "date" in prompt_obj.content.lower() or "time" in prompt_obj.content.lower():
            # Create a mock tool call with actual tool call structure for specific prompts
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.parameters = {"command": "date"}
                    import json
                    self.arguments = self.parameters  # Use parameters directly as arguments
                    self.arguments_json = json.dumps(self.parameters)
                    
            # Update the prompt object with content and tool calls
            prompt_obj.result_content = "I'll get the system date for you."
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": "shell_command", 
                    "arguments": {"command": "date"}
                }
            })
        else:
            # Update the prompt object with regular content
            prompt_obj.result_content = self.response_content
        
        prompt_obj.mark_completed(prompt_obj.result_content)

    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Mock implementation of stream_response that handles tool calls in streaming context.
        """
        # Track for testing purposes
        self.last_stream_prompt = prompt_obj.content
        
        # Check if there are already tool results in the conversation history to respond to
        has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)
        
        if has_tool_result:
            # Create final response when tool results are present
            # Find the tool result content to include in the response
            tool_content = None
            for msg in reversed(prompt_obj.conversation_history):  # Look from most recent backwards
                if msg.get("role") == "tool":
                    tool_content = msg.get("content", "")
                    break
            
            if tool_content:
                # Determine the type of response based on the tool result content
                tool_content_lower = tool_content.lower()
                if "time" in tool_content_lower or "date" in tool_content_lower or \
                   any(time_indicator in tool_content_lower for time_indicator in ["utc", "gmt", "am", "pm", 
                     ":00", ":15", ":30", ":45", ":60"]):
                    response_content = f"The current time is: {tool_content.strip()}"
                else:
                    response_content = f"Based on the tool results: {tool_content.strip()}"
                
                # Yield the response content in chunks
                chunk_size = len(response_content) // 3 if len(response_content) > 3 else len(response_content)
                for i in range(0, len(response_content), chunk_size):
                    yield response_content[i:i+chunk_size]
                
                prompt_obj.result_content = response_content
            else:
                # Fallback response if we can't find the tool content
                fallback_content = "Based on the tool results, I've completed your request."
                prompt_obj.result_content = fallback_content
                chunk_size = len(fallback_content) // 3 if len(fallback_content) > 3 else len(fallback_content)
                for i in range(0, len(fallback_content), chunk_size):
                    yield fallback_content[i:i+chunk_size]
        elif "system status" in prompt_obj.content.lower() or "date" in prompt_obj.content.lower() or "time" in prompt_obj.content.lower():
            # For specific prompts, initiate tool calls
            response_content = "I'll get the system date for you."
            
            # Add tool call to the prompt object for the turn manager to process
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": "shell_command", 
                    "arguments": {"command": "date"}
                }
            })
            
            # Yield the initial response in chunks
            chunk_size = len(response_content) // 3 if len(response_content) > 3 else len(response_content)
            for i in range(0, len(response_content), chunk_size):
                yield response_content[i:i+chunk_size]
            
            # Update result content to indicate tool was called
            prompt_obj.result_content = response_content
        else:
            # Stream the default response content
            response_content = "I'll help you with that using a tool."  # Use the default response
            prompt_obj.result_content = response_content
            
            # Stream in chunks
            chunk_size = len(response_content) // 3 if len(response_content) > 3 else len(response_content)
            for i in range(0, len(response_content), chunk_size):
                yield response_content[i:i+chunk_size]
        
        # Mark as completed at the end
        prompt_obj.mark_completed(prompt_obj.result_content)

    async def generate_response_from_conversation(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation that returns tool calls for specific conversation patterns.
        """
        # Check for user messages in conversation history
        last_user_message = None
        for msg in reversed(prompt_obj.conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Check if we should fail based on configuration (for error testing)
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")

        # For specific prompts, return tool calls
        if last_user_message and ("system status" in last_user_message.lower() or 
                                  "date" in last_user_message.lower() or 
                                  "time" in last_user_message.lower()):
            # Create a mock tool call with proper structure
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.parameters = {"command": "date"}
                    import json
                    self.arguments = self.parameters  # Use parameters directly as arguments
                    self.arguments_json = json.dumps(self.parameters)

            # Update the prompt object with content and tool call
            prompt_obj.result_content = "I'll get the system date for you."
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": "shell_command", 
                    "arguments": {"command": "date"}
                }
            })
        else:
            # Check if there's a tool result in the conversation history to respond to
            has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)
            if has_tool_result:
                # Create final response when tool results are present
                # Find the tool result content to include in the response
                for msg in prompt_obj.conversation_history:
                    if msg.get("role") == "tool":
                        tool_content = msg.get("content", "")
                        prompt_obj.result_content = f"Based on the tool results: {tool_content}"
                        break
                else:
                    # Fallback response if we can't find the tool content
                    prompt_obj.result_content = "Based on the tool results, I've completed your request."
            else:
                prompt_obj.result_content = self.response_content

        prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj