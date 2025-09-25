"""Consolidated tests for configuration management functionality."""

import asyncio
import os
import json
import pytest
from unittest.mock import patch, Mock
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface
from src.config.settings import settings


@pytest.mark.asyncio
async def test_config_loading_functionality():
    """Test loading different configurations."""
    # Initialize UCS runtime
    ucs_runtime = UCSRuntime()
    
    # Load agents (initially empty)
    ucs_runtime.load_all_agents()
    initial_agents = list(ucs_runtime.agents.keys())
    
    # Test loading website only configuration
    ucs_runtime.load_configuration("website_only")
    website_agents = list(ucs_runtime.agents.keys())
    assert "SampleAgentB" in website_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in website_agents
    assert "SystemParametersManager" not in website_agents
    assert "SampleAgentA" not in website_agents
    
    # Test loading DNS only configuration
    ucs_runtime.load_configuration("dns_only")
    dns_agents = list(ucs_runtime.agents.keys())
    assert "SampleAgentA" in dns_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in dns_agents
    assert "SystemParametersManager" not in dns_agents
    assert "SampleAgentB" not in dns_agents
    
    # Test loading combined configuration
    ucs_runtime.load_configuration("combined")
    combined_agents = list(ucs_runtime.agents.keys())
    assert "SampleAgentA" in combined_agents
    assert "SampleAgentB" in combined_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in combined_agents
    assert "SystemParametersManager" not in combined_agents
    
    # Test listing available configurations
    configs = ucs_runtime.list_available_configurations()
    assert "dns_only" in configs
    assert "website_only" in configs
    assert "combined" in configs


@pytest.mark.asyncio
async def test_config_manager_descriptions():
    """Test that config manager reads descriptions from config files."""
    # Initialize UCS runtime
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    # Test listing configurations - still accessible through the same interface
    result = ucs_runtime.run_agent("ConfigManager", "list_configurations")
    assert result["status"] == "success"
    assert "configurations" in result
    assert len(result["configurations"]) > 0
    
    # Check that descriptions are included
    for config in result["configurations"]:
        assert "name" in config
        assert "description" in config
        assert isinstance(config["description"], str)
        assert len(config["description"]) > 0


@pytest.mark.asyncio
async def test_llm_driven_config_management():
    """Test that LLM can handle configuration management as tool calls."""
    # Initialize UCS runtime and chat interface
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test listing configurations (should use ConfigManager agent)
    result = await chat_interface.process_user_input("What configurations are available?")
    assert "response" in result
    # The response should mention the configurations or the ConfigManager agent
    
    # Test listing loaded agents
    result = await chat_interface.process_user_input("What agents are currently loaded?")
    assert "response" in result
    # Confirm that actual agents (not system services) are mentioned in the response
    assert "SampleAgentA" in result["response"] or "SampleAgentB" in result["response"]
    
    # Test loading a specific configuration
    result = await chat_interface.process_user_input("Please load the website only configuration")
    assert "response" in result


def test_environment_variable_overrides():
    """Test that environment variables override default settings."""
    import importlib
    # Temporarily modify environment variables
    import os
    original_context_size = os.environ.get('MAX_CONTEXT_SIZE', None)
    original_history_length = os.environ.get('MAX_HISTORY_LENGTH', None)
    
    try:
        # Set environment variables
        os.environ['MAX_CONTEXT_SIZE'] = '4000'
        os.environ['MAX_HISTORY_LENGTH'] = '10'
        
        # Reload the settings module to pick up new values
        importlib.reload(__import__('src.config.settings', fromlist=['settings']))
        from src.config.settings import settings
        
        # Verify the new values
        assert settings.max_context_size == 4000
        assert settings.max_history_length == 10
    finally:
        # Restore original values
        if original_context_size is not None:
            os.environ['MAX_CONTEXT_SIZE'] = original_context_size
        else:
            os.environ.pop('MAX_CONTEXT_SIZE', None)
        
        if original_history_length is not None:
            os.environ['MAX_HISTORY_LENGTH'] = original_history_length
        else:
            os.environ.pop('MAX_HISTORY_LENGTH', None)
        
        # Reload settings to restore defaults
        importlib.reload(__import__('src.config.settings', fromlist=['settings']))
        from src.config.settings import settings


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        asyncio.run(test_config_loading_functionality())
        asyncio.run(test_config_manager_descriptions())
        asyncio.run(test_llm_driven_config_management())
        test_environment_variable_overrides()
        print("All configuration tests passed!")