"""Test script for additional prompt info functionality."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_additional_prompt_info():
    """Test that additional prompt info is loaded and used correctly."""
    print("=== Testing Additional Prompt Info ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load website only configuration
    result = await chat_interface.process_user_input("load config website_only")
    print(f"Load config result: {result['response']}")
    
    # Check that additional prompt info was loaded
    print(f"Additional prompt info loaded: {bool(ucs_runtime.additional_prompt_info)}")
    if ucs_runtime.additional_prompt_info:
        print(f"Domain context: {ucs_runtime.additional_prompt_info.get('domain_context', 'None')}")
        print(f"Number of instructions: {len(ucs_runtime.additional_prompt_info.get('instructions', []))}")
    
    # Try to check a website to see if the additional prompt info is used
    result = await chat_interface.process_user_input("Can you check if httpbin.org is accessible?")
    print(f"Website check result: {result['response']}")


async def test_dns_config():
    """Test DNS configuration with additional prompt info."""
    print("\n=== Testing DNS Configuration ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load DNS only configuration
    result = await chat_interface.process_user_input("load config dns_only")
    print(f"Load config result: {result['response']}")
    
    # Check that additional prompt info was loaded
    print(f"Additional prompt info loaded: {bool(ucs_runtime.additional_prompt_info)}")
    if ucs_runtime.additional_prompt_info:
        print(f"Domain context: {ucs_runtime.additional_prompt_info.get('domain_context', 'None')}")
        print(f"Number of instructions: {len(ucs_runtime.additional_prompt_info.get('instructions', []))}")
    
    # Try to perform a DNS lookup to see if the additional prompt info is used
    result = await chat_interface.process_user_input("Can you lookup the DNS for google.com?")
    print(f"DNS lookup result: {result['response']}")


if __name__ == "__main__":
    asyncio.run(test_additional_prompt_info())
    asyncio.run(test_dns_config())