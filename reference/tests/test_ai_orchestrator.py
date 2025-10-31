#!/usr/bin/env python3
"""
Test script to verify the AI orchestrator in the GCS Kernel with new architecture.
"""
import asyncio
import pytest
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


@pytest.mark.asyncio
async def test_ai_orchestrator():
    """Test the AI orchestrator directly."""
    print("Testing AI orchestrator...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    try:
        # Try to send a simple prompt directly to the kernel
        print("Sending 'hello' prompt to kernel...")
        response = await kernel.send_user_prompt("Hello")
        print(f"Response to 'hello': {response}")
        
        print("\nSending 'what is the current date?' prompt to kernel...")
        response = await kernel.send_user_prompt("What is the current date?")
        print(f"Response to 'what is the current date?': {response}")
        
        print("\nSending 'get system status' prompt to kernel...")
        response = await kernel.send_user_prompt("Get system status")
        print(f"Response to 'get system status': {response}")
        
    finally:
        # Clean up
        await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_kernel_with_mocked_llm():
    """Test kernel with a mock LLM to isolate the issue."""
    print("\nTesting kernel with mocked LLM...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Temporarily replace the content generator with a mock
    from services.llm_provider.test_mocks import ToolCallingMockContentGenerator
    
    # Create a mock content generator that returns tool calls for specific prompts
    class CustomMockContentGenerator(ToolCallingMockContentGenerator):
        async def process_tool_result(self, tool_result, conversation_history=None, prompt_id: str = None):
            class MockResponse:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []

            return MockResponse(content=f"Processed tool result: {tool_result.llm_content}")

    # Replace the content generator with mock
    mock_generator = CustomMockContentGenerator()
    kernel.ai_orchestrator.set_content_generator(mock_generator)
    
    # Now test with the mocked LLM
    try:
        print("Sending 'what is the date?' with mocked LLM...")
        response = await kernel.send_user_prompt("What is the date?")
        print(f"Response with mocked LLM: {response}")
        
        print("Sending 'hello' with mocked LLM...")
        response = await kernel.send_user_prompt("Hello")
        print(f"Response with mocked LLM: {response}")
        
    finally:
        await kernel._cleanup_components()


@pytest.mark.asyncio
async def test_turn_based_interaction():
    """Test the new turn-based interaction pattern."""
    print("\nTesting turn-based interaction...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Test with the turn-based approach
    try:
        print("Testing streaming interaction...")
        response_chunks = []
        
        async for chunk in kernel.ai_orchestrator.stream_ai_interaction("Hello"):
            response_chunks.append(chunk)
            
        full_response = "".join(response_chunks)
        print(f"Streaming response: {full_response}")
        
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing GCS Kernel AI orchestrator with new architecture...")
    
    # Test with real components
    asyncio.run(test_ai_orchestrator())
    
    # Test with mocked LLM to isolate issues
    asyncio.run(test_kernel_with_mocked_llm())
    
    # Test turn-based interaction
    asyncio.run(test_turn_based_interaction())