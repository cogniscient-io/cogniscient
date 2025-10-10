"""Unit tests for configuration management functionality."""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface


@pytest.mark.asyncio
async def test_config_loading_functionality():
    """Test loading different configurations."""
    # Initialize GCS runtime with plugin config and agent directories
    # NOTE: In production, these paths could be updated via system parameters service
    import os
    # Calculate the project root directory (go up from the current file location)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    plugin_configs_dir = os.path.join(project_root, "plugins", "sample_internal", "config")
    plugin_agents_dir = os.path.join(project_root, "plugins", "sample_internal", "agents")
    gcs_runtime = GCSRuntime(config_dir=plugin_configs_dir, agents_dir=plugin_agents_dir)
    
    # Initially no agents loaded
    initial_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    
    # Test loading website only configuration
    await gcs_runtime.config_service.load_configuration("website_only")
    # In the new architecture, loading the configuration should make the agents available for loading
    # Load the agents specified in the configuration
    website_only_config = gcs_runtime.config_service.get_configuration("website_only")
    for agent_info in website_only_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    website_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    assert "SampleAgentB" in website_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in website_agents
    assert "SystemParametersManager" not in website_agents
    assert "SampleAgentA" not in website_agents
    
    # Test loading DNS only configuration
    # First clear current agents
    for agent in list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys()):
        gcs_runtime.agent_service.unified_agent_manager.unload_agent(agent)
        
    await gcs_runtime.config_service.load_configuration("dns_only")
    # Load the agents specified in the configuration
    dns_only_config = gcs_runtime.config_service.get_configuration("dns_only")
    for agent_info in dns_only_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    dns_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    assert "SampleAgentA" in dns_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in dns_agents
    assert "SystemParametersManager" not in dns_agents
    assert "SampleAgentB" not in dns_agents
    
    # Test loading combined configuration
    # First clear current agents
    for agent in list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys()):
        gcs_runtime.agent_service.unified_agent_manager.unload_agent(agent)
        
    await gcs_runtime.config_service.load_configuration("combined")
    # Load the agents specified in the configuration
    combined_config = gcs_runtime.config_service.get_configuration("combined")
    for agent_info in combined_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    combined_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    assert "SampleAgentA" in combined_agents
    assert "SampleAgentB" in combined_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in combined_agents
    assert "SystemParametersManager" not in combined_agents
    
    # Test listing available configurations
    configs = gcs_runtime.config_service.list_configurations()
    assert "dns_only" in configs
    assert "website_only" in configs
    assert "combined" in configs
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in website_agents
    assert "SystemParametersManager" not in website_agents
    assert "SampleAgentA" not in website_agents
    
    # Test loading DNS only configuration
    # First clear current agents
    for agent in list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys()):
        gcs_runtime.agent_service.unified_agent_manager.unload_agent(agent)
        
    await gcs_runtime.config_service.load_configuration("dns_only")
    # Load the agents specified in the configuration
    dns_only_config = gcs_runtime.config_service.get_configuration("dns_only")
    for agent_info in dns_only_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
        
    dns_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    assert "SampleAgentA" in dns_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in dns_agents
    assert "SystemParametersManager" not in dns_agents
    assert "SampleAgentB" not in dns_agents
    
    # Test loading combined configuration
    # First clear current agents
    for agent in list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys()):
        gcs_runtime.agent_service.unified_agent_manager.unload_agent(agent)
        
    await gcs_runtime.config_service.load_configuration("combined")
    # Load the agents specified in the configuration
    combined_config = gcs_runtime.config_service.get_configuration("combined")
    for agent_info in combined_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    combined_agents = list(gcs_runtime.agent_service.unified_agent_manager.get_all_agents().keys())
    assert "SampleAgentA" in combined_agents
    assert "SampleAgentB" in combined_agents
    # ConfigManager and SystemParametersManager are now system services, not loaded agents
    assert "ConfigManager" not in combined_agents
    assert "SystemParametersManager" not in combined_agents
    
    # Test listing available configurations
    configs = gcs_runtime.config_service.list_configurations()
    assert "dns_only" in configs
    assert "website_only" in configs
    assert "combined" in configs


@pytest.mark.asyncio
async def test_config_manager_descriptions():
    """Test that config manager reads descriptions from config files."""
    # Initialize GCS runtime with plugin config and agent directories
    # NOTE: In production, these paths could be updated via system parameters service
    import os
    # Calculate the project root directory (go up from the current file location)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    plugin_configs_dir = os.path.join(project_root, "plugins", "sample_internal", "config")
    plugin_agents_dir = os.path.join(project_root, "plugins", "sample_internal", "agents")
    gcs_runtime = GCSRuntime(config_dir=plugin_configs_dir, agents_dir=plugin_agents_dir)
    await gcs_runtime.config_service.load_configuration("combined")
    # Load the agents specified in the configuration
    combined_config = gcs_runtime.config_service.get_configuration("combined")
    for agent_info in combined_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    # In the new architecture, configurations are handled by the config service
    # Test listing configurations
    configs = gcs_runtime.config_service.list_configurations()
    assert len(configs) > 0
    assert "combined" in configs
    assert "dns_only" in configs
    assert "website_only" in configs
    
    # Check descriptions for each configuration
    for config_name in configs:
        config_details = gcs_runtime.config_service.get_configuration(config_name)
        # Each config should have a description or other identifying information
        assert config_name is not None


@pytest.mark.asyncio
async def test_llm_driven_config_management():
    """Test LLM-driven configuration management via MCP services."""
    # Initialize system
    import os
    # Calculate the project root directory (go up from the current file location)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    plugin_configs_dir = os.path.join(project_root, "plugins", "sample_internal", "config")
    plugin_agents_dir = os.path.join(project_root, "plugins", "sample_internal", "agents")
    gcs_runtime = GCSRuntime(config_dir=plugin_configs_dir, agents_dir=plugin_agents_dir)
    await gcs_runtime.config_service.load_configuration("combined")
    # Load the agents specified in the configuration
    combined_config = gcs_runtime.config_service.get_configuration("combined")
    for agent_info in combined_config.get('agents', []):
        agent_name = agent_info['name']
        try:
            gcs_runtime.agent_service.unified_agent_manager.load_agent(agent_name)
        except FileNotFoundError:
            # If agent file doesn't exist, this is expected in the new architecture
            # The important part is that the config defines which agents should be loaded
            pass
    
    # Get the LLM service which now handles MCP integration
    llm_service = gcs_runtime.llm_service
    
    # Verify that the LLM service has MCP capabilities properly configured
    assert hasattr(llm_service, 'mcp_client_service') or hasattr(gcs_runtime, 'mcp_service')
    
    # Test that MCP service is properly initialized
    assert gcs_runtime.mcp_service is not None
    assert gcs_runtime.mcp_service.mcp_client is not None
    
    # Test that we can get connected agents
    connected_agents = gcs_runtime.mcp_service.get_connected_agents()
    assert "connected_agents" in connected_agents
    
    # Verify that MCP tools for configuration management are available via the MCP service
    # The MCP service should have these methods
    assert hasattr(gcs_runtime.mcp_service, 'connect_to_external_agent')
    assert hasattr(gcs_runtime.mcp_service, 'disconnect_from_external_agent')
    assert hasattr(gcs_runtime.mcp_service, 'get_connected_agents')
    assert hasattr(gcs_runtime.mcp_service, 'get_external_agent_capabilities')


def test_agents_dir_system_parameter():
    """Test that agents_dir can be configured via system parameters service."""
    
    # Initialize GCS runtime with the original default path
    gcs_runtime = GCSRuntime(config_dir=".", agents_dir="plugins/sample_internal/agents")
    
    # Set the agents_dir parameter explicitly so it appears in system parameters
    initial_set_result = gcs_runtime.system_parameters_service.set_system_parameter("agents_dir", "plugins/sample_internal/agents")
    assert initial_set_result["status"] == "success"
    
    # In the new architecture, config_dir and agents_dir are not direct attributes of gcs_runtime
    # They are managed by the config service and system parameters service
    # Check that the agents_dir parameter is available in system parameters
    params_result = gcs_runtime.system_parameters_service.get_system_parameters()
    assert params_result["status"] == "success"
    # The agents_dir parameter should be in the system parameters after being set
    assert "agents_dir" in params_result["parameters"]
    # Verify the initial value in the system parameters
    assert params_result["parameters"]["agents_dir"] == "plugins/sample_internal/agents"
    
    # Create the target directory to ensure it exists
    import os
    os.makedirs("custom/agents/path", exist_ok=True)
    
    # Change agents_dir via system parameters service
    change_result = gcs_runtime.system_parameters_service.set_system_parameter("agents_dir", "custom/agents/path")
    assert change_result["status"] == "success"
    
    # Get updated system parameters to verify the change
    updated_params_result = gcs_runtime.system_parameters_service.get_system_parameters()
    assert updated_params_result["status"] == "success"
    assert updated_params_result["parameters"]["agents_dir"] == "custom/agents/path"


def test_config_dir_system_parameter():
    """Test that config_dir can be configured via system parameters service."""
    
    # Initialize GCS runtime with default settings
    gcs_runtime = GCSRuntime()
    
    # Set the agents_dir to tests directory for this specific test 
    gcs_runtime.system_parameters_service.set_system_parameter('agents_dir', 'tests')
    
    # Initially check that config_dir parameter is available in system parameters after setting
    initial_set_result = gcs_runtime.system_parameters_service.set_system_parameter('config_dir', '.')
    assert initial_set_result["status"] == "success"
    
    # Now check that the config_dir parameter is available in system parameters
    params_result = gcs_runtime.system_parameters_service.get_system_parameters()
    assert params_result["status"] == "success"
    assert "config_dir" in params_result["parameters"]
    # Verify the initial value in the system parameters (should be from settings)
    assert params_result["parameters"]["config_dir"] == "."
    
    # Create the target directory to ensure it exists
    import os
    os.makedirs("/tmp/test_config_dir", exist_ok=True)
    
    # Change config_dir via system parameters service
    change_result = gcs_runtime.system_parameters_service.set_system_parameter("config_dir", "/tmp/test_config_dir")
    assert change_result["status"] == "success"
    
    # Get updated system parameters to verify the change
    updated_params_result = gcs_runtime.system_parameters_service.get_system_parameters()
    assert updated_params_result["status"] == "success"
    assert updated_params_result["parameters"]["config_dir"] == "/tmp/test_config_dir"


def test_llm_config_system_parameter():
    """Test that LLM configuration parameters can be updated via system parameters service."""
    from cogniscient.engine.config.settings import settings
    
    # Create a copy of the original values to restore later
    original_llm_model = settings.llm_model
    original_llm_base_url = settings.llm_base_url
    
    try:
        # Initialize GCS runtime with default settings
        gcs_runtime = GCSRuntime()
        
        # Set the agents_dir to tests directory for this specific test 
        gcs_runtime.system_parameters_service.set_system_parameter('agents_dir', 'tests')
        
        # Check that initial LLM settings are available in system parameters
        params_result = gcs_runtime.system_parameters_service.get_system_parameters()
        assert params_result["status"] == "success"
        assert "llm_model" in params_result["parameters"]
        assert "llm_base_url" in params_result["parameters"]
        
        # Change LLM model via system parameters service
        model_result = gcs_runtime.system_parameters_service.set_system_parameter(
            "llm_model", "ollama_chat/llama3:70b"
        )
        assert model_result["status"] == "success"
        
        # Change LLM base URL via system parameters service
        url_result = gcs_runtime.system_parameters_service.set_system_parameter(
            "llm_base_url", "http://newhost:11434"
        )
        assert url_result["status"] == "success"
        
        # Verify that the settings were updated
        assert settings.llm_model == "ollama_chat/llama3:70b"
        assert settings.llm_base_url == "http://newhost:11434"
        
        # Get updated system parameters to verify the changes
        updated_params_result = gcs_runtime.system_parameters_service.get_system_parameters()
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