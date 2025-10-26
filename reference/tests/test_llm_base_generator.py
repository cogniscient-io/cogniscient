"""
Test suite for the LLM Provider Base Generator.

This module tests the BaseContentGenerator abstract base class
and its implementations.
"""
import pytest
from typing import Any, Dict, AsyncIterator
from services.llm_provider.base_generator import BaseContentGenerator


class MockContentGenerator(BaseContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing purposes.
    """
    def __init__(self, config: Dict[str, Any] = None):
        # Store the config as an attribute for testing
        self.config = config or {}
        # Set up any attributes needed for testing from the config
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout")
        self.max_retries = self.config.get("max_retries")
    
    async def generate_response(self, prompt: str) -> Any:
        """
        Mock implementation of generate_response.
        """
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        return ResponseObj(
            content=f"Response to: {prompt}",
            tool_calls=[]
        )
    
    async def process_tool_result(self, tool_result: Any, conversation_history: list = None, available_tools: list = None) -> Any:
        """
        Mock implementation of process_tool_result.
        """
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed tool result: {tool_result}")
    
    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt}"


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
    response = await generator.generate_response("Test prompt")
    
    assert hasattr(response, 'content')
    assert hasattr(response, 'tool_calls')
    assert "Test prompt" in response.content


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
    tool_result_mock = "test_tool_result"
    response = await generator.process_tool_result(tool_result_mock)
    
    assert hasattr(response, 'content')
    assert "test_tool_result" in response.content


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
    chunks = []
    async for chunk in generator.stream_response("Test prompt"):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert "Test prompt" in chunks[0]