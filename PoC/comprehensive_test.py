#!/usr/bin/env python3
"""
More comprehensive test to reproduce the async_success_handler warning.
This tests rapid creation and cleanup of multiple adapter instances which might trigger the issue.
"""
import asyncio
import logging
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter

# Set up logging to see the messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_multiple_instances():
    """Test multiple adapter instances to potentially reproduce the issue"""
    print("Creating multiple adapter instances rapidly...")
    
    adapters = []
    
    # Create multiple adapters and make calls
    for i in range(3):
        print(f"Creating adapter {i+1}...")
        adapter = LiteLLMAdapter(
            model="ollama/qwen3:8b",
            base_url="http://192.168.0.230:11434"
        )
        adapters.append(adapter)
        
        # Make a call with each adapter
        messages = [{"role": "user", "content": f"hi from test {i+1}"}]
        try:
            await adapter.generate_response(messages=messages, temperature=0.7, max_tokens=10)
            print(f"Call {i+1} completed")
        except Exception as e:
            print(f"Call {i+1} got expected error: {e}")
    
    print("Closing all adapters...")
    # Close all adapters
    for i, adapter in enumerate(adapters):
        await adapter.close()
        print(f"Adapter {i+1} closed")
    
    print("All adapters closed.")


async def test_rapid_calls():
    """Test rapid calls to see if that triggers the issue"""
    print("Testing rapid calls with one adapter...")
    
    adapter = LiteLLMAdapter(
        model="ollama/qwen3:8b",
        base_url="http://192.168.0.230:11434"
    )
    
    # Make multiple rapid calls
    for i in range(5):
        messages = [{"role": "user", "content": f"rapid call {i+1}"}]
        try:
            await adapter.generate_response(messages=messages, temperature=0.7, max_tokens=10)
            print(f"Rapid call {i+1} completed")
        except Exception as e:
            print(f"Rapid call {i+1} got expected error: {e}")
    
    print("Closing adapter after rapid calls...")
    await adapter.close()
    print("Adapter closed after rapid calls.")


async def main():
    print("Running comprehensive test to reproduce async_success_handler issue...")
    
    print("\n1. Testing multiple instances...")
    await test_multiple_instances()
    
    print("\n2. Testing rapid calls...")
    await test_rapid_calls()
    
    print("\n3. Final test - creating and immediately closing...")
    adapter = LiteLLMAdapter(
        model="ollama/qwen3:8b",
        base_url="http://192.168.0.230:11434"
    )
    await adapter.close()  # Close immediately after creation
    print("Immediate close test completed.")
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    asyncio.run(main())