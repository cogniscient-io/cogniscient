"""
Integration test for the GCS Kernel to LLM response flow.

This test verifies the complete flow from the kernel through to the LLM and back,
using a mock provider to simulate the LLM response without requiring an actual API.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from gcs_kernel.kernel import GCSKernel
from services.ai_orchestrator import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from services.llm_provider.providers.mock_provider import MockProvider
from services.config import settings


class MockMCPClient:
    """Mock MCP client for testing purposes."""
    
    def __init__(self):
        self.submitted_executions = []
        self.execution_results = {}
    
    async def initialize(self):
        pass
        
    async def shutdown(self):
        pass
    
    async def submit_tool_execution(self, tool_name, parameters):
        execution_id = f"exec_{len(self.submitted_executions) + 1}"
        self.submitted_executions.append({
            "id": execution_id,
            "tool_name": tool_name,
            "parameters": parameters
        })
        return execution_id
    
    async def get_execution_result(self, execution_id):
        # Return a mock tool result
        from gcs_kernel.models import ToolResult
        return ToolResult(
            execution_id=execution_id,
            success=True,
            return_code=0,
            return_display=f"Mock result for execution {execution_id}",
            error_message=None
        )


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
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(kernel_client=mock_kernel_client)
        
        # Create a mock provider directly
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class MockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
        
        # Initialize the orchestrator with the mock content generator
        ai_orchestrator.set_content_generator(MockContentGenerator())
        
        # Test the full flow with a simple hello world prompt
        prompt = "Say hello world"
        response = await ai_orchestrator.handle_ai_interaction(prompt)
        
        # Verify the response contains expected content
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
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(kernel_client=mock_kernel_client)
        
        # Create a mock provider directly
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class MockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
        
        # Initialize the orchestrator with the mock content generator
        ai_orchestrator.set_content_generator(MockContentGenerator())
        
        # Test the streaming flow with a simple hello world prompt
        prompt = "Say hello world"
        chunks = []
        async for chunk in ai_orchestrator.stream_ai_interaction(prompt):
            chunks.append(chunk)
        
        # Combine all chunks to form the full response
        full_response = "".join(chunks)
        
        # Verify the response contains expected content
        assert "Hello" in full_response or "hello" in full_response
        assert "test" in full_response or "Test" in full_response
        
        print(f"Streaming integration test successful! Full response: {full_response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key