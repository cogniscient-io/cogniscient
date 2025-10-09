#!/usr/bin/env python3
"""
Debug script to reproduce the async_success_handler issue
"""
import asyncio
import logging
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter

# Set up logging to see the messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("Creating LiteLLM adapter...")
    # Create an instance of the adapter
    adapter = LiteLLMAdapter(
        model="ollama/qwen3:8b",  # Using ollama provider with qwen3:8b model
        base_url="http://192.168.0.230:11434"  # Using the same base URL as in the original error
    )
    
    print("Testing LiteLLM adapter with a simple message...")
    
    # Test basic functionality with a simple message
    messages = [
        {"role": "user", "content": "hi"}
    ]
    
    try:
        print("Making API call with generate_response...")
        response = await adapter.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=10  # Using fewer tokens to make the call faster
        )
        print(f"Response received: {response[:50]}...")  # Show first 50 chars
    except Exception as e:
        print(f"Error during generate_response: {e}")
        import traceback
        traceback.print_exc()
    
    print("About to close adapter...")
    # Close the adapter to trigger any cleanup code
    await adapter.close()
    print("Adapter closed successfully.")

if __name__ == "__main__":
    print("Running debug script...")
    asyncio.run(main())
    print("Main function completed")