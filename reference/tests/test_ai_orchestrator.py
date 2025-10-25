#!/usr/bin/env python3
"""
Test script to verify the AI orchestrator in the GCS Kernel.
"""
import asyncio
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig


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


async def test_kernel_with_mocked_llm():
    """Test kernel with a mock LLM to isolate the issue."""
    print("\nTesting kernel with mocked LLM...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Temporarily replace the AI orchestrator with one that has a mock content generator
    from unittest.mock import AsyncMock, MagicMock
    from services.llm_provider.base_generator import BaseContentGenerator
    from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
    
    class MockContentGenerator(BaseContentGenerator):
        async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
            from services.llm_provider.tool_call_processor import ToolCall
            
            # For specific prompts, return tool calls
            if "system status" in prompt.lower() or "date" in prompt.lower():
                # Create a mock tool call
                class MockResponse:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = tool_calls
                
                class MockToolCall:
                    def __init__(self):
                        self.name = "shell_command"
                        self.arguments = {"command": "date"}
                        self.parameters = {"command": "date"}
                        self.id = "call_123"
                
                return MockResponse(
                    content="I'll get the system date for you.",
                    tool_calls=[MockToolCall()]
                )
            else:
                class MockResponse:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = []
                
                return MockResponse(
                    content="Hello! How can I assist you today?",
                    tool_calls=[]
                )
        
        async def process_tool_result(self, tool_result):
            class MockResponse:
                def __init__(self, content):
                    self.content = content
            
            return MockResponse(content=f"Processed tool result: {tool_result.llm_content}")
        
        async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
            yield f"Streaming: {prompt}"

    # Replace the content generator with mock
    mock_generator = MockContentGenerator()
    kernel.ai_orchestrator.set_content_generator(mock_generator)
    
    # Now test with the mocked LLM
    try:
        print("Sending 'what is the date?' with mocked LLM...")
        response = await kernel.send_user_prompt("What is the date?")
        print(f"Response with mocked LLM: {response}")
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing GCS Kernel AI orchestrator...")
    
    # Test with real components
    asyncio.run(test_ai_orchestrator())
    
    # Test with mocked LLM to isolate issues
    asyncio.run(test_kernel_with_mocked_llm())