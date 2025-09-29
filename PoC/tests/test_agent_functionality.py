"""Consolidated tests for agent functionality and additional prompt info."""

import asyncio
import pytest
from unittest.mock import patch
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.orchestrator.chat_interface import ChatInterface


@pytest.mark.asyncio
async def test_agent_functionality_with_different_configs():
    """Test agent functionality with different configurations."""
    # Test DNS only configuration
    ucs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    ucs_runtime.load_configuration("dns_only")
    assert "SampleAgentA" in ucs_runtime.agents
    assert "SampleAgentB" not in ucs_runtime.agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in ucs_runtime.agents
    assert "SystemParametersManager" not in ucs_runtime.agents
    
    # Test website only configuration
    ucs_runtime.load_configuration("website_only")
    assert "SampleAgentB" in ucs_runtime.agents
    assert "SampleAgentA" not in ucs_runtime.agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in ucs_runtime.agents
    assert "SystemParametersManager" not in ucs_runtime.agents
    
    # Test combined configuration
    ucs_runtime.load_configuration("combined")
    assert "SampleAgentA" in ucs_runtime.agents
    assert "SampleAgentB" in ucs_runtime.agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in ucs_runtime.agents
    assert "SystemParametersManager" not in ucs_runtime.agents


@pytest.mark.asyncio
async def test_additional_prompt_info_functionality():
    """Test that additional prompt info is loaded and used correctly."""
    # Initialize UCS runtime and chat interface
    ucs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Load website only configuration
    ucs_runtime.load_configuration("website_only")
    
    # Check that additional prompt info was loaded
    assert len(ucs_runtime.additional_prompt_info) > 0
    assert "domain_context" in ucs_runtime.additional_prompt_info
    assert ucs_runtime.additional_prompt_info["domain_context"] == "Website Monitoring and Diagnostics"
    
    # Test that we can still interact with the system
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    assert "response" in result
    assert "SampleAgentB" in result["response"]


@pytest.mark.asyncio
async def test_dns_only_config_functionality():
    """Test DNS only configuration functionality."""
    # Initialize and load DNS only configuration
    ucs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    ucs_runtime.load_configuration("dns_only")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Check that additional prompt info was loaded
    assert len(ucs_runtime.additional_prompt_info) > 0
    assert "domain_context" in ucs_runtime.additional_prompt_info
    assert ucs_runtime.additional_prompt_info["domain_context"] == "DNS Resolution and Network Diagnostics"
    
    # Test that we can perform a DNS lookup
    # Note: We're not actually testing the functionality of the agent here,
    # just that it's available
    assert "SampleAgentA" in ucs_runtime.agents
    agent_description = ucs_runtime.agents["SampleAgentA"].self_describe()
    assert "perform_dns_lookup" in agent_description["methods"]


@pytest.mark.asyncio
async def test_combined_config_functionality():
    """Test combined configuration functionality."""
    # Initialize and load combined configuration
    ucs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Check that additional prompt info was loaded
    assert len(ucs_runtime.additional_prompt_info) > 0
    assert "domain_context" in ucs_runtime.additional_prompt_info
    assert ucs_runtime.additional_prompt_info["domain_context"] == "Comprehensive Network and Website Diagnostics"
    
    # Test that both agents are available
    assert "SampleAgentA" in ucs_runtime.agents
    assert "SampleAgentB" in ucs_runtime.agents
    
    # Check their methods
    agent_a_description = ucs_runtime.agents["SampleAgentA"].self_describe()
    agent_b_description = ucs_runtime.agents["SampleAgentB"].self_describe()
    
    assert "perform_dns_lookup" in agent_a_description["methods"]
    assert "perform_website_check" in agent_b_description["methods"]


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        asyncio.run(test_agent_functionality_with_different_configs())
        asyncio.run(test_additional_prompt_info_functionality())
        asyncio.run(test_dns_only_config_functionality())
        asyncio.run(test_combined_config_functionality())
        print("All agent functionality tests passed!")