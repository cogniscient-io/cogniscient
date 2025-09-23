"""Test script for LLM-driven configuration management."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_llm_driven_config_management():
    """Test that the LLM can handle configuration management as tool calls."""
    print("=== Testing LLM-Driven Configuration Management ===")
    
    # Initialize UCS runtime and chat interface with combined configuration
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")  # Load all agents including ConfigManager
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test listing configurations
    print("\n--- Testing 'list configurations' request ---")
    result = await chat_interface.process_user_input("What configurations are available?")
    print(f"Result: {result['response']}")
    
    # Test listing loaded agents
    print("\n--- Testing 'list loaded agents' request ---")
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    print(f"Result: {result['response']}")
    
    # Test loading a specific configuration
    print("\n--- Testing 'load configuration' request ---")
    result = await chat_interface.process_user_input("Please load the website only configuration")
    print(f"Result: {result['response']}")
    
    # Test listing loaded agents after configuration change
    print("\n--- Testing 'list loaded agents' after config change ---")
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    print(f"Result: {result['response']}")


if __name__ == "__main__":
    asyncio.run(test_llm_driven_config_management())