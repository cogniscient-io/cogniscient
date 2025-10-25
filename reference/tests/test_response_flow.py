#!/usr/bin/env python3
"""
Test script to trace the complete response flow from kernel to CLI.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import ToolResult
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.tool_call_processor import ToolCall


async def test_complete_flow_with_tracing():
    """Test the complete flow from kernel to CLI with detailed tracing."""
    print("Testing complete response flow with tracing...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Mock the content generator to simulate full LLM interaction
    class TracingContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
            print(f"Content generator received prompt: '{prompt}'")
            print(f"System context provided: {system_context is not None}")
            print(f"Number of tools provided: {len(tools) if tools else 0}")
            
            self.call_count += 1
            
            if self.call_count == 1:  # First call - original prompt
                print("  -> Returning tool call for first call")
                
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
                    content="Getting the system date for you...",
                    tool_calls=[tool_call]
                )
            else:  # Subsequent calls - after tool results
                print("  -> Returning final response for subsequent call")
                
                class ResponseObj:
                    def __init__(self, content, tool_calls):
                        self.content = content
                        self.tool_calls = tool_calls or []
                
                return ResponseObj(
                    content="The system date is: Fri Oct 24 08:50:00 PM PDT 2025",
                    tool_calls=[]
                )
        
        async def process_tool_result(self, tool_result):
            print(f"process_tool_result called with: {tool_result.return_display}")
            
            class ResponseObj:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []
            
            return ResponseObj(
                content="I have retrieved the date for you.",
                tool_calls=[]
            )
        
        async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
            print(f"Streaming response for prompt: '{prompt}'")
            yield f"Streaming response to: {prompt}"

    # Replace the content generator
    tracing_generator = TracingContentGenerator()
    kernel.ai_orchestrator.set_content_generator(tracing_generator)
    
    try:
        print("\n--- Starting kernel.send_user_prompt() ---")
        response = await kernel.send_user_prompt("What is the current date?")
        print("--- Returned from kernel.send_user_prompt() ---")
        print(f"Final response: '{response}'")
        
        print("\n--- Testing with a system command ---")
        response2 = await kernel.send_user_prompt("Check system status")
        print(f"System status response: '{response2}'")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await kernel._cleanup_components()


async def test_kernel_api_flow():
    """Test the flow through the kernel API to CLI."""
    print("\n" + "="*50)
    print("Testing kernel API flow...")
    
    # Create kernel 
    kernel = GCSKernel()
    
    # Initialize components
    await kernel._initialize_components()
    
    # Create kernel API client
    from ui.common.kernel_api import KernelAPIClient
    api_client = KernelAPIClient(kernel)
    
    # Mock the content generator to simulate proper tool calling
    class APIFlowTestGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
        
        async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
            self.call_count += 1
            
            class ResponseObj:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls
            
            if self.call_count == 1 and "date" in prompt.lower():
                # Return a tool call
                tool_call = ToolCall(
                    id="call_date",
                    name="shell_command", 
                    arguments={"command": "date"}
                )
                return ResponseObj(
                    content="Let me get the system date for you.",
                    tool_calls=[tool_call]
                )
            else:
                # Return final response
                return ResponseObj(
                    content="The date has been retrieved successfully.",
                    tool_calls=[]
                )
        
        async def process_tool_result(self, tool_result):
            print(f"API flow: Processing tool result: {tool_result.return_display}")
            
            class ResponseObj:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []
            
            return ResponseObj(
                content=f"Final response after tool: {tool_result.return_display}",
                tool_calls=[]
            )
        
        async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
            yield f"Streaming response: {prompt}"

    # Replace the content generator
    test_generator = APIFlowTestGenerator()
    kernel.ai_orchestrator.set_content_generator(test_generator)
    
    try:
        print("Calling api_client.send_user_prompt()...")
        response = await api_client.send_user_prompt("What is the date?")
        print(f"Response from API client: '{response}'")
        
        print("\nTesting streaming response...")
        chunks = []
        async for chunk in api_client.stream_user_prompt("What is the time?"):
            chunks.append(chunk)
        print(f"Streamed chunks: {chunks}")
        
    except Exception as e:
        print(f"Error in API flow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing complete response flow in GCS Kernel...")
    
    # Test the kernel flow
    asyncio.run(test_complete_flow_with_tracing())
    
    # Test the API flow
    asyncio.run(test_kernel_api_flow())