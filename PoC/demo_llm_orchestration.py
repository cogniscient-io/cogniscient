"""Demo script for LLM-Enhanced Orchestration."""

import asyncio
import json
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def demo_llm_orchestration():
    """Demonstrate LLM-Enhanced Orchestration capabilities."""
    print("=== LLM-Enhanced Orchestration Demo ===")
    
    # Initialize UCS runtime
    ucs_runtime = UCSRuntime()
    
    # Load agents
    print("Loading agents...")
    ucs_runtime.load_all_agents()
    
    # Initialize LLM orchestrator
    orchestrator = LLMOrchestrator(ucs_runtime)
    
    # Set up parameter ranges for SampleAgentA
    orchestrator.parameter_ranges = {
        "SampleAgentA": {
            "dns_settings.timeout": {"min": 1, "max": 30, "default": 5}
        }
    }
    
    # Initialize chat interface
    chat_interface = ChatInterface(orchestrator)
    
    print("Agents loaded successfully!")
    print(f"Available agents: {list(ucs_runtime.agents.keys())}")
    
    # Demonstrate agent orchestration with adaptive retry logic
    print("\n--- Orchestration Demo ---")
        
    # Demonstrate chat interface\n    print(\"\\\\n--- Chat Interface Demo ---\")\n    user_input = \"What agents are currently loaded?\"\n    response = await chat_interface.process_user_input(user_input)\n    print(f\"User: {user_input}\")\n    if isinstance(response, dict) and \"response_with_tokens\" in response:\n        print(f\"Assistant: {response['response_with_tokens']}\")\n    else:\n        print(f\"Assistant: {response}\")\n    \n    # Demonstrate LLM-driven website checking through chat interface\n    print(\"\\\\n--- LLM-Driven Website Checking Demo ---\")\n    \n    # Test successful website check\n    user_input = \"Can you check if https://httpbin.org/delay/1 is accessible?\"\n    response = await chat_interface.process_user_input(user_input)\n    print(f\"User: {user_input}\")\n    if isinstance(response, dict) and \"response_with_tokens\" in response:\n        print(f\"Assistant: {response['response_with_tokens']}\")\n    else:\n        print(f\"Assistant: {response}\")\n    \n    # Test website check with error\n    user_input = \"Please verify the status of https://this-domain-should-not-exist-12345.com\"\n    response = await chat_interface.process_user_input(user_input)\n    print(f\"User: {user_input}\")\n    if isinstance(response, dict) and \"response_with_tokens\" in response:\n        print(f\"Assistant: {response['response_with_tokens']}\")\n    else:\n        print(f\"Assistant: {response}\")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_llm_orchestration())