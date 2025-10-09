#!/usr/bin/env python3
"""
Simple test script to reproduce the async_success_handler warning
"""
import asyncio
import logging
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter

# Set up logging to see the messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_basic():
    print("Creating LiteLLM adapter...")
    adapter = LiteLLMAdapter(
        model="ollama/qwen3:8b",
        base_url="http://192.168.0.230:11434"
    )
    
    print("Sending simple message...")
    messages = [{"role": "user", "content": "hi"}]
    
    try:
        # Just make a call without storing the result to see if the issue occurs
        await adapter.generate_response(messages=messages, temperature=0.7, max_tokens=10)
    except Exception as e:
        print(f"Got expected error: {e}")
    
    print("About to close adapter...")
    await adapter.close()
    print("Adapter closed.")

if __name__ == "__main__":
    print("Running simple test to reproduce the issue...")
    asyncio.run(test_basic())
    print("Test completed.")