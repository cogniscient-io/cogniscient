"""
Integration test for the GCS Kernel to LLM response flow.

This test verifies the complete flow from the kernel through to the LLM and back,
using real system components where possible while mocking external dependencies.
"""

import asyncio
import pytest

from gcs_kernel.kernel import GCSKernel
from gcs_kernel.registry import ToolRegistry
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from services.config import settings


@pytest.mark.asyncio
async def test_kernel_to_llm_hello_world():
    """
    Test the end-to-end flow from kernel to LLM and back with a simple hello world prompt.
    
    This integration test verifies that:
    1. The GCSKernel can be initialized and started
    2. The AIOrchestratorService can be connected to the kernel
    3. The LLM provider can generate a response to a simple prompt
    4. The response flows back through the system correctly
    """
    # Use mock settings for testing to avoid requiring real API keys
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Create a real kernel instance
        kernel = GCSKernel()
        
        # Initialize the MCP client for the kernel
        # For integration test, we'll create a minimal kernel client that simulates
        # communication with the kernel
        class TestKernelClient:
            def __init__(self, kernel_instance):
                self.kernel = kernel_instance

            async def submit_tool_execution(self, tool_name, parameters):
                # Simulate tool execution submission to the kernel
                if self.kernel and hasattr(self.kernel, 'registry'):
                    # Use the actual kernel to execute tools when possible
                    tool = await self.kernel.registry.get_tool(tool_name)
                    if tool:
                        result = await tool.execute(parameters)
                        return f"exec_{id(result)}"
                
                # Fallback to simulated execution ID
                return f"exec_{hash(tool_name) % 10000}"
            
            async def get_execution_result(self, execution_id):
                # Simulate getting result from kernel
                from gcs_kernel.models import ToolResult
                return ToolResult(
                    tool_name="test_tool",
                    success=True,
                    llm_content=f"Simulated result for execution {execution_id}",
                    return_display=f"Simulated result for execution {execution_id}"
                )

        kernel_client = TestKernelClient(kernel)
        
        # Initialize the AI orchestrator service with the kernel client
        ai_orchestrator = AIOrchestratorService(kernel_client=kernel_client)
        
        # Set up real kernel services
        registry = ToolRegistry()
        ai_orchestrator.set_kernel_services(registry=registry)
        
        # Create the real content generator - this tests the real integration
        content_generator = LLMContentGenerator(kernel=kernel)
        
        # Override the provider in the content generator to avoid real API calls
        # But keep the real converter, pipeline, and other components for integration testing
        from services.llm_provider.providers.mock_provider import MockProvider
        
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        content_generator.provider = MockProvider(mock_provider_config)
        
        # Set up the pipeline with the mock provider
        from services.llm_provider.pipeline import ContentGenerationPipeline
        content_generator.pipeline = ContentGenerationPipeline(content_generator.provider)
        
        # Initialize the orchestrator with the real content generator
        ai_orchestrator.set_content_generator(content_generator)
        
        # Test the full flow with a simple hello world prompt
        prompt = "Say hello world"
        response = await ai_orchestrator.handle_ai_interaction(prompt)
        
        # Verify the response contains expected content
        # This tests that the whole pipeline works correctly
        assert response is not None
        # The MockProvider returns "Hello, this is a test response from the LLM!"
        assert "Hello" in response or "hello" in response
        assert "test" in response or "Test" in response
        
        print(f"Integration test successful! Response: {response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key


@pytest.mark.asyncio
async def test_kernel_llm_streaming_hello_world():
    """
    Test the streaming end-to-end flow from kernel to LLM and back.
    
    This integration test verifies the streaming capability of the system.
    """
    # Use mock settings for testing to avoid requiring real API keys
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Create a real kernel instance
        kernel = GCSKernel()
        
        # Initialize the MCP client for the kernel
        class TestKernelClient:
            def __init__(self, kernel_instance):
                self.kernel = kernel_instance

            async def submit_tool_execution(self, tool_name, parameters):
                # Simulate tool execution submission to the kernel
                if self.kernel and hasattr(self.kernel, 'registry'):
                    # Use the actual kernel to execute tools when possible
                    tool = await self.kernel.registry.get_tool(tool_name)
                    if tool:
                        result = await tool.execute(parameters)
                        return f"exec_{id(result)}"
                
                # Fallback to simulated execution ID
                return f"exec_{hash(tool_name) % 10000}"
            
            async def get_execution_result(self, execution_id):
                # Simulate getting result from kernel
                from gcs_kernel.models import ToolResult
                return ToolResult(
                    tool_name="test_tool",
                    success=True,
                    llm_content=f"Simulated result for execution {execution_id}",
                    return_display=f"Simulated result for execution {execution_id}"
                )
        
        kernel_client = TestKernelClient(kernel)
        
        # Initialize the AI orchestrator service with the kernel client
        ai_orchestrator = AIOrchestratorService(kernel_client=kernel_client)
        
        # Set up real kernel services
        registry = ToolRegistry()
        ai_orchestrator.set_kernel_services(registry=registry)
        
        # Create the real content generator - this tests the real integration
        content_generator = LLMContentGenerator(kernel=kernel)
        
        # Override the provider in the content generator to avoid real API calls
        # But keep the real converter, pipeline, and other components for integration testing
        from services.llm_provider.providers.mock_provider import MockProvider
        
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        content_generator.provider = MockProvider(mock_provider_config)
        
        # Set up the pipeline with the mock provider
        from services.llm_provider.pipeline import ContentGenerationPipeline
        content_generator.pipeline = ContentGenerationPipeline(content_generator.provider)
        
        # Initialize the orchestrator with the real content generator
        ai_orchestrator.set_content_generator(content_generator)
        
        # Test the streaming flow with a simple hello world prompt
        prompt = "Say hello world"
        chunks = []
        async for chunk in ai_orchestrator.stream_ai_interaction(prompt):
            chunks.append(chunk)
        
        # Combine all chunks to form the full response
        full_response = "".join(chunks)
        
        # Verify the response contains expected content
        # This tests that the whole streaming pipeline works correctly
        assert full_response is not None
        # The MockProvider returns "Hello, this is a test response from the LLM!"
        assert "Hello" in full_response or "hello" in full_response
        assert "test" in full_response or "Test" in full_response
        
        print(f"Streaming integration test successful! Full response: {full_response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key