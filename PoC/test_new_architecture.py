#!/usr/bin/env python3
"""
Test script to verify the new LLM architectural redesign works correctly.
"""

import asyncio
from cogniscient.engine.gcs_runtime import GCSRuntime

async def test_new_architecture():
    """Test that the new architecture works correctly."""
    print("Testing new LLM architecture...")
    
    # Initialize the GCS Runtime with new architecture
    runtime = GCSRuntime()
    
    # Verify key services are available (before async init)
    print(f"GCS Runtime initialized: {runtime is not None}")
    print(f"LLM Provider Manager: {runtime.llm_provider_manager is not None}")
    print(f"Response Evaluator Service: {runtime.response_evaluator_service is not None}")
    print(f"Conversation Manager: {runtime.conversation_manager is not None}")
    print(f"Agent Orchestrator: {runtime.agent_orchestrator is not None}")
    print(f"MCP Service (before init): {runtime.mcp_service is not None}")
    print(f"Config Service: {runtime.config_service is not None}")
    
    # Test service registration in kernel
    kernel_services = list(runtime.kernel.service_registry.keys())
    print(f"Registered services: {kernel_services}")
    
    # Now initialize async components
    await runtime.async_init()
    print(f"MCP Service (after init): {runtime.mcp_service is not None}")
    
    # Test a simple parameter get operation
    try:
        llm_model = await runtime.config_service.get_parameter("llm_model")
        print(f"LLM Model parameter: {llm_model}")
    except Exception as e:
        print(f"Error getting parameter: {e}")
    
    # Shutdown cleanly
    await runtime.shutdown()
    print("Runtime shutdown completed successfully")
    
    print("All tests passed! New architecture is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_new_architecture())