"""Test script for configuration loading functionality."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_config_loading():
    """Test loading different configurations."""
    print("=== Testing Configuration Loading ===")
    
    # Initialize UCS runtime
    ucs_runtime = UCSRuntime()
    
    # Load agents (initially empty)
    ucs_runtime.load_all_agents()
    print(f"Initially loaded agents: {list(ucs_runtime.agents.keys())}")
    
    # Test loading website only configuration
    print("\n--- Loading website only configuration ---")
    try:
        ucs_runtime.load_configuration("website_only")
        print(f"Loaded agents: {list(ucs_runtime.agents.keys())}")
    except Exception as e:
        print(f"Error loading website only configuration: {e}")
    
    # Test loading DNS only configuration
    print("\n--- Loading DNS only configuration ---")
    try:
        ucs_runtime.load_configuration("dns_only")
        print(f"Loaded agents: {list(ucs_runtime.agents.keys())}")
    except Exception as e:
        print(f"Error loading DNS only configuration: {e}")
    
    # Test loading combined configuration
    print("\n--- Loading combined configuration ---")
    try:
        ucs_runtime.load_configuration("combined")
        print(f"Loaded agents: {list(ucs_runtime.agents.keys())}")
    except Exception as e:
        print(f"Error loading combined configuration: {e}")
    
    # Test listing available configurations
    print("\n--- Listing available configurations ---")
    configs = ucs_runtime.list_available_configurations()
    print(f"Available configurations: {configs}")


async def test_chat_interface_commands():
    """Test chat interface commands for configuration loading."""
    print("\n\n=== Testing Chat Interface Commands ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_all_agents()  # Load initial agents
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test listing configurations
    print("\n--- Testing 'list configs' command ---")
    result = await chat_interface.process_user_input("list configs")
    print(f"Result: {result['response']}")
    
    # Test listing agents
    print("\n--- Testing 'list agents' command ---")
    result = await chat_interface.process_user_input("list agents")
    print(f"Result: {result['response']}")
    
    # Test loading a configuration
    print("\n--- Testing 'load config' command ---")
    result = await chat_interface.process_user_input("load config website_only")
    print(f"Result: {result['response']}")
    
    # Test listing agents again
    print("\n--- Testing 'list agents' command after loading config ---")
    result = await chat_interface.process_user_input("list agents")
    print(f"Result: {result['response']}")


if __name__ == "__main__":
    asyncio.run(test_config_loading())
    asyncio.run(test_chat_interface_commands())