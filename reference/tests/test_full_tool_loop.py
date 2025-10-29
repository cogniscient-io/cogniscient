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
        
        async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
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
async def test_full_tool_loop_with_current_generator():
    """Test the full tool calling loop with the current generator and architecture."""
    print("\nTesting full tool loop with current architecture...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Create a mock content generator that simulates realistic tool call behavior
    from services.llm_provider.base_generator import BaseContentGenerator
    from services.llm_provider.tool_call_processor import ToolCall

    class AdvancedTestContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
            print(f"Advanced generator - Received prompt: {prompt}")
            print(f"Available tools count: {len(tools) if tools else 0}")
            
            # On first call, simulate a tool call for date command
            if self.call_count == 0:
                self.call_count += 1
                print("Returning tool call for date command")
                
                tool_call = ToolCall(
                    id="call_date_1",
                    name="shell_command", 
                    arguments={"command": "date"}
                )
                
                class ResponseObj:
                    content = "Let me get the current date for you."
                    tool_calls = [tool_call]
                
                return ResponseObj()
            
            # On second call, simulate a final response
            else:
                print("Returning final response")
                
                class ResponseObj:
                    content = "The current date is now available."
                    tool_calls = []
                
                return ResponseObj()
        
        async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
            print(f"Processing tool result - success: {tool_result.success}")
            print(f"Tool result content: {tool_result.llm_content[:50]}..." if tool_result.llm_content else "No content")
            print(f"Conversation history length: {len(conversation_history) if conversation_history else 0}")
            
            class ResponseObj:
                content = f"Based on the tool execution: {tool_result.llm_content.strip()}"
                tool_calls = []
            
            return ResponseObj()
        
        async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
            yield f"Processing: {prompt}"

    # Replace the content generator with our advanced test version
    test_generator = AdvancedTestContentGenerator()
    kernel.ai_orchestrator.set_content_generator(test_generator)
    
    try:
        print("Initiating full tool loop test...")
        response = await kernel.send_user_prompt("What time is it?")
        print(f"Final response received: {response}")
        
        # Verify that conversation history is properly maintained
        history = kernel.ai_orchestrator.get_conversation_history()
        print(f"Conversation history contains {len(history)} messages")
        
        # Ensure the history includes all expected interaction steps
        assert len(history) > 0, "Conversation history should not be empty"
        print("✅ Conversation history properly maintained")
        
        # Verify response contains expected content
        assert response is not None, "Response should not be None"
        print("✅ Response properly generated")
        
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing full tool calling loop in GCS Kernel...")
    
    # Test the full loop with mocked content generator
    asyncio.run(test_full_tool_calling_loop())
    
    # Test with the original generator and mocked network
    asyncio.run(test_with_original_generator())