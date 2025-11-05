"""
Test script to verify ToolCall conversion methods.
"""

import pytest
from gcs_kernel.tool_call_model import ToolCall


@pytest.mark.asyncio
async def test_from_openai_format():
    """Test creating a ToolCall from OpenAI format dictionary."""
    openai_format = {
        "id": "call_123",
        "function": {
            "name": "test_tool",
            "arguments": '{"param1": "value1", "param2": 42}'
        }
    }
    
    tool_call = ToolCall.from_openai_format(openai_format)
    
    assert tool_call.id == "call_123"
    assert tool_call.name == "test_tool"
    assert tool_call.function["name"] == "test_tool"
    assert tool_call.function["arguments"] == '{"param1": "value1", "param2": 42}'
    assert tool_call.arguments == {"param1": "value1", "param2": 42}


@pytest.mark.asyncio
async def test_to_openai_format():
    """Test converting a ToolCall to OpenAI format dictionary."""
    tool_call = ToolCall(
        id="call_456",
        function={
            "name": "another_tool",
            "arguments": '{"paramA": "valueA", "paramB": true}'
        }
    )
    
    openai_format = tool_call.to_openai_format()
    
    assert openai_format["id"] == "call_456"
    assert openai_format["function"]["name"] == "another_tool"
    assert openai_format["function"]["arguments"] == '{"paramA": "valueA", "paramB": true}'


@pytest.mark.asyncio
async def test_ensure_openai_format_with_dict():
    """Test ensure_openai_format with an OpenAI format dictionary."""
    original_dict = {
        "id": "call_789",
        "function": {
            "name": "tool_name",
            "arguments": '{"test": "value"}'
        }
    }
    
    # The ensure_openai_format should add the 'type' field if not present
    expected_dict = {
        "id": "call_789",
        "function": {
            "name": "tool_name",
            "arguments": '{"test": "value"}'
        },
        "type": "function"  # Added by ensure_openai_format
    }
    
    result = ToolCall.ensure_openai_format(original_dict)
    
    assert result == expected_dict
    assert isinstance(result, dict)
    assert "id" in result
    assert "function" in result
    assert "type" in result
    assert result["function"]["name"] == "tool_name"
    assert result["type"] == "function"


@pytest.mark.asyncio
async def test_ensure_openai_format_with_toolcall():
    """Test ensure_openai_format with a ToolCall object."""
    tool_call = ToolCall(
        id="call_abc",
        function={
            "name": "example_tool",
            "arguments": '{"example": "data"}'
        }
    )
    
    result = ToolCall.ensure_openai_format(tool_call)
    
    assert isinstance(result, dict)
    assert result["id"] == "call_abc"
    assert result["function"]["name"] == "example_tool"
    assert result["function"]["arguments"] == '{"example": "data"}'


@pytest.mark.asyncio
async def test_ensure_openai_format_with_invalid_input():
    """Test ensure_openai_format with invalid input."""
    # Test with an object that doesn't have the expected attributes
    class FakeObject:
        def __init__(self):
            self.id = "fake_id"
            self.name = "fake_name"
            self.arguments_json = "fake_args"  # This is what the method looks for first
    
    fake_obj = FakeObject()
    result = ToolCall.ensure_openai_format(fake_obj)
    
    assert isinstance(result, dict)
    assert result["id"] == "fake_id"
    assert result["function"]["name"] == "fake_name"
    assert result["function"]["arguments"] == "fake_args"


@pytest.mark.asyncio
async def test_comprehensive_conversion_workflow():
    """Test a complete conversion workflow: dict -> ToolCall -> dict -> ToolCall."""
    # Start with an OpenAI format dictionary (without type field)
    original_openai_dict = {
        "id": "call_workflow",
        "function": {
            "name": "workflow_tool",
            "arguments": '{"step": 1, "data": "initial"}'
        }
    }
    
    # The expected dict after conversion should include the type field
    expected_openai_dict = {
        "id": "call_workflow",
        "function": {
            "name": "workflow_tool",
            "arguments": '{"step": 1, "data": "initial"}'
        },
        "type": "function"
    }
    
    # Convert to ToolCall object
    tool_call_obj = ToolCall.from_openai_format(original_openai_dict)
    assert tool_call_obj.id == "call_workflow"
    assert tool_call_obj.name == "workflow_tool"
    
    # Convert back to OpenAI format - should include type field
    converted_back_dict = tool_call_obj.to_openai_format()
    assert converted_back_dict == expected_openai_dict
    
    # Convert using ensure_openai_format (should handle both dict and object and add type field)
    ensure_result_from_dict = ToolCall.ensure_openai_format(original_openai_dict)
    assert ensure_result_from_dict == expected_openai_dict
    
    ensure_result_from_obj = ToolCall.ensure_openai_format(tool_call_obj)
    assert ensure_result_from_obj == expected_openai_dict


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("Testing ToolCall conversion methods...")
        
        await test_from_openai_format()
        print("✓ test_from_openai_format passed")
        
        await test_to_openai_format()
        print("✓ test_to_openai_format passed")
        
        await test_ensure_openai_format_with_dict()
        print("✓ test_ensure_openai_format_with_dict passed")
        
        await test_ensure_openai_format_with_toolcall()
        print("✓ test_ensure_openai_format_with_toolcall passed")
        
        await test_ensure_openai_format_with_invalid_input()
        print("✓ test_ensure_openai_format_with_invalid_input passed")
        
        await test_comprehensive_conversion_workflow()
        print("✓ test_comprehensive_conversion_workflow passed")
        
        print("\nAll conversion tests passed! ✓")
    
    asyncio.run(run_tests())