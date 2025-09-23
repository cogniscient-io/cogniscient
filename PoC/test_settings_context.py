"""Test script for settings-based context management."""

import asyncio
import os
from src.config.settings import settings
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_settings_based_context_management():
    """Test that context management uses settings from .env file."""
    print("=== Testing Settings-Based Context Management ===")
    
    # Show current settings
    print(f"Current settings:")
    print(f"  MAX_CONTEXT_SIZE: {settings.max_context_size}")
    print(f"  MAX_HISTORY_LENGTH: {settings.max_history_length}")
    print(f"  COMPRESSION_THRESHOLD: {settings.compression_threshold}")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    # Check that the orchestrator uses the settings
    max_context_size = getattr(orchestrator, 'max_context_size', settings.max_context_size)
    print(f"Orchestrator max_context_size: {max_context_size}")
    
    # Create chat interface with default settings
    chat_interface = ChatInterface(orchestrator)
    print(f"Chat interface max_history_length: {chat_interface.max_history_length}")
    print(f"Chat interface compression_threshold: {chat_interface.compression_threshold}")
    
    # Test context window size calculation
    print("\n--- Testing context window size calculation ---")
    initial_size = chat_interface.get_context_window_size()
    print(f"Initial context window size: {initial_size} characters")
    
    # Add some conversation history
    result = await chat_interface.process_user_input("Hello, can you help me with a question?")
    print(f"After first message: {chat_interface.get_context_window_size()} characters")
    
    result = await chat_interface.process_user_input("I'm testing the settings-based context management.")
    print(f"After second message: {chat_interface.get_context_window_size()} characters")
    
    # Test with custom parameters (should override settings)
    print("\n--- Testing with custom parameters ---")
    chat_interface_custom = ChatInterface(orchestrator, max_history_length=5, compression_threshold=3)
    print(f"Custom chat interface max_history_length: {chat_interface_custom.max_history_length}")
    print(f"Custom chat interface compression_threshold: {chat_interface_custom.compression_threshold}")
    
    # Test that we can still interact with the system
    print("\n--- Testing interaction ---")
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    print(f"Result: {result['response'][:100]}...")


if __name__ == "__main__":
    asyncio.run(test_settings_based_context_management())