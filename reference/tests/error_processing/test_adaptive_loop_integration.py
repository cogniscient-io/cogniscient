"""
Test suite for Adaptive Loop integration with OpenAI Provider.

This module tests the integration between AdaptiveErrorProcessingService
and OpenAIProvider's get_model_info functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.error_processing.adaptive_error_service import AdaptiveErrorProcessingService
from services.llm_provider.providers.openai_provider import OpenAIProvider


class MockOrchestrator:
    """Mock AI orchestrator for testing."""
    async def handle_ai_interaction(self, prompt_obj):
        # For testing purposes, return a fixed response that our service can parse
        prompt_obj.result_content = "max_tokens: 32000"
        prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj


@pytest.fixture
def mock_openai_provider():
    """Create an OpenAIProvider instance for testing."""
    config = {
        "api_key": "test-key",
        "model": "gpt-4-turbo"
    }
    return OpenAIProvider(config)


@pytest.mark.asyncio
async def test_openai_provider_has_adaptive_error_service_method(mock_openai_provider):
    """Test that OpenAIProvider has the set_adaptive_error_service method."""
    assert hasattr(mock_openai_provider, 'set_adaptive_error_service')
    
    # Verify it can be called without error
    mock_service = MagicMock()
    mock_openai_provider.set_adaptive_error_service(mock_service)
    assert mock_openai_provider.adaptive_error_service == mock_service


@pytest.mark.asyncio
async def test_adaptive_error_service_integration():
    """Test full integration between AdaptiveErrorProcessingService and OpenAIProvider."""
    # Create the adaptive error service
    mock_client = MagicMock()
    mock_orchestrator = MockOrchestrator()
    adaptive_service = AdaptiveErrorProcessingService(mock_client, mock_orchestrator)
    
    # Create the provider and set the adaptive service
    config = {
        "api_key": "test-key",
        "model": "gpt-4-turbo"
    }
    provider = OpenAIProvider(config)
    provider.set_adaptive_error_service(adaptive_service)
    
    # Verify the service was set correctly
    assert provider.adaptive_error_service == adaptive_service


@pytest.mark.asyncio
async def test_get_model_info_uses_adaptive_service_if_available(monkeypatch, mock_openai_provider):
    """Test that get_model_info uses adaptive error service when available."""
    # Mock the HTTP call to simulate a model response without max_context_length
    async def mock_get(url, headers=None):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "gpt-4-turbo-test",
            "object": "model",
            "created": 1686935002,
            "owned_by": "openai",
            # Intentionally omit max_context_length to trigger AI processing
        }
        return mock_response

    # Create an async mock for httpx.AsyncClient
    class MockAsyncClient:
        def __init__(self, timeout=None, headers=None):
            pass
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        
        async def get(self, url):
            return await mock_get(url)

    # Patch httpx.AsyncClient
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    
    # Create adaptive error service with known return value
    mock_client = MagicMock()
    
    class DeterministicOrchestrator:
        async def handle_ai_interaction(self, prompt_obj):
            # This should identify max_context_length in the model response
            prompt_obj.result_content = "max_tokens: 16000"
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
    
    adaptive_service = AdaptiveErrorProcessingService(mock_client, DeterministicOrchestrator())
    
    # Set the adaptive error service on the provider
    mock_openai_provider.set_adaptive_error_service(adaptive_service)
    
    # Call get_model_info
    result = await mock_openai_provider.get_model_info("gpt-4-turbo-test")
    
    # Verify that the result uses the value from AI processing (16000)
    # rather than the fallback
    assert result["max_context_length"] == 16000


@pytest.mark.asyncio
async def test_get_model_info_uses_fallback_when_adaptive_service_not_available(monkeypatch, mock_openai_provider):
    """Test that get_model_info uses fallback when adaptive service is not available."""
    # Mock the HTTP call to simulate a model response without max_context_length
    async def mock_get(url, headers=None):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "gpt-4-turbo-test",
            "object": "model",
            "created": 1686935002,
            "owned_by": "openai",
            # Intentionally omit max_context_length to trigger fallback logic
        }
        return mock_response

    # Create an async mock for httpx.AsyncClient
    class MockAsyncClient:
        def __init__(self, timeout=None, headers=None):
            pass
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        
        async def get(self, url):
            return await mock_get(url)

    # Patch httpx.AsyncClient
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    
    # Don't set adaptive error service, so it should use fallback logic
    # When the adaptive service is not set, it should use the hardcoded fallback logic
    
    # Call get_model_info
    result = await mock_openai_provider.get_model_info("gpt-4-turbo-test")
    
    # With gpt-4-turbo in the name, it should use the fallback value of 128000
    assert result["max_context_length"] == 128000  # This is the hardcoded fallback for gpt-4-turbo