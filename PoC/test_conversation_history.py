"""Test script for conversation history management."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_conversation_history_management():
    """Test conversation history clearing and compression."""
    print("=== Testing Conversation History Management ===")
    
    # Initialize UCS runtime and chat interface with combined configuration
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")  # Load all agents including ConfigManager
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test conversation history building
    print("\n--- Building conversation history ---")
    for i in range(5):
        result = await chat_interface.process_user_input(f"Hello, this is message {i+1}")
        print(f"Message {i+1}: {result['response'][:50]}...")
    
    print(f"Conversation history length: {len(chat_interface.conversation_history)}")
    
    # Test context compression by adding more messages
    print("\n--- Testing context compression ---")
    for i in range(10):
        result = await chat_interface.process_user_input(f"Additional message {i+1} for compression test")
        print(f"Additional message {i+1}: {result['response'][:50]}...")
    
    print(f"Conversation history length after compression: {len(chat_interface.conversation_history)}")
    
    # Test configuration change clearing conversation history
    print("\n--- Testing configuration change clears history ---")
    print(f"History length before config change: {len(chat_interface.conversation_history)}")
    
    # Load a different configuration
    ucs_runtime.load_configuration("website_only")
    
    print(f"History length after config change: {len(chat_interface.conversation_history)}")
    if len(chat_interface.conversation_history) == 0:
        print("Conversation history successfully cleared!")
    else:
        print("Conversation history was not cleared.")
    
    # Test that we can still interact with the system
    print("\n--- Testing interaction after config change ---")
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    print(f"Result: {result['response']}")


if __name__ == "__main__":
    asyncio.run(test_conversation_history_management())