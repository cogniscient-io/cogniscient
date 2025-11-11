"""
Mock Provider for GCS Kernel LLM Provider Backend Integration Testing.

This module implements a mock provider that simulates an LLM response for testing purposes.
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from gcs_kernel.models import PromptObject
from services.llm_provider.providers.base_provider import BaseProvider


class MockProvider(BaseProvider):
    """
    Mock provider implementation for integration testing with configurable responses.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the mock provider with configuration.

        Args:
            config: Dictionary containing provider configuration
                    Additional options:
                    - response_content: Default response content
                    - response_callback: Function to generate response based on prompt
                    - status_code: Default status code to return (default: 200)
                    - should_error: Whether to simulate an error response (default: False)
                    - response_delay: Delay in seconds before returning response (default: 0.1)
                    - tool_calls: List of tool calls to include in response
        """
        # Call the parent constructor
        super().__init__(config)

        # Initialize a converter for this provider
        from .openai_converter import OpenAIConverter
        self._converter = OpenAIConverter(self.model)

        # Store configuration options for mock behavior
        self.response_content = config.get("response_content", "Hello, this is a test response from the LLM!")
        self.response_callback = config.get("response_callback")  # Function to generate response
        self.status_code = config.get("status_code", 200)
        self.should_error = config.get("should_error", False)
        self.response_delay = config.get("response_delay", 0.1)
        self.tool_calls = config.get("tool_calls", [])

        # Add counter for tracking response sequence to prevent infinite loops
        self._response_counter = 0
        self._max_responses = config.get("max_responses", 3)  # Default to 3 max responses

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
            A mock client with configurable behavior
        """
        class MockClient:
            def __init__(self, provider):
                self.provider = provider

            async def post(self, url, json=None, headers=None):
                # Simulate an API response with configurable behavior
                class MockResponse:
                    def __init__(self, provider):
                        self.provider = provider
                        self._json_data = self._build_response_data(json)

                    def _build_response_data(self, json_data):
                        # If a response callback is provided, use it to generate response
                        if self.provider.response_callback and callable(self.provider.response_callback):
                            # Pass the request JSON to the callback for complex response generation
                            content = self.provider.response_callback(json_data)
                        else:
                            # Otherwise use default content
                            content = self.provider.response_content

                        # Build the response with potential tool calls
                        response_data = {
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": content,
                                        "tool_calls": []  # Initially empty, may be filled below
                                    }
                                }
                            ]
                        }

                        # Increment response counter to prevent infinite loops
                        self.provider._response_counter += 1

                        # Check for tool results in conversation history for multi-turn responses
                        tool_results = []
                        has_configured_tool_calls = bool(self.provider.tool_calls)
                        if json_data and "messages" in json_data:
                            tool_results = [msg for msg in json_data["messages"] if msg.get("role") == "tool"]

                        # Add request-specific response for more realistic testing
                        if json_data and "messages" in json_data:
                            last_message = json_data["messages"][-1]["content"] if json_data["messages"] else ""

                            # Check if we should return configured tool calls (not on subsequent responses to prevent loops)
                            should_return_configured_tool_calls = (
                                has_configured_tool_calls and
                                self.provider._response_counter <= self.provider._max_responses and
                                not tool_results  # Don't return tool calls if responding to tool results
                            )

                            # Prioritize configured tool calls over heuristic behaviors
                            if should_return_configured_tool_calls:
                                # Return configured tool calls (highest priority)
                                response_data["choices"][0]["message"]["tool_calls"] = self.provider.tool_calls
                                # Use configured content or default content
                                response_data["choices"][0]["message"]["content"] = self.provider.response_content
                            elif tool_results and self.provider._response_counter <= self.provider._max_responses:
                                # Respond to tool results
                                latest_tool_result = tool_results[-1]
                                tool_content = latest_tool_result.get("content", "")

                                if "date" in tool_content.lower() or "time" in tool_content.lower():
                                    response_data["choices"][0]["message"]["content"] = f"Based on the date tool result, the current time is: {tool_content}"
                                elif "uptime" in tool_content.lower():
                                    response_data["choices"][0]["message"]["content"] = f"Based on the uptime tool result: {tool_content}"
                                else:
                                    response_data["choices"][0]["message"]["content"] = f"Based on the tool result: {tool_content}"

                                # Don't return tool calls when responding to tool results
                                response_data["choices"][0]["message"]["tool_calls"] = []
                            elif "time" in last_message.lower() or "date" in last_message.lower():
                                response_data["choices"][0]["message"]["content"] = "The current time is: 2025-01-24 12:34:56 UTC"
                            elif "error" in last_message.lower():
                                response_data["choices"][0]["message"]["content"] = "Simulated error response"
                            else:
                                # Default response - use original content
                                response_data["choices"][0]["message"]["tool_calls"] = []
                        else:
                            # No json data - use configured tool calls if available
                            if has_configured_tool_calls and self.provider._response_counter <= self.provider._max_responses:
                                response_data["choices"][0]["message"]["tool_calls"] = self.provider.tool_calls
                                response_data["choices"][0]["message"]["content"] = self.provider.response_content
                            else:
                                response_data["choices"][0]["message"]["tool_calls"] = []

                        return response_data

                    def json(self):
                        """Synchronous JSON method like real httpx response."""
                        return self._json_data

                    @property
                    def status_code(self):
                        """Status code property like real httpx response."""
                        return self.provider.status_code

                # Simulate network delay
                await asyncio.sleep(self.provider.response_delay)

                # If configured to simulate an error, return an error response
                if self.provider.should_error:
                    class ErrorResponse:
                        def json(self):
                            return {
                                "error": {
                                    "message": "Simulated error response",
                                    "type": "server_error"
                                }
                            }

                        @property
                        def status_code(self):
                            return 500  # Simulate server error

                    return ErrorResponse()

                return MockResponse(self.provider)

            def stream(self, method, url, json=None, headers=None):
                """Mock stream method to return a streaming response."""
                # Create a streaming response that mimics httpx stream behavior
                class MockStream:
                    def __init__(self, provider, json_request):
                        self.provider = provider
                        self.json_request = json_request
                        self.is_streaming = True
                        self._content_chunks = self._generate_content_chunks()

                    def _generate_content_chunks(self):
                        """Generate streaming chunks based on the provider's response."""
                        # Get the complete response that would come from non-streaming request
                        # This ensures consistency with the non-streaming behavior
                        if self.provider.response_callback and callable(self.provider.response_callback):
                            content = self.provider.response_callback(self.json_request)
                        else:
                            content = self.provider.response_content

                        # Split content into chunks for streaming simulation
                        chunks = []
                        for i in range(0, len(content), 5):  # Create 5-character chunks
                            chunk = content[i:i+5]
                            if chunk:
                                chunks.append({
                                    "choices": [{
                                        "delta": {"content": chunk},
                                        "index": 0,
                                        "finish_reason": None
                                    }]
                                })

                        # Add finish chunk
                        chunks.append({
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop"
                            }]
                        })

                        # If there are tool calls, add them as well
                        if self.provider.tool_calls:
                            for i, tool_call in enumerate(self.provider.tool_calls):
                                chunks.append({
                                    "choices": [{
                                        "delta": {
                                            "tool_calls": [{
                                                "index": i,  # Index for the tool call
                                                "id": tool_call.get("id", f"call_{i}"),
                                                "function": {
                                                    "name": tool_call.get("function", {}).get("name", ""),
                                                    "arguments": tool_call.get("function", {}).get("arguments", "{}")
                                                },
                                                "type": tool_call.get("type", "function")
                                            }]
                                        },
                                        "index": 0,
                                        "finish_reason": "tool_calls"
                                    }]
                                })

                        return chunks

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        pass

                    async def aiter_lines(self):
                        """Async iterator for streaming lines, similar to httpx."""
                        for chunk in self._content_chunks:
                            import json
                            yield f"data: {json.dumps(chunk)}"
                        # Yield the DONE signal
                        yield "data: [DONE]"

                return MockStream(self.provider, json)

        return MockClient(self)

    def build_request(self, prompt_obj: 'PromptObject') -> Dict[str, Any]:
        """
        Build a mock request from a PromptObject.

        Args:
            prompt_obj: The PromptObject containing all necessary information

        Returns:
            Mock request structure in OpenAI-compatible format
        """
        # Create the mock request from the prompt object's fields
        messages = prompt_obj.conversation_history + [{"role": prompt_obj.role, "content": prompt_obj.content}]

        openai_request = {
            "messages": messages,
            "model": self.model
        }

        # Add optional parameters if present in the prompt object
        if prompt_obj.max_tokens is not None:
            openai_request["max_tokens"] = prompt_obj.max_tokens
        if prompt_obj.temperature:
            openai_request["temperature"] = prompt_obj.temperature

        # Add tools if specified in the prompt object
        if prompt_obj.tool_policy and prompt_obj.tool_policy.value != "none":
            if prompt_obj.custom_tools:
                openai_request["tools"] = prompt_obj.custom_tools

        # Add the user ID for tracking
        if prompt_obj.user_id:
            openai_request["user"] = prompt_obj.user_id
        elif prompt_obj.prompt_id:
            # Use prompt_id if user_id is not available
            openai_request["user"] = prompt_obj.prompt_id

        # Add other fields that may be relevant from the prompt object
        if prompt_obj.streaming_enabled:
            openai_request["stream"] = True

        # Add prompt ID for tracking
        openai_request["user_prompt_id"] = prompt_obj.prompt_id

        # Convert using the converter
        openai_request = self.converter.convert_kernel_request_to_provider(openai_request)

        return openai_request

    def set_response_content(self, content: str):
        """
        Set the default response content for this mock provider.

        Args:
            content: The content to return in responses
        """
        self.response_content = content

    def set_response_callback(self, callback: Callable[[Dict[str, Any]], str]):
        """
        Set a callback function to generate responses based on the request.

        Args:
            callback: A function that takes the request JSON and returns a response string
        """
        self.response_callback = callback

    def set_tool_calls(self, tool_calls: list):
        """
        Set the tool calls to include in responses.

        Args:
            tool_calls: List of tool call dictionaries to include
        """
        self.tool_calls = tool_calls

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model (mock implementation).

        Args:
            model_name: Name of the model to get information for

        Returns:
            Dictionary containing model information including capabilities
        """
        # For mock provider, return static information with intelligent defaults based on model name
        if 'gpt-4-turbo' in model_name or 'gpt-4o' in model_name:
            max_context_length = 128000
        elif 'gpt-4' in model_name:
            max_context_length = 128000
        elif 'gpt-3.5-turbo' in model_name:
            max_context_length = 16384
        else:
            max_context_length = 4096  # Default fallback
        
        # For mock provider, return static information
        return {
            'id': model_name,
            'object': 'model',
            'created': 1677610602,  # Mock creation timestamp
            'owned_by': 'organization-owner',
            'max_context_length': max_context_length,
            'capabilities': {
                'supports_tools': True,
                'supports_streaming': True
            }
        }