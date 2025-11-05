"""
Integration test for the Content Generation Pipeline that tests full LLM integration.

This is the only place (aside from end-to-end tests) where we test the full LLM integration.
Uses a real provider but with a mock API key to avoid actual LLM costs during testing.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.openai_provider import OpenAIProvider
from services.llm_provider.providers.mock_provider import MockProvider
from gcs_kernel.models import PromptObject


@pytest.mark.asyncio
async def test_full_pipeline_integration_with_mock_llm():
    """
    Full pipeline integration test that simulates communication with a real LLM API.
    
    This test verifies the complete flow:
    1. PromptObject input
    2. Request building through provider
    3. Request sending via client
    4. Response processing
    5. Response conversion and return
    """
    # Configuration for the provider (using a mock API key)
    config = {
        "api_key": "sk-mock-test-key-12345",  # This won't actually work for real calls
        "model": "gpt-4-test",
        "base_url": "https://api.mock-test.com/v1"  # Mock URL
    }
    
    # Create provider
    provider = OpenAIProvider(config)
    
    # Create a mock response that simulates what a real LLM API would return
    mock_response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM integration test",
                    "tool_calls": []
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 9,
            "completion_tokens": 12,
            "total_tokens": 21
        }
    }
    
    # Mock the httpx client to return our mock response instead of making a real call
    mock_client = AsyncMock()
    mock_client_response = AsyncMock()
    mock_client_response.status_code = 200
    mock_client_response.json.return_value = mock_response_data
    mock_client.post.return_value = mock_client_response
    
    # Create the pipeline with the mocked client
    with patch.object(provider, 'build_client', return_value=mock_client):
        pipeline = ContentGenerationPipeline(provider)
        
        # Create a PromptObject for the test
        prompt_obj = PromptObject.create(
            content="Test integration with LLM",
            max_tokens=100,
            temperature=0.7
        )
        # In the new architecture, the user message should already be in the conversation history
        prompt_obj.add_user_message(prompt_obj.content)
        
        # Execute through the pipeline
        result = await pipeline.execute(prompt_obj)
        
        # Verify the result structure in the new OpenAI format
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]
        assert "tool_calls" in result["choices"][0]["message"]
        assert result["choices"][0]["message"]["content"] == "This is a test response from the LLM integration test"
        assert result["choices"][0]["message"]["tool_calls"] == []
        
        # Verify that the client's post method was called with the right parameters
        mock_client.post.assert_called_once()
        
        # Get the call arguments to verify the request was built correctly
        call_args = mock_client.post.call_args
        args, kwargs = call_args
        
        # The first positional argument is the URL
        url = args[0]
        
        # Verify URL is correct
        assert url == "https://api.mock-test.com/v1/chat/completions"
        
        # Verify request payload includes our prompt
        request_payload = kwargs['json']
        assert "messages" in request_payload
        assert request_payload["model"] == "gpt-4-test"
        assert request_payload["max_tokens"] == 100
        assert request_payload["temperature"] == 0.7
        
        # Check that the prompt was included in the messages
        messages = request_payload["messages"]
        user_message = next((msg for msg in messages if msg["role"] == "user"), None)
        assert user_message is not None
        assert user_message["content"] == "Test integration with LLM"


@pytest.mark.asyncio
async def test_full_pipeline_integration_with_tool_calls():
    """
    Full pipeline integration test that includes tool calls in the response.
    """
    config = {
        "api_key": "sk-mock-test-key-12345",
        "model": "gpt-4-test",
        "base_url": "https://api.mock-test.com/v1"
    }
    
    provider = OpenAIProvider(config)
    
    # Mock response that includes tool calls
    mock_response_data = {
        "id": "chatcmpl-456",
        "object": "chat.completion",
        "created": 1677652289,
        "model": "gpt-4-0613",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I will use a tool to get that information for you",
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_current_weather",
                                "arguments": '{"location": "New York", "unit": "celsius"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ]
    }
    
    # Mock the client
    mock_client = AsyncMock()
    mock_client_response = AsyncMock()
    mock_client_response.status_code = 200
    mock_client_response.json.return_value = mock_response_data
    mock_client.post.return_value = mock_client_response
    
    with patch.object(provider, 'build_client', return_value=mock_client):
        pipeline = ContentGenerationPipeline(provider)
        
        prompt_obj = PromptObject.create(
            content="What's the weather like in New York?",
            max_tokens=150
        )
        
        result = await pipeline.execute(prompt_obj)
        
        # Verify response includes tool calls in the new OpenAI format
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]
        assert "tool_calls" in result["choices"][0]["message"]
        assert result["choices"][0]["message"]["content"] == "I will use a tool to get that information for you"
        assert len(result["choices"][0]["message"]["tool_calls"]) == 1
        assert result["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_current_weather"
        assert result["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] == '{"location": "New York", "unit": "celsius"}'


@pytest.mark.asyncio
async def test_full_pipeline_streaming_integration():
    """
    Full pipeline integration test for streaming functionality.
    """
    config = {
        "api_key": "mock-key-test",
        "model": "gpt-test-model",
    }
    
    # Create the provider with mock configuration
    provider = MockProvider(config)
    
    # Create the pipeline with the provider
    pipeline = ContentGenerationPipeline(provider)
    
    # Test streaming - since the actual streaming implementation in the pipeline
    # has a mock fallback when no stream method exists, we'll test that path
    prompt_obj = PromptObject.create(content="Stream this content")
    
    # Capture the streamed content
    streamed_content = []
    async for chunk in pipeline.execute_stream(prompt_obj):
        # Extract content from the chunk (in streaming format)
        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if content:  # Only append if there's actual content
            streamed_content.append(content)
        
        # Limit chunks to avoid infinite loops in case of issues
        if len(streamed_content) > 100:  # Safety limit
            break
    
    full_content = "".join(streamed_content)
    
    # Verify we got streamed content
    assert len(full_content) > 0
    assert "test" in full_content.lower()