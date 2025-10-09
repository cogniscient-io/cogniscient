#!/usr/bin/env python3
"""
Test script to verify the LiteLLM adapter fix for async_success_handler warning
"""
import asyncio
import logging
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter

# Set up logging to see the messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    # Create an instance of the adapter
    # For Ollama, the model format should be "ollama/[model_name]"
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
        response = await adapter.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during generate_response: {e}")
        # Continue with cleanup anyway
    
    print("Closing adapter...")
    # Close the adapter to trigger any cleanup code
    await adapter.close()
    print("Adapter closed successfully.")

if __name__ == "__main__":
    asyncio.run(main())