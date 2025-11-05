"""
Unit tests for ContentGenerationPipeline functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.mock_provider import MockProvider
from gcs_kernel.models import PromptObject


def test_pipeline_initialization():
    """Test that ContentGenerationPipeline initializes properly."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model"
    }
    provider = MockProvider(config)
    
    pipeline = ContentGenerationPipeline(provider)
    
    assert pipeline.provider == provider
    assert pipeline.converter is not None


@pytest.mark.asyncio
async def test_pipeline_execute_with_mock_provider():
    """Test pipeline execution with a properly configured mock provider."""
    from unittest.mock import AsyncMock, PropertyMock
    
    # Create a mock response with the expected structure
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Test response content from pipeline",
                    "tool_calls": []
                }
            }
        ]
    }
    # Mock the headers property
    type(mock_response).headers = PropertyMock(return_value={'content-type': 'application/json'})
    
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    
    # Create a provider with custom response content
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    
    # Override the client with our mock to ensure consistent behavior
    pipeline.client = mock_client
    
    # Execute the pipeline with a PromptObject
    prompt_obj = PromptObject.create(
        content="Test prompt for pipeline execution"
    )
    
    result = await pipeline.execute(prompt_obj)
    
    # Verify the client's post method was called once
    mock_client.post.assert_called_once()
    
    # Verify result structure - checking the actual nested structure
    assert result["choices"][0]["message"]["content"] == "Test response content from pipeline"
    assert isinstance(result["choices"][0]["message"]["tool_calls"], list)


@pytest.mark.asyncio
async def test_pipeline_execute_with_tool_calls():
    """Test pipeline execution with tool calls in the response."""
    from unittest.mock import PropertyMock
    
    # Create a mock response with tool calls
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "I'll use a tool to help with that",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "test_tool",
                                "arguments": '{"param": "value"}'
                            }
                        }
                    ]
                }
            }
        ]
    }
    # Mock the headers property
    type(mock_response).headers = PropertyMock(return_value={'content-type': 'application/json'})
    
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    # Override the client with our mock
    pipeline.client = mock_client
    
    prompt_obj = PromptObject.create(content="Use a tool for this")
    
    result = await pipeline.execute(prompt_obj)
    
    # Verify tool calls are in the result (using the new format)
    assert result["choices"][0]["message"]["content"] == "I'll use a tool to help with that"
    assert len(result["choices"][0]["message"]["tool_calls"]) == 1
    assert result["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "test_tool"


@pytest.mark.asyncio
async def test_pipeline_execute_error_handling():
    """Test pipeline error handling during request execution."""
    # Configure the provider to simulate an error response
    config = {
        "api_key": "invalid-key",
        "model": "gpt-test-model",
        "should_error": True  # This will cause the provider to return an error response
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    
    prompt_obj = PromptObject.create(content="Test error handling")
    
    # Should raise an exception due to the simulated error response
    with pytest.raises(Exception):
        await pipeline.execute(prompt_obj)


@pytest.mark.asyncio
async def test_pipeline_execute_stream():
    """Test pipeline streaming functionality."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "response_content": "Streaming test content",
        "response_delay": 0  # No delay for tests
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    
    prompt_obj = PromptObject.create(content="Stream this content")
    
    # Test streaming - collect the streamed chunks
    streamed_chunks = []
    async for chunk in pipeline.execute_stream(prompt_obj):
        streamed_chunks.append(chunk)
        
        # Limit chunks to avoid infinite loops in case of issues
        if len(streamed_chunks) > 20:  # Safety limit
            break
    
    # Extract content from the streamed chunks
    full_content = ""
    for chunk in streamed_chunks:
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            full_content += content
    
    # Verify we got streamed content
    assert len(full_content) > 0
    assert "test" in full_content.lower()





@pytest.mark.asyncio
async def test_pipeline_execute_with_conversation_history():
    """Test pipeline execution with conversation history."""
    from unittest.mock import AsyncMock, PropertyMock
    
    # Create a mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Response considering the conversation history",
                    "tool_calls": []
                }
            }
        ]
    }
    # Mock the headers property
    type(mock_response).headers = PropertyMock(return_value={'content-type': 'application/json'})
    
    # Create a mock client
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    # Override the client with our mock
    pipeline.client = mock_client
    
    # Create a PromptObject with conversation history
    prompt_obj = PromptObject.create(content="Follow up on previous conversation")
    prompt_obj.conversation_history = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "What's the weather today?"},
        {"role": "assistant", "content": "The weather is sunny"},
    ]
    
    result = await pipeline.execute(prompt_obj)
    
    # Verify the response matches the new format
    assert result["choices"][0]["message"]["content"] == "Response considering the conversation history"


def test_pipeline_provider_access():
    """Test that pipeline properly accesses provider attributes."""
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model"
    }
    provider = MockProvider(config)
    pipeline = ContentGenerationPipeline(provider)
    
    # Verify pipeline has access to provider and its components
    assert pipeline.provider == provider
    assert pipeline.converter is not None
    assert pipeline.client is not None