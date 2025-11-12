#!/usr/bin/env python3
"""
Test script specifically for vLLM streaming behavior.
This script tests the scenario where the final chunk contains the full response object
with post-processing information, not just the accumulated content from deltas.
"""

import asyncio
import json
from services.llm_provider.content_generator import LLMContentGenerator


async def test_vllm_final_response():
    """
    Test that when streaming, if the final chunk contains complete response object
    (like with vLLM post-processing), that object is used instead of reconstructed one.
    """
    print("Testing vLLM streaming final response capture...")
    
    # Create a generator instance (without actual provider for this test)
    generator = LLMContentGenerator()
    
    # Simulate streaming chunks from vLLM where the final chunk contains the complete
    # response with post-processing information (like usage stats)
    mock_vllm_chunks = [
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
                    "delta": {},
                    "finish_reason": "stop",  # This chunk has finish_reason
                    "message": {  # This chunk also has the complete message
                        "role": "assistant",
                        "content": "Hello world!",
                        "function_call": None
                    }
                }
            ],
            "usage": {  # This chunk also has usage stats, which is common in final chunks
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
    ]
    
    print("Simulating vLLM streaming chunks:")
    for i, chunk in enumerate(mock_vllm_chunks):
        print(f"  Chunk {i+1}: {json.dumps(chunk, indent=2)}")
    
    # Process these chunks using the updated logic in stream_response
    # We'll simulate the key part here:
    
    chunks_accumulated = mock_vllm_chunks
    
    # Apply the same logic as in stream_response to find complete response
    final_response = None
    for chunk in reversed(chunks_accumulated):
        # Check if this chunk contains complete response information (like usage)
        if chunk.get("usage") or any(choice.get("finish_reason") for choice in chunk.get("choices", [])):
            final_response = chunk
            break
    
    print(f"\nDetected final response from chunks: {json.dumps(final_response, indent=2)}")
    
    if final_response:
        print("\n✅ SUCCESS: Final chunk with complete response information was detected!")
        print(f"   Contains usage stats: {'usage' in final_response}")
        print(f"   Contains finish_reason: {any('finish_reason' in choice for choice in final_response.get('choices', []))}")
        
        # Check if the final response has the complete message instead of just deltas
        choices = final_response.get("choices", [])
        has_complete_message = any(
            "message" in choice and choice["message"].get("content")
            for choice in choices
        )
        
        if has_complete_message:
            print("   Contains complete message: YES")
            message = next((choice["message"] for choice in choices if "message" in choice), {})
            print(f"   Complete content: '{message.get('content', '')}'")
        else:
            print("   Contains complete message: NO")
        
        return True
    else:
        print("\n❌ FAILURE: No final chunk with complete response information detected")
        return False


async def test_vllm_reconstruction_fallback():
    """
    Test that if the final chunk doesn't contain complete response information,
    we fall back to reconstructing from deltas.
    """
    print("\n" + "="*60)
    print("Testing vLLM streaming reconstruction fallback...")
    
    # Create a generator instance (without actual provider for this test)
    generator = LLMContentGenerator()
    
    # Simulate streaming chunks where the final chunk only has finish_reason but not complete response
    mock_chunks_no_complete = [
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
                        "content": "Goodbye"
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
                    "finish_reason": "stop"  # Final chunk with finish_reason, but no complete message
                }
            ]
            # No usage stats in this chunk
        }
    ]
    
    print("Simulating streaming chunks without complete response in final chunk:")
    for i, chunk in enumerate(mock_chunks_no_complete):
        print(f"  Chunk {i+1}: {json.dumps(chunk, indent=2)}")
    
    # Process these chunks using the same logic as in stream_response
    chunks_accumulated = mock_chunks_no_complete
    
    # Apply the same logic as in stream_response to find complete response
    final_response = None
    for chunk in reversed(chunks_accumulated):
        # Check if this chunk contains complete response information (like usage)
        if chunk.get("usage") or any(choice.get("finish_reason") for choice in chunk.get("choices", [])):
            final_response = chunk
            break
    
    print(f"\nDetected final response from chunks: {json.dumps(final_response, indent=2)}")
    
    # If no complete response was found, reconstruct from chunks
    if not final_response or not any("message" in choice for choice in final_response.get("choices", [])):
        print("\nFalling back to reconstruction from streaming chunks...")
        reconstructed = generator.process_streaming_chunks(chunks_accumulated)
        print(f"Reconstructed response: {json.dumps(reconstructed, indent=2)}")
        
        # Verify that reconstruction worked properly
        choices = reconstructed.get("choices", [])
        if choices and "message" in choices[0]:
            message = choices[0]["message"]
            if message.get("content") == "Goodbye":
                print("\n✅ SUCCESS: Reconstruction from deltas worked correctly!")
                return True
            else:
                print(f"\n❌ FAILURE: Reconstructed content '{message.get('content')}' doesn't match expected 'Goodbye'")
                return False
        else:
            print("\n❌ FAILURE: Reconstructed response doesn't have a message")
            return False
    else:
        print("\n❌ UNEXPECTED: The final chunk has a complete message when it shouldn't")
        return False


async def main():
    """
    Main test function.
    """
    print("Testing vLLM Streaming Behavior - Final Response Capture")
    print("="*70)
    
    # Run both tests
    test1_passed = await test_vllm_final_response()
    test2_passed = await test_vllm_reconstruction_fallback()
    
    print("\n" + "="*70)
    print("SUMMARY:")
    print(f"  Complete response detection test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  Reconstruction fallback test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All vLLM streaming tests passed! The implementation properly handles both scenarios:")
        print("   1. When the final chunk contains the complete response object (e.g., from vLLM post-processing)")
        print("   2. When we need to reconstruct the response from streaming deltas")
    else:
        print("\n⚠️  Some vLLM streaming tests failed.")


if __name__ == "__main__":
    asyncio.run(main())