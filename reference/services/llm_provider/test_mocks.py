"""
Mock Implementations for Testing LLM Provider Components

This module provides centralized mock implementations of various LLM provider
components that can be used across different test modules to avoid duplication
and ensure consistency.
"""

import asyncio
from typing import Any, Dict, AsyncIterator, List, Optional
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.providers.base_provider import BaseProvider
from services.llm_provider.providers.openai_converter import OpenAIConverter


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
        self.process_tool_result_calls = []  # Track calls for testing
    
    async def generate_response(self, prompt: str, system_context: str = None, prompt_id: str = None, tools: list = None) -> Any:
        """
        Mock implementation of generate_response.
        Supports both old and new signatures for compatibility.
        """
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'prompt_id': prompt_id,
            'tools': tools
        })
        
        # Check if we should fail based on configuration (for error testing)
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        return ResponseObj(
            content=f"{self.response_content} to: {prompt}",
            tool_calls=self.tool_calls
        )
    
    async def process_tool_result(self, tool_result: Any, conversation_history: list = None, prompt_id: str = None, available_tools: list = None) -> Any:
        """
        Mock implementation of process_tool_result.
        Supports both old and new signatures for compatibility.
        """
        # Track the call for testing purposes
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'prompt_id': prompt_id,
            'available_tools': available_tools
        })
        
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed tool result: {tool_result}")
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None) -> AsyncIterator[str]:
        """
        Mock implementation of stream_response.
        Compatible with both old and new signatures.
        """
        # Track for testing purposes
        self.last_stream_prompt = prompt
        
        if self.should_stream:
            yield f"Streaming {self.response_content} to: {prompt}"
        else:
            yield f"{self.response_content} to: {prompt}"
    
    async def generate_response_from_conversation(self, conversation_history: list, prompt_id: str = None, tools: list = None) -> Any:
        """
        Mock implementation of generate_response_from_conversation.
        Supports both old and new signatures for compatibility.
        """
        # Track the call for testing purposes (similar to generate_response)
        last_user_message = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_id,
            'tools': tools
        })
        
        # Fail the first few calls if configured to do so
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        return ResponseObj(
            content=f"{self.response_content} to conversation with {len(conversation_history)} messages",
            tool_calls=self.tool_calls
        )


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
    
    async def process_tool_result(self, tool_result, conversation_history=None, prompt_id: str = None, available_tools: list = None) -> Any:
        """
        Override process_tool_result to return a natural response incorporating the tool result.
        """
        class ResponseObj:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls or []

        # Track the call for testing purposes
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'prompt_id': prompt_id,
            'available_tools': available_tools
        })
        
        # Create a natural response that incorporates the tool result
        # If the tool result contains time/date information, create a relevant response
        tool_content = getattr(tool_result, 'llm_content', 'No content provided')
        
        # Determine the type of response based on the tool result content
        tool_content_lower = tool_content.lower()
        if "time" in tool_content_lower or "date" in tool_content_lower or \
           any(time_indicator in tool_content_lower for time_indicator in ["utc", "gmt", "am", "pm", 
             ":00", ":15", ":30", ":45", ":60"]):
            return ResponseObj(
                content=f"The current time is: {tool_content.strip()}",
                tool_calls=[]  # No more tool calls needed
            )
        else:
            return ResponseObj(
                content=f"Based on the tool results: {tool_content.strip()}",
                tool_calls=[]  # No more tool calls needed
            )
    
    async def generate_response(self, prompt: str, system_context: str = None, prompt_id: str = None, tools: list = None) -> Any:
        """
        Mock implementation that returns tool calls for specific prompts.
        Supports both old and new signatures for compatibility.
        """
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'prompt_id': prompt_id,
            'tools': tools
        })
        
        # Check if we should fail based on configuration (for error testing)
        if self.should_fail and self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # For specific prompts, return tool calls
        if "system status" in prompt.lower() or "date" in prompt.lower() or "time" in prompt.lower():
            # Create a mock tool call with actual tool call structure
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.parameters = {"command": "date"}
                    import json
                    self.arguments = self.parameters  # Use parameters directly as arguments
                    self.arguments_json = json.dumps(self.parameters)
            
            return ResponseObj(
                content="I'll get the system date for you.",
                tool_calls=[MockToolCall()]
            )
        else:
            return ResponseObj(
                content=self.response_content,
                tool_calls=self.tool_calls
            )
    
    async def generate_response_from_conversation(self, conversation_history: list, prompt_id: str = None, tools: list = None) -> Any:
        """
        Mock implementation that returns tool calls for specific conversation patterns.
        Supports both old and new signatures for compatibility.
        """
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # Check for user messages in conversation history
        last_user_message = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_id,
            'tools': tools
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

            return ResponseObj(
                content="I'll get the system date for you.",
                tool_calls=[MockToolCall()]
            )
        else:
            # Check if there's a tool result in the conversation history to respond to
            has_tool_result = any(msg.get("role") == "tool" for msg in conversation_history)
            if has_tool_result:
                # Create final response when tool results are present
                # Find the tool result content to include in the response
                for msg in conversation_history:
                    if msg.get("role") == "tool":
                        tool_content = msg.get("content", "")
                        return ResponseObj(
                            content=f"Based on the tool results: {tool_content}",
                            tool_calls=[]
                        )
                
                # Fallback response if we can't find the tool content
                return ResponseObj(
                    content="Based on the tool results, I've completed your request.",
                    tool_calls=[]
                )
            else:
                return ResponseObj(
                    content=self.response_content,
                    tool_calls=self.tool_calls
                )


class MockProvider(BaseProvider):
    """
    Mock provider implementation for integration testing.
    (This is a copy of the existing mock provider, to keep all mocks together)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the mock provider with configuration.
        
        Args:
            config: Dictionary containing provider configuration
        """
        # Call the parent constructor
        super().__init__(config)
        
        # Initialize a converter for this provider
        self._converter = OpenAIConverter(self.model)
    
    @property
    def converter(self):
        """
        The converter for this mock provider to transform data between kernel and provider formats.
        This returns an OpenAI-compatible converter suitable for testing.
        """
        return self._converter
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for mock API requests.

        Returns:
            Dictionary of headers for mock API requests
        """
        return {"Content-Type": "application/json"}

    def build_client(self):
        """
        Build a mock client that doesn't make actual API calls.

        Returns:
            A mock client (simulated object)
        """
        class MockClient:
            async def post(self, url, json=None, headers=None):
                # Simulate an API response
                class MockResponse:
                    async def json(self):
                        # Return a mock response that includes a "hello world" message
                        return {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": "Hello, this is a test response from the LLM!"
                                    }
                                }
                            ]
                        }
                    
                    @property
                    def status_code(self):
                        return 200
                
                await asyncio.sleep(0.1)  # Simulate network delay
                return MockResponse()
        
        return MockClient()
    
    def build_request(self, request: Dict[str, Any], user_prompt_id: str) -> Dict[str, Any]:
        """
        Convert and build a mock request based on the input.
        
        Args:
            request: The base request in kernel format
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Mock request structure in OpenAI-compatible format
        """
        # Convert the kernel format request to OpenAI format (for consistency with testing)
        openai_request = self.converter.convert_kernel_request_to_provider(request)
        
        # Add user prompt ID for tracking
        openai_request["user_prompt_id"] = user_prompt_id
        return openai_request