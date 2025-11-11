"""
Integration test for Adaptive Error Processing Service with real model response example.

This module tests the AdaptiveErrorProcessingService with a realistic model response
to verify it can extract max_model_len from a VLLM-style response.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from gcs_kernel.models import PromptObject
from services.error_processing.adaptive_error_service import AdaptiveErrorProcessingService


class RealisticResponseOrchestrator:
    """Mock orchestrator that simulates realistic AI processing for model responses."""
    async def handle_ai_interaction(self, prompt_obj):
        # Parse the content to find the model response and problem description
        content = prompt_obj.content
        
        # If this is a request about max_context_length and includes the VLLM response format
        if "max_model_len" in content and "vllm" in content:
            # The AI should identify max_model_len: 262144
            prompt_obj.result_content = "max_model_len: 262144"
            prompt_obj.mark_completed(prompt_obj.result_content)
        elif "max_context_length" in content and "missing" in content:
            # Default response for max_context_length requests
            prompt_obj.result_content = "max_tokens: 128000"
            prompt_obj.mark_completed(prompt_obj.result_content)
        else:
            # Fallback response
            prompt_obj.result_content = "field_name: 8000"
            prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj


@pytest.fixture
def mock_client():
    """Create a mock MCP client for testing."""
    return MagicMock()


@pytest.fixture
def realistic_orchestrator():
    """Create a realistic orchestrator for testing."""
    return RealisticResponseOrchestrator()


@pytest.fixture
def adaptive_error_service(mock_client, realistic_orchestrator):
    """Create an adaptive error processing service instance for testing."""
    return AdaptiveErrorProcessingService(
        mcp_client=mock_client,
        ai_orchestrator=realistic_orchestrator
    )


@pytest.mark.asyncio
async def test_adaptive_service_extracts_max_model_len_from_vllm_response(adaptive_error_service):
    """Test that the adaptive service can extract max_model_len from a VLLM-style response."""
    # This is the exact model response format from the user's example
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
    
    result = await adaptive_error_service.process_error_async(
        error_context=context_data,
        problem_description="Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct",
        fallback_value=4096
    )
    
    # Should extract the max_model_len value: 262144
    assert result == 262144
    print(f"✓ Successfully extracted max_model_len: {result} from VLLM response")


@pytest.mark.asyncio
async def test_adaptive_service_fallback_when_no_value_found():
    """Test fallback when AI cannot find the requested value."""
    mock_client = MagicMock()
    
    class NotFoundOrchestrator:
        async def handle_ai_interaction(self, prompt_obj):
            prompt_obj.result_content = "NOT_FOUND"
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
    
    service = AdaptiveErrorProcessingService(
        mcp_client=mock_client,
        ai_orchestrator=NotFoundOrchestrator()
    )
    
    # A model response without max context length information
    model_response = {
        "id": "some-model",
        "object": "model",
        "created": 1234567890,
        "owned_by": "test",
        # Intentionally no max_context_length-like fields
    }
    
    context_data = {
        "model_response": model_response,
        "model_name": "some-model",
        "missing_field": "max_context_length"
    }
    
    result = await service.process_error_async(
        error_context=context_data,
        problem_description="Find the maximum context length field in the model response",
        fallback_value=8192  # This should be returned
    )
    
    # Should return the fallback value since AI said NOT_FOUND
    assert result == 8192
    print(f"✓ Correctly returned fallback value: {result} when AI couldn't find the field")


@pytest.mark.asyncio
async def test_build_prompt_includes_context_and_problem():
    """Test that the built prompt properly includes the context and problem description."""
    mock_client = MagicMock()
    
    class VerifyingOrchestrator:
        def __init__(self):
            self.prompt_verified = False
            
        async def handle_ai_interaction(self, prompt_obj):
            # Verify the prompt contains both context and problem
            content = prompt_obj.content
            assert "Context:" in content
            assert "Problem:" in content
            assert "qwen3-coder-30b-a3b-instruct" in content  # From the model name
            assert "max_model_len" in content  # From the field we're looking for
            assert "find the maximum context length" in content.lower()  # From the problem description
            
            self.prompt_verified = True
            prompt_obj.result_content = "max_model_len: 131072"
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
    
    verifying_orchestrator = VerifyingOrchestrator()
    service = AdaptiveErrorProcessingService(
        mcp_client=mock_client,
        ai_orchestrator=verifying_orchestrator
    )
    
    # Test with a simplified model response
    model_response = {
        "id": "qwen/qwen3-coder-30b-a3b-instruct",
        "max_model_len": 131072
    }
    
    context_data = {
        "model_response": model_response,
        "model_name": "qwen/qwen3-coder-30b-a3b-instruct",
        "missing_field": "max_context_length"
    }
    
    result = await service.process_error_async(
        error_context=context_data,
        problem_description="Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct",
        fallback_value=4096
    )
    
    # Verify that the prompt was properly constructed and sent to AI
    assert verifying_orchestrator.prompt_verified
    assert result == 131072
    print("✓ Prompt was correctly built with context and problem description")