"""Unit tests for configuration management functionality."""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface


@pytest.mark.asyncio
async def test_config_loading_functionality():
    """Test loading different configurations."""
    # Initialize UCS runtime with plugin config and agent directories
    # NOTE: In production, these paths could be updated via system parameters service
    import os
    plugin_configs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "sample_internal", "config")
    plugin_agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "sample_internal", "agents")
    ucs_runtime = GCSRuntime(config_dir=plugin_configs_dir, agents_dir=plugin_agents_dir)
    
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
    # Initialize UCS runtime with plugin config and agent directories
    # NOTE: In production, these paths could be updated via system parameters service
    import os
    plugin_configs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "sample_internal", "config")
    plugin_agents_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins", "sample_internal", "agents")
    ucs_runtime = GCSRuntime(config_dir=plugin_configs_dir, agents_dir=plugin_agents_dir)
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
    """Test LLM-driven configuration management via MCP services."""
    # Initialize system
    ucs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    ucs_runtime.load_configuration("combined")
    
    # Get the contextual LLM service which now handles MCP integration
    contextual_llm_service = ucs_runtime.llm_service
    
    # Verify that the contextual LLM service has MCP capabilities properly configured
    assert contextual_llm_service.mcp_client_service is not None
    
    # Test that we can format the system service capabilities
    capabilities_str = contextual_llm_service._format_system_service_capabilities()
    assert "MCP" in capabilities_str
    assert "config.list_configurations" in capabilities_str
    assert "config.load_configuration" in capabilities_str
    
    # Test that we can get all available tools including MCP tools
    all_tools = contextual_llm_service.get_all_available_tools()
    assert "mcp_tools" in all_tools
    
    # Verify that MCP tools for configuration management are available
    mcp_tools = all_tools["mcp_tools"]
    assert "mcp.connect_external_agent" in mcp_tools
    assert "mcp.list_connected_agents" in mcp_tools
    assert "mcp.list_external_agent_capabilities" in mcp_tools
    assert "mcp.call_external_agent_tool" in mcp_tools


def test_agents_dir_system_parameter():
    """Test that agents_dir can be configured via system parameters service."""
    
    # Initialize UCS runtime with the original default path
    ucs_runtime = GCSRuntime(config_dir=".", agents_dir="plugins/sample_internal/agents")
    
    # Verify initial agents_dir
    assert ucs_runtime.agents_dir == "plugins/sample_internal/agents"
    assert ucs_runtime.local_agent_manager.agents_dir == "plugins/sample_internal/agents"
    assert ucs_runtime.local_agent_manager.config_manager.agents_dir == "plugins/sample_internal/agents"
    
    # Check that the agents_dir parameter is available in system parameters
    params_result = ucs_runtime.system_parameters_service.get_system_parameters()
    assert params_result["status"] == "success"
    assert "agents_dir" in params_result["parameters"]
    assert params_result["parameters"]["agents_dir"] == "plugins/sample_internal/agents"
    
    # Create the target directory to ensure it exists
    import os
    os.makedirs("custom/agents/path", exist_ok=True)
    
    # Change agents_dir via system parameters service
    change_result = ucs_runtime.system_parameters_service.set_system_parameter("agents_dir", "custom/agents/path")
    assert change_result["status"] == "success"
    
    # Verify that the change was applied to the runtime
    assert ucs_runtime.agents_dir == "custom/agents/path"
    assert ucs_runtime.local_agent_manager.agents_dir == "custom/agents/path"
    assert ucs_runtime.local_agent_manager.config_manager.agents_dir == "custom/agents/path"
    
    # Get updated system parameters to verify the change
    updated_params_result = ucs_runtime.system_parameters_service.get_system_parameters()
    assert updated_params_result["status"] == "success"
    assert updated_params_result["parameters"]["agents_dir"] == "custom/agents/path"
    
    # Test that the get_agents_dir method in AgentConfigManager returns the updated value
    config_manager_agents_dir = ucs_runtime.local_agent_manager.config_manager.get_agents_dir()
    assert config_manager_agents_dir == "custom/agents/path"
    
    # Test that the LocalAgentManager method also works
    lam_agents_dir = ucs_runtime.local_agent_manager._get_current_agents_dir()
    assert lam_agents_dir == "custom/agents/path"


def test_config_dir_system_parameter():
    """Test that config_dir can be configured via system parameters service."""
    
    # Initialize UCS runtime with default settings
    ucs_runtime = GCSRuntime()
    
    # Set the agents_dir to tests directory for this specific test 
    ucs_runtime.system_parameters_service.set_system_parameter('agents_dir', 'tests')
    
    # Verify initial config_dir
    assert ucs_runtime.config_dir == "."
    assert ucs_runtime.config_service.config_dir == "."
    
    # Check that the config_dir parameter is available in system parameters
    params_result = ucs_runtime.system_parameters_service.get_system_parameters()
    assert params_result["status"] == "success"
    assert "config_dir" in params_result["parameters"]
    assert params_result["parameters"]["config_dir"] == "."
    
    # Create the target directory to ensure it exists
    import os
    os.makedirs("/tmp/test_config_dir", exist_ok=True)
    
    # Change config_dir via system parameters service
    change_result = ucs_runtime.system_parameters_service.set_system_parameter("config_dir", "/tmp/test_config_dir")
    assert change_result["status"] == "success"
    
    # Verify that the change was applied to the runtime
    assert ucs_runtime.config_dir == "/tmp/test_config_dir"
    assert ucs_runtime.config_service.config_dir == "/tmp/test_config_dir"
    
    # Get updated system parameters to verify the change
    updated_params_result = ucs_runtime.system_parameters_service.get_system_parameters()
    assert updated_params_result["status"] == "success"
    assert updated_params_result["parameters"]["config_dir"] == "/tmp/test_config_dir"


def test_llm_config_system_parameter():
    """Test that LLM configuration parameters can be updated via system parameters service."""
    from cogniscient.engine.config.settings import settings
    
    # Create a copy of the original values to restore later
    original_llm_model = settings.llm_model
    original_llm_base_url = settings.llm_base_url
    
    try:
        # Initialize UCS runtime with default settings
        ucs_runtime = GCSRuntime()
        
        # Set the agents_dir to tests directory for this specific test 
        ucs_runtime.system_parameters_service.set_system_parameter('agents_dir', 'tests')
        
        # Check that initial LLM settings are available in system parameters
        params_result = ucs_runtime.system_parameters_service.get_system_parameters()
        assert params_result["status"] == "success"
        assert "llm_model" in params_result["parameters"]
        assert "llm_base_url" in params_result["parameters"]
        
        # Change LLM model via system parameters service
        model_result = ucs_runtime.system_parameters_service.set_system_parameter(
            "llm_model", "ollama_chat/llama3:70b"
        )
        assert model_result["status"] == "success"
        
        # Change LLM base URL via system parameters service
        url_result = ucs_runtime.system_parameters_service.set_system_parameter(
            "llm_base_url", "http://newhost:11434"
        )
        assert url_result["status"] == "success"
        
        # Verify that the settings were updated
        assert settings.llm_model == "ollama_chat/llama3:70b"
        assert settings.llm_base_url == "http://newhost:11434"
        
        # Get updated system parameters to verify the changes
        updated_params_result = ucs_runtime.system_parameters_service.get_system_parameters()
        assert updated_params_result["status"] == "success"
        assert updated_params_result["parameters"]["llm_model"] == "ollama_chat/llama3:70b"
        assert updated_params_result["parameters"]["llm_base_url"] == "http://newhost:11434"
    finally:
        # Restore original settings
        settings.llm_model = original_llm_model
        settings.llm_base_url = original_llm_base_url


def test_environment_variable_overrides():
    """Test that environment variables override default settings."""
    import importlib
    # Temporarily modify environment variables
    import os
    original_context_size = os.environ.get('MAX_CONTEXT_SIZE', None)
    original_history_length = os.environ.get('MAX_HISTORY_LENGTH', None)
    original_compression_threshold = os.environ.get('COMPRESSION_THRESHOLD', None)
    
    try:
        # Set environment variables
        os.environ['MAX_CONTEXT_SIZE'] = '4000'
        os.environ['MAX_HISTORY_LENGTH'] = '20'  # Use 20 instead of 10 to avoid conflict with default compression_threshold of 15
        os.environ['COMPRESSION_THRESHOLD'] = '10'  # Set compression threshold to be less than max_history_length
        
        # Reload the settings module to pick up new values
        importlib.reload(__import__('cogniscient.engine.config.settings', fromlist=['settings']))
        from cogniscient.engine.config.settings import settings
        
        # Verify the new values
        assert settings.max_context_size == 4000
        assert settings.max_history_length == 20
        assert settings.compression_threshold == 10
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
            
        if original_compression_threshold is not None:
            os.environ['COMPRESSION_THRESHOLD'] = original_compression_threshold
        else:
            os.environ.pop('COMPRESSION_THRESHOLD', None)
        
        # Reload settings to restore defaults
        importlib.reload(__import__('cogniscient.engine.config.settings', fromlist=['settings']))
        from cogniscient.engine.config.settings import settings


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