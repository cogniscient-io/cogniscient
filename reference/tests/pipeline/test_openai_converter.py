"""
Unit tests for OpenAIConverter functionality in the pipeline.
"""
import pytest
from services.llm_provider.providers.openai_converter import OpenAIConverter


def test_openai_converter_initialization():
    """Test that OpenAIConverter initializes properly."""
    converter = OpenAIConverter("gpt-4-test")
    
    assert converter.model == "gpt-4-test"


def test_openai_converter_convert_provider_response_to_kernel():
    """Test that OpenAIConverter can convert responses to kernel format."""
    converter = OpenAIConverter("gpt-4-test")
    
    # Sample OpenAI response
    openai_response = {
        "choices": [
            {
                "message": {
                    "content": "Hello, this is a test response",
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
    
    result = converter.convert_provider_response_to_kernel(openai_response)
    
    # Verify the converted result
    assert result["content"] == "Hello, this is a test response"
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["function"]["name"] == "test_tool"


def test_openai_converter_convert_provider_response_to_kernel_no_tool_calls():
    """Test that OpenAIConverter handles responses without tool calls."""
    converter = OpenAIConverter("gpt-4-test")
    
    # Sample OpenAI response without tool calls
    openai_response = {
        "choices": [
            {
                "message": {
                    "content": "Simple response",
                }
            }
        ]
    }
    
    result = converter.convert_provider_response_to_kernel(openai_response)
    
    # Verify the converted result
    assert result["content"] == "Simple response"
    assert result["tool_calls"] == []


def test_openai_converter_convert_kernel_request_to_provider():
    """Test that OpenAIConverter can convert from kernel format to OpenAI format."""
    converter = OpenAIConverter("gpt-4-test")
    
    # Sample kernel format
    kernel_format = {
        "messages": [
            {"role": "user", "content": "Test prompt"}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param": {"type": "string"}
                        }
                    }
                }
            }
        ]
    }
    
    result = converter.convert_kernel_request_to_provider(kernel_format)
    
    # Verify the converted result
    assert "messages" in result
    assert "model" in result
    assert result["model"] == "gpt-4-test"


def test_openai_converter_convert_kernel_tools_to_provider():
    """Test that OpenAIConverter can convert kernel tools to provider format."""
    converter = OpenAIConverter("gpt-4-test")
    
    # Sample kernel tools
    kernel_tools = [
        {
            "type": "function",
            "function": {
                "name": "tool1",
                "description": "First tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "tool2",
                "description": "Second tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param2": {"type": "string"}
                    }
                }
            }
        }
    ]
    
    result = converter.convert_kernel_tools_to_provider(kernel_tools)
    
    # Verify both tools are converted
    assert len(result) == 2
    assert result[0]["function"]["name"] == "tool1"
    assert result[1]["function"]["name"] == "tool2"