"""
Test suite for the Content Generation Pipeline Implementation.

This module tests the ContentGenerationPipeline class and its functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.base_provider import BaseProvider


class MockProvider(BaseProvider):
    """
    Mock implementation of BaseProvider for testing purposes.
    """
    def __init__(self, config, mock_client=None):
        self.config = config
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-test-model")
        self.base_url = config.get("base_url", "https://api.test.com/v1")
        self.timeout = config.get("timeout", 60)
        self.max_retries = config.get("max_retries", 3)
        self._mock_client = mock_client  # Store the client to return
        
        # Initialize a converter for the mock provider
        from services.llm_provider.providers.openai_converter import OpenAIConverter
        self._converter = OpenAIConverter(self.model)
    
    @property
    def converter(self):
        """
        The converter for this mock provider to transform data between kernel and provider formats.
        """
        return self._converter
    
    def build_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    
    def build_client(self):
        # Return the pre-configured mock client if available, otherwise create a new MagicMock
        return self._mock_client if self._mock_client is not None else MagicMock()
    
    def build_request(self, request, user_prompt_id):
        enhanced_request = request.copy()
        if "model" not in enhanced_request:
            enhanced_request["model"] = self.model
        if "user" not in enhanced_request:
            enhanced_request["user"] = user_prompt_id
        return enhanced_request


@pytest.mark.asyncio
async def test_content_generation_pipeline_initialization():
    """
    Test that ContentGenerationPipeline initializes properly with provider and converter.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model"
    }
    provider = MockProvider(config)
    
    pipeline = ContentGenerationPipeline(provider)
    
    assert pipeline.provider == provider
    assert pipeline.converter is not None





@pytest.mark.asyncio
async def test_content_generation_pipeline_execute_with_proper_mock():
    """
    Test that ContentGenerationPipeline can execute a content generation request
    with a properly configured mock client.
    """
    from unittest.mock import AsyncMock
    
    # Create a mock response with the expected structure
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Test response content",
                    "tool_calls": []
                }
            }
        ]
    }
    
    # Create a mock client that returns the proper mock response
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    
    # Create a provider with the pre-configured mock client
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model"
    }
    provider = MockProvider(config, mock_client=mock_client)
    pipeline = ContentGenerationPipeline(provider)
    
    # Execute the pipeline
    request = {
        "prompt": "Test prompt",
        "model": "gpt-test-model"
    }
    
    result = await pipeline.execute(request, "user_prompt_123")
    
    # Verify the client's post method was called once
    mock_client.post.assert_called_once()
    
    # Verify result structure
    assert "content" in result
    assert "tool_calls" in result
    assert result["content"] == "Test response content"


