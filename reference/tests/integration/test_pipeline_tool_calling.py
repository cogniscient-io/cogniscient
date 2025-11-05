"""
Integration test for Content Generation Pipeline with Tool Calling functionality.

This test verifies the complete flow from pipeline through tool calling and execution.
"""

import pytest
from unittest.mock import AsyncMock

from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.mock_provider import MockProvider
from gcs_kernel.models import PromptObject, ToolResult


@pytest.mark.asyncio
async def test_pipeline_tool_calling_integration():
    """
    Test content generation pipeline with tool calling functionality.
    
    This integration test verifies that:
    1. Pipeline can generate responses with tool calls
    2. Tool calls are properly detected in the response
    3. The response structure is correct for tool calling
    """
    # Create a mock provider that returns tool calls
    mock_provider_config = {
        "api_key": "test-key",
        "model": "gpt-4-test",
        "base_url": "https://mock.api.test",
        "timeout": 30,
        "max_retries": 1,
        "response_content": "I'll use a tool to help with that.",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "shell_command",
                    "arguments": '{"command": "date"}'
                }
            }
        ]
    }
    mock_provider = MockProvider(mock_provider_config)
    
    # Create pipeline with the mock provider
    pipeline = ContentGenerationPipeline(mock_provider)
    
    # Test with a prompt that should trigger tool calling
    prompt_obj = PromptObject.create(content="Can you help me with something?")
    
    # Execute through the pipeline
    response = await pipeline.execute(prompt_obj)
    
    # Verify the response structure in the new OpenAI format
    assert "choices" in response
    assert len(response["choices"]) > 0
    assert "message" in response["choices"][0]
    assert "content" in response["choices"][0]["message"] 
    assert "tool_calls" in response["choices"][0]["message"]
    # The MockProvider has built-in logic for certain prompts, so just verify it's not empty
    assert len(response["choices"][0]["message"]["content"]) > 0
    
    # Verify tool calls are in the response
    assert len(response["choices"][0]["message"]["tool_calls"]) == 1
    assert response["choices"][0]["message"]["tool_calls"][0]["id"] == "call_123"
    assert response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "shell_command"
    assert response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] == '{"command": "date"}'
    
    print(f"Pipeline tool calling integration test successful! Response: {response}")


@pytest.mark.asyncio
async def test_pipeline_streaming_basic_integration():
    """
    Test content generation pipeline basic streaming functionality.
    
    This integration test verifies that:
    1. Streaming works for basic content generation
    2. The complete streaming flow works
    """
    # Create a mock provider for basic streaming
    mock_provider_config = {
        "api_key": "test-key",
        "model": "gpt-4-test",
        "base_url": "https://mock.api.test",
        "timeout": 30,
        "max_retries": 1,
        "response_content": "Hello, this is a streaming response!",
    }
    mock_provider = MockProvider(mock_provider_config)
    
    # Create pipeline with the mock provider
    pipeline = ContentGenerationPipeline(mock_provider)
    
    # Test with a basic prompt
    prompt_obj = PromptObject.create(content="Please help me with a task")
    
    # Stream through the pipeline
    chunks = []
    async for chunk in pipeline.execute_stream(prompt_obj):
        # Extract content from the chunk (in streaming format)
        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if content:  # Only append if there's actual content
            chunks.append(content)
    
    # Combine all chunks to form the full response
    full_response = "".join(chunks)
    
    # Verify the response contains expected content
    assert full_response is not None
    assert len(full_response) > 0
    assert "Hello" in full_response or "hello" in full_response
    
    print(f"Pipeline basic streaming integration test successful! Full response: {full_response}")