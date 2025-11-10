"""
Integration test for kernel initialization timing.
This test verifies the kernel's initialization sequence works properly.
"""

import asyncio
import pytest
from gcs_kernel.kernel import GCSKernel
from common.settings import settings


@pytest.mark.asyncio 
async def test_kernel_initialization_timing():
    """
    Test the kernel initialization timing scenario to ensure 
    proper handling of initialization states.
    """
    # Setup
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"
    
    try:
        # Create a kernel to test initialization sequence
        kernel = GCSKernel()
        
        # Initially content_generator should be present (initialized in constructor)
        assert kernel.ai_orchestrator.content_generator is not None
        assert kernel.is_running() is False  # _running starts as False
        assert getattr(kernel, '_fully_initialized', False) is False
        
        # Now initialize components (this is what happens in kernel.run())
        await kernel._initialize_components()
        
        # Content generator should now be set and initialization flag should be true
        assert kernel.ai_orchestrator.content_generator is not None
        assert getattr(kernel, '_fully_initialized', False) is True
        assert kernel.is_running() is False  # But still not running until run() sets _running=True
        
        # Set running status to True (this happens in run() method)
        kernel._running = True
        assert kernel.is_running() is True
        
        print("Initialization timing test successful!")
        
    finally:
        settings.llm_api_key = original_api_key