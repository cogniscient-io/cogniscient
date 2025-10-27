"""
Test suite for the Content Converter Implementation.

This module tests the ContentConverter class and its functionality.
"""
import pytest
from services.llm_provider.providers.openai_converter import ContentConverter
from gcs_kernel.models import ToolResult


def test_content_converter_initialization():
    """
    Test that ContentConverter initializes properly with model.
    """
    converter = ContentConverter("gpt-test-model")
    
    assert converter.model == "gpt-test-model"


def test_convert_kernel_request_to_provider():
    """
    Test converting kernel request format to provider format.
    """
    converter = ContentConverter("gpt-test-model")
    
    kernel_request = {
        "prompt": "Test user prompt",
        "temperature": 0.8,
        "max_tokens": 500
    }
    
    provider_request = converter.convert_kernel_request_to_provider(kernel_request)
    
    # Check that messages format is created correctly
    assert "messages" in provider_request
    assert len(provider_request["messages"]) == 1
    assert provider_request["messages"][0]["role"] == "user"
    assert provider_request["messages"][0]["content"] == "Test user prompt"
    
    # Check that other parameters are preserved
    assert provider_request["model"] == "gpt-test-model"
    assert provider_request["temperature"] == 0.8
    assert provider_request["max_tokens"] == 500


def test_convert_kernel_request_to_provider_with_system_prompt():
    """
    Test converting kernel request format to provider format with system prompt.
    """
    converter = ContentConverter("gpt-test-model")
    
    kernel_request = {
        "prompt": "Test user prompt",
        "system_prompt": "System instructions",
        "temperature": 0.8
    }
    
    provider_request = converter.convert_kernel_request_to_provider(kernel_request)
    
    # Check that system prompt is added as first message
    assert len(provider_request["messages"]) == 2
    assert provider_request["messages"][0]["role"] == "system"
    assert provider_request["messages"][0]["content"] == "System instructions"
    assert provider_request["messages"][1]["role"] == "user"
    assert provider_request["messages"][1]["content"] == "Test user prompt"


def test_convert_kernel_request_to_provider_with_tools():
    """
    Test converting kernel request format to provider format with tools.
    """
    converter = ContentConverter("gpt-test-model")
    
    kernel_request = {
        "prompt": "Test user prompt",
        "tools": [
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    }
                }
            }
        ]
    }
    
    provider_request = converter.convert_kernel_request_to_provider(kernel_request)
    
    # Check that tools are converted to provider format
    assert "tools" in provider_request
    assert len(provider_request["tools"]) == 1
    assert provider_request["tools"][0]["type"] == "function"
    assert provider_request["tools"][0]["function"]["name"] == "test_tool"
    assert provider_request["tools"][0]["function"]["description"] == "A test tool"


def test_convert_provider_response_to_kernel():
    """
    Test converting provider response format to kernel format.
    With passthrough architecture, tool calls remain in OpenAI format.
    """
    converter = ContentConverter("gpt-test-model")
    
    provider_response = {
        "choices": [
            {
                "message": {
                    "content": "Test response content",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": {
                                "name": "test_tool",
                                "arguments": "{\"param1\": \"value1\"}"
                            },
                            "type": "function"
                        }
                    ]
                }
            }
        ]
    }
    
    kernel_response = converter.convert_provider_response_to_kernel(provider_response)
    
    assert kernel_response["content"] == "Test response content"
    assert len(kernel_response["tool_calls"]) == 1
    # With passthrough, tool calls remain in OpenAI format (with function property)
    assert kernel_response["tool_calls"][0]["id"] == "call_123"
    assert kernel_response["tool_calls"][0]["function"]["name"] == "test_tool"
    assert kernel_response["tool_calls"][0]["function"]["arguments"] == "{\"param1\": \"value1\"}"
    assert kernel_response["tool_calls"][0]["type"] == "function"


def test_convert_provider_response_to_kernel_no_tool_calls():
    """
    Test converting provider response format to kernel format without tool calls.
    """
    converter = ContentConverter("gpt-test-model")
    
    provider_response = {
        "choices": [
            {
                "message": {
                    "content": "Simple response content"
                }
            }
        ]
    }
    
    kernel_response = converter.convert_provider_response_to_kernel(provider_response)
    
    assert kernel_response["content"] == "Simple response content"
    assert kernel_response["tool_calls"] == []


def test_convert_provider_response_to_kernel_empty_choices():
    """
    Test converting provider response format to kernel format with empty choices.
    """
    converter = ContentConverter("gpt-test-model")
    
    provider_response = {
        "choices": []
    }
    
    kernel_response = converter.convert_provider_response_to_kernel(provider_response)
    
    assert kernel_response["content"] == ""
    assert kernel_response["tool_calls"] == []


def test_convert_kernel_tools_to_provider():
    """
    Test converting kernel tools to provider format.
    """
    converter = ContentConverter("gpt-test-model")
    
    kernel_tools = [
        {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }
    ]
    
    provider_tools = converter.convert_kernel_tools_to_provider(kernel_tools)
    
    assert len(provider_tools) == 1
    assert provider_tools[0]["type"] == "function"
    assert provider_tools[0]["function"]["name"] == "test_tool"
    assert provider_tools[0]["function"]["description"] == "A test tool"
    assert provider_tools[0]["function"]["parameters"] == kernel_tools[0]["parameters"]


def test_convert_kernel_tool_result_to_provider():
    """
    Test converting kernel ToolResult to provider format.
    """
    tool_result = ToolResult(
        tool_name="test_tool",
        llm_content="Test result for LLM",
        return_display="Test result for user",
        success=True
    )
    
    converter = ContentConverter("gpt-test-model")
    provider_tool_result = converter.convert_kernel_tool_result_to_provider(tool_result)
    
    assert provider_tool_result["role"] == "tool"
    assert provider_tool_result["content"] == "Test result for user"
    assert provider_tool_result["tool_call_id"] == "test_tool"