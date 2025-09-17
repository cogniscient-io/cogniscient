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
    
    # Demonstrate agent orchestration
    print("\n--- Orchestration Demo ---")
    result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_dns_lookup")
    print(f"Orchestration result: {json.dumps(result, indent=2)}")
    
    # Demonstrate parameter adaptation
    print("\n--- Parameter Adaptation Demo ---")
    changes = {"dns_settings.timeout": 10}
    adaptation_result = await orchestrator.adapt_parameters("SampleAgentA", changes)
    print(f"Parameter adaptation result: {adaptation_result}")
    print(f"New timeout value: {ucs_runtime.agent_configs['SampleAgentA']['dns_settings']['timeout']}")
    
    # Demonstrate chat interface
    print("\n--- Chat Interface Demo ---")
    user_input = "What agents are currently loaded?"
    response = await chat_interface.process_user_input(user_input)
    print(f"User: {user_input}")
    print(f"Assistant: {response}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_llm_orchestration())