#!/usr/bin/env python3
"""
Test script to verify streaming behavior in the LLM Content Generator.
This script simulates the streaming process to check if the final message object
is properly captured after the stream ends.
"""

import asyncio
import json
from services.llm_provider.content_generator import LLMContentGenerator


async def test_streaming_reconstruction():
    """
    Test that streaming chunks are properly reconstructed into a full response.
    """
    print("Testing streaming reconstruction...")
    
    # Create a generator instance (without actual provider for this test)
    generator = LLMContentGenerator()
    
    # Simulate streaming chunks as they would come from an LLM API
    # This simulates what OpenAI would return during a streaming response
    mock_streaming_chunks = [
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": "Hello"
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": " world"
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "!"
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"  # Final chunk with finish_reason
                }
            ]
        }
    ]
    
    print("Simulating streaming chunks:")
    for i, chunk in enumerate(mock_streaming_chunks):
        print(f"  Chunk {i+1}: {json.dumps(chunk, indent=2)}")
    
    # Process these chunks using the same logic as in stream_response
    full_response = generator.process_streaming_chunks(mock_streaming_chunks)
    
    print("\nReconstructed full response:")
    print(json.dumps(full_response, indent=2))
    
    # Check that content was properly accumulated
    choices = full_response.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        finish_reason = choices[0].get("finish_reason", "")
        
        print(f"\nAccumulated content: '{content}'")
        print(f"Finish reason: {finish_reason}")
        
        # Verify that the content matches what we expect
        if content == "Hello world!" and finish_reason == "stop":
            print("\n✅ SUCCESS: Content and finish reason properly reconstructed!")
            return True
        else:
            print(f"\n❌ FAILURE: Expected 'Hello world!' with finish_reason 'stop', got '{content}' with finish_reason '{finish_reason}'")
            return False
    else:
        print("\n❌ FAILURE: No choices found in reconstructed response")
        return False


async def test_tool_call_streaming():
    """
    Test streaming with tool calls to ensure they're also properly reconstructed.
    """
    print("\n" + "="*60)
    print("Testing tool call streaming reconstruction...")
    
    # Create a generator instance (without actual provider for this test)
    generator = LLMContentGenerator()
    
    # Simulate streaming chunks with tool calls
    mock_tool_call_chunks = [
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant"
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "I'll call the search function"
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_123",
                                "function": {
                                    "name": "search"
                                },
                                "type": "function"
                            }
                        ]
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {
                                    "arguments": "{\"query\": \"python streaming\"}"
                                }
                            }
                        ]
                    },
                    "finish_reason": None
                }
            ]
        },
        {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1694268190,
            "model": "gpt-4-turbo",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "tool_calls"  # Final chunk with tool_calls finish_reason
                }
            ]
        }
    ]
    
    print("Simulating tool call streaming chunks:")
    for i, chunk in enumerate(mock_tool_call_chunks):
        print(f"  Chunk {i+1}: {json.dumps(chunk, indent=2)[:200]}...")  # Truncate for readability
    
    # Process these chunks using the same logic as in stream_response
    full_response = generator.process_streaming_chunks(mock_tool_call_chunks)
    
    print("\nReconstructed full response:")
    print(json.dumps(full_response, indent=2))
    
    # Check that both content and tool calls were properly accumulated
    choices = full_response.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])
        finish_reason = choices[0].get("finish_reason", "")
        
        print(f"\nAccumulated content: '{content}'")
        print(f"Accumulated tool calls: {tool_calls}")
        print(f"Finish reason: {finish_reason}")
        
        # Verify that the content, tool calls, and finish reason match what we expect
        expected_content = "I'll call the search function"
        expected_tool_call_name = "search"
        expected_tool_call_args = "{\"query\": \"python streaming\"}"
        
        if (content == expected_content and 
            len(tool_calls) == 1 and 
            tool_calls[0]["function"]["name"] == expected_tool_call_name and
            expected_tool_call_args in tool_calls[0]["function"]["arguments"] and
            finish_reason == "tool_calls"):
            print("\n✅ SUCCESS: Tool calls and content properly reconstructed!")
            return True
        else:
            print(f"\n❌ FAILURE: Tool call reconstruction failed")
            print(f"  Expected content: '{expected_content}', got: '{content}'")
            print(f"  Expected tool call name: '{expected_tool_call_name}', got: '{tool_calls[0]['function']['name'] if tool_calls else 'None'}")
            print(f"  Expected finish_reason: 'tool_calls', got: '{finish_reason}'")
            return False
    else:
        print("\n❌ FAILURE: No choices found in reconstructed response")
        return False


async def main():
    """
    Main test function.
    """
    print("Testing LLM Content Generator streaming behavior")
    print("="*60)
    
    # Run both tests
    test1_passed = await test_streaming_reconstruction()
    test2_passed = await test_tool_call_streaming()
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Content streaming test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  Tool call streaming test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The streaming implementation properly captures the final message object.")
    else:
        print("\n⚠️  Some tests failed. There may be issues with final message capture.")


if __name__ == "__main__":
    asyncio.run(main())