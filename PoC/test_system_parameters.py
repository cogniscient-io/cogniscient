"""Test script for system parameters manager."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_system_parameters_manager():
    """Test the system parameters manager agent."""
    print("=== Testing System Parameters Manager ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test getting system parameters
    print("\n--- Testing get_system_parameters ---")
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
        print(f"System parameters: {result}")
    except Exception as e:
        print(f"Error getting system parameters: {e}")
    
    # Test getting parameter descriptions
    print("\n--- Testing get_parameter_descriptions ---")
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "get_parameter_descriptions")
        print(f"Parameter descriptions: {result}")
    except Exception as e:
        print(f"Error getting parameter descriptions: {e}")
    
    # Test setting a parameter
    print("\n--- Testing set_system_parameter ---")
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "set_system_parameter", 
                                     parameter_name="max_history_length", parameter_value="10")
        print(f"Set parameter result: {result}")
    except Exception as e:
        print(f"Error setting parameter: {e}")
    
    # Test getting parameters after setting one
    print("\n--- Testing get_system_parameters after setting ---")
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
        print(f"System parameters after setting: {result}")
    except Exception as e:
        print(f"Error getting system parameters: {e}")


if __name__ == "__main__":
    asyncio.run(test_system_parameters_manager())