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
        
        async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
            print(f"Content generator received prompt: {prompt}")
            print(f"Available tools: {tools}")
            
            # For the first call (original prompt), return a tool call
            if self.call_count == 0:
                self.call_count += 1
                
                # Create a tool call response
                class ResponseObj:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = tool_calls
                
                # Create a proper ToolCall object
                tool_call = ToolCall(
                    id="call_123",
                    name="shell_command",
                    arguments={"command": "date"}
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
        
        async def process_tool_result(self, tool_result):
            print(f"Processing tool result: {tool_result}")
            
            class ResponseObj:
                def __init__(self, content):
                    self.content = content
            
            return ResponseObj(content="The current date is: Fri Oct 24 08:30:00 PM PDT 2025")
        
        async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
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
async def test_with_original_generator():
    """Test with the original content generator to see if the issue is elsewhere."""
    print("\nTesting with original LLM provider setup...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Use the actual LLM content generator but intercept network calls
    with patch('httpx.AsyncClient.post') as mock_post:
        # Mock a response that includes a tool call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_123",
                        "function": {
                            "name": "shell_command",
                            "arguments": "{\"command\": \"date\"}"
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        try:
            print("Sending 'what is the date?' with network call mocked...")
            response = await kernel.send_user_prompt("What is the date?")
            print(f"Response: {response}")
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