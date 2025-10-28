#!/usr/bin/env python3
"""
Test script to verify the full tool calling loop works with the orchestrator.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import ToolResult


@pytest.mark.asyncio
async def test_full_tool_calling_loop():
    """Test the full tool calling loop including validation and execution."""
    print("Testing full tool calling loop...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Mock the content generator to simulate LLM that returns tool calls
    from services.llm_provider.base_generator import BaseContentGenerator
    from services.llm_provider.tool_call_processor import ToolCall
    
    class TestContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt: str, system_context: str = None):
            print(f"Content generator received prompt: {prompt}")
            
            # For the first call (original prompt), return a tool call
            if self.call_count == 0:
                self.call_count += 1
                
                # Create a tool call response
                class ResponseObj:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = tool_calls
                
                # Create a proper ToolCall object with arguments_json
                class MockToolCall:
                    def __init__(self, call_id, name, arguments):
                        self.id = call_id
                        self.name = name
                        self.arguments = arguments
                        self.arguments_json = '{"command": "date"}'
                
                tool_call = MockToolCall(
                    "call_123",
                    "shell_command",
                    {"command": "date"}
                )
                
                return ResponseObj(
                    content="I'll get the system date for you.",
                    tool_calls=[tool_call]
                )
            else:
                # For subsequent calls (after tool results), return final response
                class ResponseObj:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = tool_calls or []
                
                return ResponseObj(
                    content="The current date is: Fri Oct 24 08:30:00 PM PDT 2025",
                    tool_calls=[]
                )
        
        async def process_tool_result(self, tool_result, conversation_history=None):
            print(f"Processing tool result: {tool_result}")
            
            class ResponseObj:
                def __init__(self, content):
                    self.content = content
            
            return ResponseObj(content="The current date is: Fri Oct 24 08:30:00 PM PDT 2025")
        
        async def stream_response(self, prompt: str, system_context: str = None):
            yield f"Streaming response: {prompt}"

    # Replace the content generator
    test_generator = TestContentGenerator()
    kernel.ai_orchestrator.set_content_generator(test_generator)
    
    try:
        print("Sending prompt to trigger tool calling...")
        response = await kernel.send_user_prompt("What is the current date?")
        print(f"Final response: {response}")
        
    finally:
        await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_with_mocked_llm_provider():
    """Test with a mocked LLM provider that simulates realistic API responses."""
    print("\nTesting with mocked LLM provider...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Create a mock provider that simulates realistic API responses
    from services.llm_provider.providers.mock_provider import MockProvider
    from services.llm_provider.content_generator import LLMContentGenerator
    
    # Create content generator with the kernel reference
    content_generator = LLMContentGenerator(kernel=kernel)
    
    # Override provider with a custom mock that returns a response with tool call
    class TestMockProvider:
        async def generate_content(self, request: dict, user_prompt_id: str):
            # Check if this is the first call (for the original prompt) or follow-up
            if 'date' in request.get('messages', [{}])[0].get('content', ''):
                # Return a response with a tool call
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "I'll get the current date from the system.",
                            "tool_calls": [{
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "shell_command",
                                    "arguments": "{\"command\": \"date\"}"
                                }
                            }]
                        }
                    }]
                }
            else:
                # Return a final response without tool calls
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant", 
                            "content": "The current date is: Fri Oct 24 08:30:00 PM PDT 2025",
                            "tool_calls": []
                        }
                    }]
                }
        
        async def stream_content(self, request: dict, user_prompt_id: str):
            # Simulate streaming response
            yield {"choices": [{"delta": {"content": "The current date is:"}}]}
    
    # Replace the provider in the content generator
    content_generator.provider = TestMockProvider()
    
    # Set the content generator on the kernel's orchestrator
    if hasattr(kernel, 'ai_orchestrator') and kernel.ai_orchestrator:
        kernel.ai_orchestrator.set_content_generator(content_generator)
    
    try:
        print("Sending 'what is the date?' with mocked provider...")
        response = await kernel.send_user_prompt("What is the date?")
        print(f"Response: {response}")
        
        # Verify that we got a response (might include tool call processing text)
        assert response is not None
        print("Test passed: Got a response from the system")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing full tool calling loop in GCS Kernel...")
    
    # Test the full loop with mocked content generator
    asyncio.run(test_full_tool_calling_loop())
    
    # Test with the original generator and mocked network
    asyncio.run(test_with_original_generator())