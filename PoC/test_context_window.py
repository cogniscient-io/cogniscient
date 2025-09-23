"""Test script for context window size parameter."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_context_window_size():
    """Test context window size parameter and compression."""
    print("=== Testing Context Window Size Parameter ===")
    
    # Initialize UCS runtime and chat interface with custom parameters
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    # Set a small max context size for testing
    orchestrator.max_context_size = 500  # Small size to trigger compression quickly
    
    # Create chat interface with custom parameters
    chat_interface = ChatInterface(
        orchestrator, 
        max_history_length=10,  # Smaller history limit
        compression_threshold=8   # Compress earlier
    )
    
    # Test context window size calculation
    print("\n--- Testing context window size calculation ---")
    initial_size = chat_interface.get_context_window_size()
    print(f"Initial context window size: {initial_size} characters")
    
    # Add some conversation history
    result = await chat_interface.process_user_input("Hello, can you help me with a question?")
    print(f"After first message: {chat_interface.get_context_window_size()} characters")
    
    result = await chat_interface.process_user_input("I'm testing the context window size feature.")
    print(f"After second message: {chat_interface.get_context_window_size()} characters")
    
    # Test setting compression parameters
    print("\n--- Testing compression parameter updates ---")
    print(f"Before update - Max history: {chat_interface.max_history_length}, Compression threshold: {chat_interface.compression_threshold}")
    
    # Update parameters
    chat_interface.set_compression_parameters(max_history_length=15, compression_threshold=12)
    print(f"After update - Max history: {chat_interface.max_history_length}, Compression threshold: {chat_interface.compression_threshold}")
    
    # Test that we can't set invalid parameters
    try:
        chat_interface.set_compression_parameters(max_history_length=5, compression_threshold=10)
        print("ERROR: Should have raised ValueError for invalid parameters")
    except ValueError as e:
        print(f"Correctly caught invalid parameters: {e}")
    
    # Test context size with longer messages
    print("\n--- Testing with longer messages ---")
    long_message = "This is a longer message to test the context window size calculation. " * 9
    result = await chat_interface.process_user_input(long_message)
    context_size = chat_interface.get_context_window_size()
    print(f"Context window size after long message: {context_size} characters")
    
    # Test that we can still interact with the system
    print("\n--- Testing interaction ---")
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    print(f"Result: {result['response'][:100]}...")


if __name__ == "__main__":
    asyncio.run(test_context_window_size())