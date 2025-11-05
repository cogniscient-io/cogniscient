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
    from gcs_kernel.tool_call_model import ToolCall
    
    class TestContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt_obj: 'PromptObject') -> None:
            print(f"Content generator received prompt: {prompt_obj.content}")
            print(f"Available tools: {getattr(prompt_obj, 'custom_tools', None)}")
            
            # For the first call (original prompt), return a tool call
            if self.call_count == 0:
                self.call_count += 1
                
                # Create a proper ToolCall object
                tool_call = ToolCall(
                    id="call_123",
                    function={
                        "name": "shell_command",
                        "arguments": '{"command": "date"}'
                    }
                )
                
                # Update the prompt object with content and tool calls
                prompt_obj.result_content = "I'll get the system date for you."
                prompt_obj.add_tool_call({
                    "id": tool_call.id,
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments_json
                    }
                })
            else:
                # For subsequent calls (after tool results), return final response
                prompt_obj.result_content = "The current date is: Fri Oct 24 08:30:00 PM PDT 2025"
                prompt_obj.mark_completed(prompt_obj.result_content)
        
        async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
            print(f"Processing tool result: {tool_result}")
            
            class ResponseObj:
                def __init__(self, content):
                    self.content = content
            
            return ResponseObj(content="The current date is: Fri Oct 24 08:30:00 PM PDT 2025")
        
        async def stream_response(self, prompt_obj: 'PromptObject'):
            yield f"Streaming response: {prompt_obj.content}"
        
        async def generate_response_from_conversation(self, conversation_history: list, tools: list = None):
            # For this test, just return the same as generate_response
            # but with the last user message from the conversation history
            last_user_message = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break

            class ResponseObj:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls or []

            # If we have a tool result in the conversation, return final response
            has_tool_result = any(msg.get("role") == "tool" for msg in conversation_history)
            if has_tool_result:
                return ResponseObj(
                    content="The current date is: Fri Oct 24 08:30:00 PM PDT 2025",
                    tool_calls=[]
                )
            else:
                # Otherwise, return a tool call for the date command
                tool_call = ToolCall(
                    id="call_123",
                    function={
                        "name": "shell_command",
                        "arguments": '{"command": "date"}'
                    }
                )
                return ResponseObj(
                    content="I'll get the system date for you.",
                    tool_calls=[tool_call]
                )

    # Replace the content generator
    test_generator = TestContentGenerator()
    kernel.ai_orchestrator.set_content_generator(test_generator)
    
    try:
        print("Sending prompt to trigger tool calling...")
        response = await kernel.submit_prompt("What is the current date?")
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
    from gcs_kernel.tool_call_model import ToolCall

    class AdvancedTestContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt_obj):
            print(f"Advanced generator - Received prompt: {prompt_obj.content}")
            # Available tools are part of the prompt_obj now
            tools = getattr(prompt_obj, 'custom_tools', None)
            tools_count = len(tools) if tools else 0
            print(f"Available tools count: {tools_count}")
            
            # On first call, simulate a tool call for date command
            if self.call_count == 0:
                self.call_count += 1
                print("Returning tool call for date command")
                
                tool_call = ToolCall(
                    id="call_date_1",
                    function={
                        "name": "shell_command",
                        "arguments": '{"command": "date"}'
                    }
                )
                
                # Update the prompt object with tool calls (following new architecture)
                prompt_obj.result_content = "Let me get the current date for you."
                prompt_obj.add_tool_call({
                    "id": tool_call.id,
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments_json
                    }
                })
                
                return prompt_obj
            
            # On second call, simulate a final response
            else:
                print("Returning final response")
                
                # Update the prompt object with final content (following new architecture)
                prompt_obj.result_content = "The current date is now available."
                
                return prompt_obj
        
        async def process_tool_result(self, tool_result, prompt_obj):
            print(f"Processing tool result - success: {tool_result.success}")
            print(f"Tool result content: {tool_result.llm_content[:50]}..." if tool_result.llm_content else "No content")
            print(f"Conversation history length: {len(prompt_obj.conversation_history) if prompt_obj.conversation_history else 0}")
            
            # Update the prompt object with the processed result
            prompt_obj.result_content = f"Based on the tool execution: {tool_result.llm_content.strip()}"
            
            return prompt_obj
        
        async def stream_response(self, prompt_obj):
            yield f"Processing: {prompt_obj.content}"
        
        # This method may not be used in the new architecture, but keeping it for compatibility
        # In the new architecture, generate_response should handle everything with PromptObject
        pass

    # Replace the content generator with our advanced test version
    test_generator = AdvancedTestContentGenerator()
    kernel.ai_orchestrator.set_content_generator(test_generator)
    
    try:
        print("Initiating full tool loop test...")
        response = await kernel.submit_prompt("What time is it?")
        print(f"Final response received: {response}")
        
        # Verify response contains expected content
        assert response is not None, "Response should not be None"
        print("✅ Response properly generated")
        
        # Verify the kernel is still functional and properly configured
        assert hasattr(kernel, 'tool_execution_manager'), "ToolExecutionManager should be available"
        print("✅ ToolExecutionManager properly configured")
        
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing full tool calling loop in GCS Kernel...")
    
    # Test the full loop with mocked content generator
    asyncio.run(test_full_tool_calling_loop())