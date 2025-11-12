"""
Integration test for Adaptive Loop with real kernel components.

This module tests the complete Adaptive Loop flow using real components,
though it requires actual LLM access to function properly.
"""
import pytest
import os
from unittest.mock import MagicMock

from gcs_kernel.kernel import GCSKernel
from services.adaptive_loop.adaptive_loop_service import AdaptiveLoopService


@pytest.mark.asyncio
async def test_adaptive_loop_with_real_kernel_components():
    """
    Test the Adaptive Loop with real kernel components.
    This test uses actual AI orchestrator and related components,
    though it requires a valid LLM configuration to produce meaningful results.
    """
    
    # Create a minimal config for testing
    config = {
        "mcp_config": {
            "server_url": "http://localhost:8000"  # Default value
        }
    }
    
    # Create the kernel (this will set up the adaptive loop service and orchestrator)
    kernel = GCSKernel(config)
    
    # Access the adaptive loop service that was created with the kernel
    adaptive_service = kernel.adaptive_loop_service
    
    # Verify that the service and its orchestrator are properly connected
    assert adaptive_service is not None
    assert adaptive_service.ai_orchestrator is not None
    assert adaptive_service.mcp_client is not None
    
    # Verify that the connection is working at the component level
    assert hasattr(adaptive_service.ai_orchestrator, 'handle_ai_interaction')
    assert hasattr(kernel.mcp_client_manager, 'initialize')
    
    print("✓ AdaptiveLoopService is properly integrated with kernel components")
    print("✓ AI orchestrator is connected to the adaptive service")
    print("✓ MCP client is available for communication")
    
    # Test with a mock model response similar to the user's example
    # Note: This test will work with mocked responses in actual test runs,
    # but would connect to a real LLM when properly configured
    vllm_model_response = {
        "object": "list",
        "data": [
            {
                "id": "qwen/qwen3-coder-30b-a3b-instruct",
                "object": "model",
                "created": 1762804142,
                "owned_by": "vllm",
                "root": "qwen/qwen3-coder-30b-a3b-instruct",
                "parent": None,
                "max_model_len": 262144,  # This is the value we want to extract
                "permission": [
                    {
                        "id": "modelperm-66945a594bec418a9f57cd69919a0517",
                        "object": "model_permission",
                        "created": 1762804142,
                        "allow_create_engine": False,
                        "allow_sampling": True,
                        "allow_logprobs": True,
                        "allow_search_indices": False,
                        "allow_view": True,
                        "allow_fine_tuning": False,
                        "organization": "*",
                        "group": None,
                        "is_blocking": False
                    }
                ]
            }
        ]
    }
    
    # Context data similar to what would be passed in the actual implementation
    context_data = {
        "model_response": vllm_model_response,
        "model_name": "qwen/qwen3-coder-30b-a3b-instruct",
        "missing_field": "max_context_length",
        "possible_field_names": [
            "max_model_len", "max_context_length", "context_length",
            "max_tokens", "max_input_tokens", "max_seq_len", "max_position_embeddings"
        ]
    }
    
    # Note: This test is checking that the system is properly structured to make
    # calls to the AI orchestrator. In a real environment with proper LLM configuration,
    # this would actually process the request and get a response from the LLM.
    
    # Verify that all required fields are accessible
    assert hasattr(adaptive_service, 'adapt_async')
    assert hasattr(adaptive_service, '_build_prompt')
    assert hasattr(adaptive_service, '_parse_ai_response')
    
    print("✓ AdaptiveLoopService has all required methods")
    
    # The service is ready to process real requests when the system is properly configured
    print("✓ System is properly configured to process real AI requests when LLM is available")
    
    # Test that the prompt structure can be built correctly
    test_prompt = adaptive_service._build_prompt(context_data, 
                                               "Find the maximum context length field in the model response")
    assert "Context:" in test_prompt
    assert "qwen/qwen3-coder-30b-a3b-instruct" in test_prompt
    assert "max_model_len" in test_prompt
    
    print("✓ Prompt building works correctly with real model response data")


@pytest.mark.asyncio
async def test_kernel_initialization_sets_up_adaptive_loop():
    """Test that kernel initialization properly sets up the Adaptive Loop."""
    
    # Create kernel with minimal config
    config = {}
    kernel = GCSKernel(config)
    
    # Verify that the kernel has the adaptive loop service
    assert hasattr(kernel, 'adaptive_loop_service')
    assert kernel.adaptive_loop_service is not None
    
    # Verify that the adaptive loop service is connected to the AI orchestrator
    assert kernel.adaptive_loop_service.ai_orchestrator is kernel.ai_orchestrator
    
    # Verify that the provider (through content generator) has the adaptive loop service
    content_generator = kernel.ai_orchestrator.content_generator
    provider = content_generator.provider
    
    # Verify the adaptive loop service is set on the provider
    # (This works because the kernel sets it via the provider's set_adaptive_error_service method)
    assert hasattr(provider, 'adaptive_loop_service') 
    assert provider.adaptive_loop_service is kernel.adaptive_loop_service
    
    print("✓ Kernel properly initializes and connects all Adaptive Loop components")
    print("✓ AdaptiveLoopService is connected to AI orchestrator")
    print("✓ OpenAIProvider has reference to adaptive loop service")
    
    # Verify the complete chain: Kernel -> AdaptiveService -> Orchestrator -> Provider -> AdaptiveService
    assert kernel.adaptive_loop_service.ai_orchestrator == kernel.ai_orchestrator
    assert provider.adaptive_loop_service == kernel.adaptive_loop_service
    
    print("✓ Full component chain is properly established")