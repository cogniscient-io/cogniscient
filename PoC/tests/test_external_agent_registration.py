"""Unit tests for external agent registration functionality."""

import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch
from cogniscient.engine.agent_utils.external_agent_registry import ExternalAgentRegistry
from cogniscient.engine.agent_utils.external_agent_adapter import ExternalAgentAdapter
from cogniscient.engine.agent_utils.external_agent_manager import ExternalAgentManager
from cogniscient.engine.services.system_parameters_service import SystemParametersService
from cogniscient.engine.config.settings import settings


@pytest.fixture
def sample_agent_config():
    """Sample external agent configuration for testing."""
    return {
        "name": "TestExternalAgent",
        "description": "A test external agent",
        "version": "1.0.0",
        "endpoint_url": "http://localhost:8000/api",
        "methods": {
            "test_method": {
                "description": "A test method",
                "parameters": {}
            }
        },
        "settings": {
            "timeout": 30
        }
    }


@pytest.fixture
def runtime_data_dir_fixture():
    """Fixture to temporarily change runtime_data_dir to a unique test directory for the test duration."""
    # Save the original value
    original_runtime_data_dir = settings.runtime_data_dir
    
    # Create a unique temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change the runtime_data_dir to use the temporary directory
        param_service = SystemParametersService()
        param_service.set_system_parameter("runtime_data_dir", temp_dir)
        
        # Yield control to the test
        yield temp_dir
        
        # Restore the original value after the test
        param_service.set_system_parameter("runtime_data_dir", original_runtime_data_dir)


@pytest.fixture
def clean_test_runtime_data():
    """Fixture to ensure the test runtime_data directory starts with a clean registry file."""
    import json
    registry_file = os.path.join("tests", "runtime_data", "external_agents_registry.json")
    
    # Ensure the directory exists
    os.makedirs("tests/runtime_data", exist_ok=True)
    
    # Backup any existing file
    backup_content = None
    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            backup_content = f.read()
    
    # Create a clean registry file
    with open(registry_file, 'w') as f:
        json.dump({}, f)
    
    yield  # Run the test
    
    # Optionally restore from backup after test if needed for other test purposes
    # For now, we'll just leave it cleaned to ensure isolation
    if backup_content is not None:
        with open(registry_file, 'w') as f:
            f.write(backup_content)


@pytest.mark.asyncio
async def test_external_agent_adapter_initialization(sample_agent_config):
    """Test that ExternalAgentAdapter can be initialized with a valid config."""
    adapter = ExternalAgentAdapter(sample_agent_config)
    
    assert adapter.config == sample_agent_config
    assert adapter.name == "TestExternalAgent"
    assert adapter.session is None  # Session should be created on demand


@pytest.mark.asyncio
async def test_external_agent_adapter_self_describe(sample_agent_config):
    """Test that ExternalAgentAdapter's self_describe returns the config."""
    adapter = ExternalAgentAdapter(sample_agent_config)
    
    description = adapter.self_describe()
    assert description == sample_agent_config


@pytest.mark.asyncio
async def test_external_agent_registry_initialization(clean_test_runtime_data):
    """Test that ExternalAgentRegistry can be initialized."""
    # Use a test-specific runtime data directory for this test
    import os
    test_runtime_dir = os.path.join("tests", "runtime_data")
    registry = ExternalAgentRegistry(runtime_data_dir=test_runtime_dir)
    
    expected_registry_file = os.path.join(test_runtime_dir, "external_agents_registry.json")
    assert registry.agents == {}
    assert registry.agent_configs == {}
    assert registry.registry_file == expected_registry_file


@pytest.mark.asyncio
async def test_external_agent_registry_register_agent(sample_agent_config, runtime_data_dir_fixture):
    """Test registering an external agent."""
    registry = ExternalAgentRegistry()
    
    result = registry.register_agent(sample_agent_config)
    assert result is True
    assert "TestExternalAgent" in registry.agents
    assert "TestExternalAgent" in registry.agent_configs
    assert registry.agent_configs["TestExternalAgent"] == sample_agent_config
    # Note: validate_agent_endpoint is not called during registration, only during health checks


@pytest.mark.asyncio
async def test_external_agent_registry_deregister_agent(sample_agent_config, runtime_data_dir_fixture):
    """Test deregistering an external agent."""
    registry = ExternalAgentRegistry()
    
    # Mock the validate_agent_endpoint to return success
    with patch.object(registry, 'validate_agent_endpoint', 
                      new_callable=AsyncMock, 
                      return_value={"status": "success", "message": "Valid"}):
        
        # Register an agent first
        registry.register_agent(sample_agent_config)
        assert "TestExternalAgent" in registry.agents
        
        # Deregister the agent
        result = registry.deregister_agent("TestExternalAgent")
        assert result is True
        assert "TestExternalAgent" not in registry.agents
        assert "TestExternalAgent" not in registry.agent_configs


@pytest.mark.asyncio
async def test_external_agent_registry_get_agent(sample_agent_config, runtime_data_dir_fixture):
    """Test retrieving an external agent."""
    registry = ExternalAgentRegistry()
    
    # Register an agent first
    registry.register_agent(sample_agent_config)
    
    # Get the agent
    agent = registry.get_agent("TestExternalAgent")
    assert agent is not None
    # Check that it's an external agent adapter (the type can be checked by module/class name)
    assert hasattr(agent, 'self_describe')  # ExternalAgentAdapter has this method
    assert hasattr(agent, 'config')  # ExternalAgentAdapter has this attribute


@pytest.mark.asyncio
async def test_external_agent_registry_list_agents(sample_agent_config, runtime_data_dir_fixture):
    """Test listing registered external agents."""
    registry = ExternalAgentRegistry()
    
    # Mock the validate_agent_endpoint to return success
    with patch.object(registry, 'validate_agent_endpoint', 
                      new_callable=AsyncMock, 
                      return_value={"status": "success", "message": "Valid"}):
        
        # Register an agent
        registry.register_agent(sample_agent_config)
        
        # List agents
        agents = registry.list_agents()
        assert "TestExternalAgent" in agents
        assert len(agents) == 1


@pytest.mark.asyncio
async def test_external_agent_registry_invalid_config(runtime_data_dir_fixture):
    """Test that invalid configurations are rejected."""
    registry = ExternalAgentRegistry()
    
    # Test config without required fields
    invalid_config = {
        "name": "InvalidAgent"
        # Missing required fields: version, endpoint_url, methods
    }
    
    result = registry.register_agent(invalid_config)
    assert result is False


@pytest.mark.asyncio
async def test_agent_manager_external_agent_integration(sample_agent_config, clean_test_runtime_data):
    """Test that ExternalAgentManager can register external agents."""
    external_manager = ExternalAgentManager(runtime_data_dir="tests/runtime_data")
    
    # Mock the validate_agent_endpoint to return success
    with patch.object(external_manager.external_agent_registry, 'validate_agent_endpoint', 
                      new_callable=AsyncMock, 
                      return_value={"status": "success", "message": "Valid"}):

        # Register an external agent
        result = external_manager.register_agent(sample_agent_config)
        assert result is True
        assert "TestExternalAgent" in external_manager._agents
        assert "TestExternalAgent" in external_manager.external_agent_registry.agent_configs


@pytest.mark.asyncio
async def test_agent_manager_deregister_external_agent(sample_agent_config, clean_test_runtime_data):
    """Test that ExternalAgentManager can deregister external agents."""
    external_manager = ExternalAgentManager(runtime_data_dir="tests/runtime_data")
    
    # Mock the validate_agent_endpoint to return success
    with patch.object(external_manager.external_agent_registry, 'validate_agent_endpoint', 
                      new_callable=AsyncMock, 
                      return_value={"status": "success", "message": "Valid"}):

        # Register an external agent first
        external_manager.register_agent(sample_agent_config)
        assert "TestExternalAgent" in external_manager._agents
        
        # Deregister the external agent
        result = external_manager.deregister_agent("TestExternalAgent")
        assert result is True
        assert "TestExternalAgent" not in external_manager._agents


@pytest.mark.asyncio
async def test_external_agent_registry_save_and_load():
    """Test saving and loading agent configurations."""
    # Use a temporary file for this test
    registry_file = "test_external_agents_registry.json"
    registry = ExternalAgentRegistry(registry_file=registry_file)
    
    sample_config = {
        "name": "TestSavedAgent",
        "description": "A test agent for save/load functionality",
        "version": "1.0.0",
        "endpoint_url": "http://localhost:8000/api",
        "methods": {
            "test_method": {
                "description": "A test method",
                "parameters": {}
            }
        }
    }
    
    # Register an agent
    with patch.object(registry, 'validate_agent_endpoint', 
                      new_callable=AsyncMock, 
                      return_value={"status": "success", "message": "Valid"}):
        registry.register_agent(sample_config)
    
    # Verify it was saved to file
    with open(registry_file, "r") as f:
        saved_data = json.load(f)
        assert "TestSavedAgent" in saved_data
    
    # Create a new registry and load from file
    new_registry = ExternalAgentRegistry(registry_file=registry_file)
    assert "TestSavedAgent" in new_registry.agent_configs
    
    # Clean up
    import os
    if os.path.exists(registry_file):
        os.remove(registry_file)


if __name__ == "__main__":
    # For running tests directly with Python (not pytest)
    import sys
    
    if "pytest" not in sys.modules:
        pytest.main([__file__])