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
    
    # Initial attempt
    result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_dns_lookup")
    print(f"Initial orchestration result: {json.dumps(result, indent=2)}")
    
    # Check if we need to retry based on LLM evaluation
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        # Check the evaluation from the LLM orchestrator
        evaluation = result.get("evaluation", {})
        decision = evaluation.get("decision", "failure")
        
        if decision == "success":
            print("Orchestration successful!")
            break
        elif decision == "retry":
            retry_count += 1
            print(f"Retrying... (attempt {retry_count}/{max_retries})")
            
            # Get retry parameters from LLM evaluation
            retry_params = evaluation.get("retry_params", {})
            
            # If retry_params are provided, adapt the parameters
            if retry_params:
                print(f"Adapting parameters: {retry_params}")
                await orchestrator.adapt_parameters("SampleAgentA", retry_params)
            
            # Retry the orchestration
            result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_dns_lookup")
            print(f"Retry #{retry_count} result: {json.dumps(result, indent=2)}")
        else:
            # For any other decision (including "failure"), we'll consider it a failure
            print(f"Orchestration failed with decision: {decision}")
            if "reasoning" in evaluation:
                print(f"Reasoning: {evaluation['reasoning']}")
            break
    else:
        print("Max retries reached. Orchestration failed.")
    
    # Demonstrate failure and retry scenario
    print("\n--- Failure and Retry Demo ---")
    # Temporarily change the target domain to one that will fail
    original_domain = ucs_runtime.agent_configs["SampleAgentA"]["dns_settings"]["target_domain"]
    ucs_runtime.agent_configs["SampleAgentA"]["dns_settings"]["target_domain"] = "test.cogniscient.io"
    
    # Perform orchestration which should fail
    result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_dns_lookup")
    print(f"Orchestration result with failing domain: {json.dumps(result, indent=2)}")
    
    # Check if we need to retry based on LLM evaluation
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        # Check the evaluation from the LLM orchestrator
        evaluation = result.get("evaluation", {})
        decision = evaluation.get("decision", "failure")
        
        if decision == "success":
            print("Orchestration successful!")
            break
        elif decision == "retry":
            retry_count += 1
            print(f"Retrying... (attempt {retry_count}/{max_retries})")
            
            # Get retry parameters from LLM evaluation
            retry_params = evaluation.get("retry_params", {})
            
            # If retry_params are provided, adapt the parameters
            if retry_params:
                print(f"Adapting parameters: {retry_params}")
                await orchestrator.adapt_parameters("SampleAgentA", retry_params)
            
            # Retry the orchestration
            result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_dns_lookup")
            print(f"Retry #{retry_count} result: {json.dumps(result, indent=2)}")
        else:
            # For any other decision (including "failure"), we'll consider it a failure
            print(f"Orchestration failed with decision: {decision}")
            if "reasoning" in evaluation:
                print(f"Reasoning: {evaluation['reasoning']}")
            break
    else:
        print("Max retries reached. Orchestration failed.")
    
    # Restore the original domain
    ucs_runtime.agent_configs["SampleAgentA"]["dns_settings"]["target_domain"] = original_domain
    
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
    
    # Demonstrate LLM-driven website checking through chat interface
    print("\n--- LLM-Driven Website Checking Demo ---")
    
    # Test successful website check
    user_input = "Can you check if https://httpbin.org/delay/1 is accessible?"
    response = await chat_interface.process_user_input(user_input)
    print(f"User: {user_input}")
    print(f"Assistant: {response}")
    
    # Test website check with error
    user_input = "Please verify the status of https://this-domain-should-not-exist-12345.com"
    response = await chat_interface.process_user_input(user_input)
    print(f"User: {user_input}")
    print(f"Assistant: {response}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_llm_orchestration())