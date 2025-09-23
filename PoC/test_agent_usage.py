"""Test script for configuration loading and agent usage."""

import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


async def test_dns_only_config():
    """Test DNS only configuration."""
    print("=== Testing DNS Only Configuration ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load DNS only configuration
    result = await chat_interface.process_user_input("load config dns_only")
    print(f"Load config result: {result['response']}")
    
    # Try to perform a DNS lookup
    result = await chat_interface.process_user_input("Can you lookup the DNS for google.com?")
    print(f"DNS lookup result: {result['response']}")


async def test_website_only_config():
    """Test website only configuration."""
    print("\n=== Testing Website Only Configuration ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load website only configuration
    result = await chat_interface.process_user_input("load config website_only")
    print(f"Load config result: {result['response']}")
    
    # Try to check a website
    result = await chat_interface.process_user_input("Can you check if httpbin.org is accessible?")
    print(f"Website check result: {result['response']}")


async def test_combined_config():
    """Test combined configuration."""
    print("\n=== Testing Combined Configuration ===")
    
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load combined configuration
    result = await chat_interface.process_user_input("load config combined")
    print(f"Load config result: {result['response']}")
    
    # Try to check a website
    result = await chat_interface.process_user_input("Can you check if httpbin.org is accessible?")
    print(f"Website check result: {result['response']}")
    
    # Try to perform a DNS lookup
    result = await chat_interface.process_user_input("Can you lookup the DNS for google.com?")
    print(f"DNS lookup result: {result['response']}")


if __name__ == "__main__":
    asyncio.run(test_dns_only_config())
    asyncio.run(test_website_only_config())
    asyncio.run(test_combined_config())