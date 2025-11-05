"""
Test suite for the LLM Provider Base Generator.

This module tests the BaseContentGenerator abstract base class
and its implementations.
"""
import pytest
from typing import Any, Dict, AsyncIterator
from services.llm_provider.test_mocks import MockContentGenerator


def test_base_content_generator_initialization():
    """
    Test that BaseContentGenerator initializes properly with config.
    """
    config = {
        "api_key": "test-key-12345",
        "model": "gpt-test-model",
        "base_url": "https://api.test.com/v1",
        "timeout": 30,
        "max_retries": 2
    }
    
    generator = MockContentGenerator(config)
    
    assert generator.config == config
    assert generator.api_key == "test-key-12345"
    assert generator.model == "gpt-test-model"
    assert generator.base_url == "https://api.test.com/v1"
    assert generator.timeout == 30
    assert generator.max_retries == 2


@pytest.mark.asyncio
async def test_base_content_generator_generate_response():
    """
    Test that BaseContentGenerator can generate response properly.
    """
    config = {
        "api_key": "test-key",
        "model": "gpt-test",
        "base_url": "https://api.test.com/v1"
    }
    
    generator = MockContentGenerator(config)
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Test prompt")
    response = await generator.generate_response(prompt_obj)
    
    # In the new architecture, the generator operates on the live prompt object in place
    # and returns None or raises an exception if there's an error
    assert response is None  # Confirm it returns None as per new design
    
    # The prompt object should have been updated in place
    assert hasattr(prompt_obj, 'result_content')
    assert hasattr(prompt_obj, 'tool_calls')
    assert "Test prompt" in prompt_obj.result_content


@pytest.mark.asyncio
async def test_base_content_generator_process_tool_result():
    """
    Test that BaseContentGenerator can process tool results properly.
    """
    config = {
        "api_key": "test-key",
        "model": "gpt-test"
    }
    
    generator = MockContentGenerator(config)
    from gcs_kernel.models import PromptObject
    tool_result_mock = "test_tool_result"
    prompt_obj = PromptObject.create(content="Test prompt")
    response = await generator.process_tool_result(tool_result_mock, prompt_obj)
    
    assert hasattr(response, 'result_content')
    assert "test_tool_result" in response.result_content


@pytest.mark.asyncio
async def test_base_content_generator_stream_response():
    """
    Test that BaseContentGenerator can stream response properly.
    """
    config = {
        "api_key": "test-key",
        "model": "gpt-test"
    }
    
    generator = MockContentGenerator(config)
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Test prompt")
    chunks = []
    async for chunk in generator.stream_response(prompt_obj):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert "Test prompt" in chunks[0]