import asyncio
import json
from services.tool_call_streaming_service import tool_call_streaming_service


def test_basic_functionality():
    """Test basic functionality of the ToolCallStreamingService"""
    print("Testing ToolCallStreamingService...")
    
    # Create a sample chunk that represents a streaming response
    operation_id = "test_operation_1"
    
    # Simulate a tool call that comes in chunks
    chunk1 = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_123",
                    "function": {
                        "name": "search",
                        "arguments": "{\"query\": \"how to"
                    }
                }]
            }
        }]
    }
    
    chunk2 = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "function": {
                        "arguments": " write a"
                    }
                }]
            }
        }]
    }
    
    chunk3 = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "function": {
                        "arguments": " test\"}"
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }
    
    # Process the chunks
    result1 = tool_call_streaming_service.process_streaming_chunk(chunk1, operation_id)
    print(f"Result 1: {result1}")
    
    result2 = tool_call_streaming_service.process_streaming_chunk(chunk2, operation_id)
    print(f"Result 2: {result2}")
    
    result3 = tool_call_streaming_service.process_streaming_chunk(chunk3, operation_id)
    print(f"Result 3: {result3}")
    
    # Get the completed tool calls
    completed = tool_call_streaming_service.get_completed_tool_calls(operation_id)
    print(f"Completed tool calls: {completed}")
    
    # Verify the result
    expected_args = {"query": "how to write a test"}
    expected = [{
        'id': 'call_123',
        'name': 'search',
        'args': expected_args,
        'index': 0
    }]
    
    assert len(completed) == 1, f"Expected 1 completed tool call, got {len(completed)}"
    assert completed[0]['name'] == 'search', f"Expected name 'search', got {completed[0]['name']}"
    assert completed[0]['args'] == expected_args, f"Expected args {expected_args}, got {completed[0]['args']}"
    
    print("Test passed!")


def test_json_repair():
    """Test the JSON repair functionality"""
    print("\nTesting JSON repair functionality...")
    
    operation_id = "test_operation_2"
    
    # This chunk has an unclosed string which should be repaired
    chunk = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_456",
                    "function": {
                        "name": "repair_test",
                        "arguments": "{\"test\": \"unclosed string"
                    }
                }]
            }
        }]
    }
    
    result = tool_call_streaming_service.process_streaming_chunk(chunk, operation_id)
    print(f"Result with potentially incomplete JSON: {result}")
    
    # Add the closing part to complete it
    chunk2 = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "function": {
                        "arguments": "\"}"
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }
    
    result2 = tool_call_streaming_service.process_streaming_chunk(chunk2, operation_id)
    print(f"Result after closing: {result2}")
    
    completed = tool_call_streaming_service.get_completed_tool_calls(operation_id)
    print(f"Completed after repair: {completed}")
    
    # The repair should have handled the unclosed string
    assert len(completed) == 1, f"Expected 1 completed tool call, got {len(completed)}"
    assert completed[0]['name'] == 'repair_test', f"Expected name 'repair_test', got {completed[0]['name']}"
    assert completed[0]['args'] == {"test": "unclosed string"}, f"Expected repaired args"
    
    print("JSON repair test passed!")


def test_multiple_tool_calls():
    """Test handling multiple concurrent tool calls"""
    print("\nTesting multiple tool calls...")
    
    operation_id = "test_operation_3"
    
    # Two tool calls in the same response
    chunk1 = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_789",
                    "function": {
                        "name": "first_tool",
                        "arguments": "{\"param\": \"value1\"}"
                    }
                }, {
                    "index": 1,
                    "id": "call_999",
                    "function": {
                        "name": "second_tool",
                        "arguments": "{\"param\": \"value2\"}"
                    }
                }]
            }
        }]
    }
    
    result = tool_call_streaming_service.process_streaming_chunk(chunk1, operation_id)
    print(f"Result for multiple tool calls: {result}")
    
    completed = tool_call_streaming_service.get_completed_tool_calls(operation_id)
    print(f"Completed multiple tool calls: {completed}")
    
    # Should have two completed tool calls
    assert len(completed) == 2, f"Expected 2 completed tool calls, got {len(completed)}"
    
    names = [tc['name'] for tc in completed]
    assert 'first_tool' in names, f"Expected 'first_tool' in names {names}"
    assert 'second_tool' in names, f"Expected 'second_tool' in names {names}"
    
    print("Multiple tool calls test passed!")


if __name__ == "__main__":
    test_basic_functionality()
    test_json_repair()
    test_multiple_tool_calls()
    print("\nAll tests passed!")