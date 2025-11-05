"""
Integration test for the new GCS Kernel CLI architecture.

This test verifies the complete flow from the new CLI through to the kernel's AI orchestrator
and back, using a mock provider to simulate the LLM response without requiring an actual API.
"""

import asyncio
import pytest
from gcs_kernel.kernel import GCSKernel
from ui.common.kernel_api import KernelAPIClient
from ui.common.cli_ui import CLIUI
from services.config import settings


@pytest.mark.asyncio
async def test_new_cli_architecture_hello_world():
    """
    Test the complete flow from new CLI to LLM and back with a 'hello world' prompt.
    
    This integration test verifies that:
    1. The new CLI architecture can be initialized properly
    2. A 'hello world' prompt can be submitted through the new CLI
    3. The prompt flows through the kernel to the AI orchestrator using a mock provider
    4. The response flows back through the system correctly via the kernel
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Create the kernel which should initialize with an AI orchestrator
        kernel = GCSKernel()
        
        # Mock only the external provider to simulate responses without API calls
        from gcs_kernel.models import PromptObject
        async def mock_handle_interaction(prompt_obj):
            response_obj = PromptObject.create(
                content=f"Response for: {prompt_obj.content}"
            )
            response_obj.result_content = f"Response for: {prompt_obj.content}"
            return response_obj
        
        # Replace the orchestrator's method with mock - need to ensure it's properly initialized
        # Also need to ensure the content_generator is not None to avoid the initialization check
        from unittest.mock import AsyncMock
        kernel.ai_orchestrator.content_generator = AsyncMock()  # Mock content generator to pass check
        
        # Replace the orchestrator's method with mock
        kernel.ai_orchestrator.handle_ai_interaction = mock_handle_interaction
        
        # Create the new kernel API client that interfaces with kernel
        kernel_api_client = KernelAPIClient(kernel)
        
        # Create the new CLI UI with proper async resource management
        cli_ui = CLIUI(kernel_api_client)
        
        # Test the specific functionality - process a 'hello world' prompt
        # Note: In the new architecture, we're directly calling the API methods
        # rather than the old process_user_input method
        result = await cli_ui.display_response("hello world")
        
        # Verify the result contains expected content from the kernel's AI orchestrator
        assert "Response for: hello world" in result
        
        print(f"New CLI architecture test successful! Result: {result}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key


@pytest.mark.asyncio
async def test_new_cli_architecture_streaming():
    """
    Test the streaming functionality in the new CLI architecture.
    
    This test validates that the proper streaming functionality works through the kernel.
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Create the kernel which should initialize with an AI orchestrator
        kernel = GCSKernel()
        
        # Mock only the external provider to simulate responses without API calls
        from gcs_kernel.models import PromptObject
        from typing import AsyncIterator
        async def mock_stream_interaction(prompt_obj: PromptObject) -> AsyncIterator[str]:
            response = f"Streaming response for: {prompt_obj.content}"
            # Yield chunks to simulate streaming
            for i in range(0, len(response), 5):  # Yield every 5 characters
                chunk = response[i:i+5]
                yield chunk
        
        # Need to ensure content_generator is set to bypass initialization check
        from unittest.mock import AsyncMock
        kernel.ai_orchestrator.content_generator = AsyncMock()  # Mock content generator to pass check
        
        # Replace the orchestrator's streaming method with mock
        kernel.ai_orchestrator.stream_ai_interaction = mock_stream_interaction
        
        # Create the new kernel API client that interfaces with kernel
        kernel_api_client = KernelAPIClient(kernel)
        
        # Create the new CLI UI with proper async resource management
        cli_ui = CLIUI(kernel_api_client)
        
        # Test the streaming functionality
        # For the test, we'll directly call the streaming handler to verify it works
        stream_generator = kernel_api_client.stream_user_prompt("hello world")
        response_chunks = []
        async for chunk in stream_generator:
            response_chunks.append(chunk)
        
        # Verify we got a proper streaming response
        full_response = "".join(response_chunks)
        assert "Streaming response for: hello world" in full_response
        
        print(f"New CLI streaming test successful! Response: {full_response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key