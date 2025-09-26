"""Test suite for external agent registration functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.agents.external_agent_adapter import ExternalAgentAdapter
from src.agent_utils.external_agent_registry import ExternalAgentRegistry
from src.agent_utils.local_agent_manager import LocalAgentManager
from src.agent_utils.external_agent_manager import ExternalAgentManager


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
async def test_external_agent_registry_initialization():
    """Test that ExternalAgentRegistry can be initialized."""
    # Use a temporary registry file for this test to avoid cross-test contamination
    registry = ExternalAgentRegistry(registry_file="test_external_agents_registry.json")
    
    assert registry.agents == {}
    assert registry.agent_configs == {}
    assert registry.registry_file == "test_external_agents_registry.json"

    # Clean up the temp file after the test
    import os
    if os.path.exists("test_external_agents_registry.json"):
        os.remove("test_external_agents_registry.json")


@pytest.mark.asyncio
async def test_external_agent_registry_register_agent(sample_agent_config):
    """Test registering an external agent."""
    registry = ExternalAgentRegistry()
    
    result = registry.register_agent(sample_agent_config)
    assert result is True
    assert "TestExternalAgent" in registry.agents
    assert "TestExternalAgent" in registry.agent_configs
    assert registry.agent_configs["TestExternalAgent"] == sample_agent_config
    # Note: validate_agent_endpoint is not called during registration, only during health checks


@pytest.mark.asyncio
async def test_external_agent_registry_deregister_agent(sample_agent_config):
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
async def test_external_agent_registry_get_agent(sample_agent_config):
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
async def test_external_agent_registry_list_agents(sample_agent_config):
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
async def test_external_agent_registry_invalid_config():
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
async def test_agent_manager_external_agent_integration(sample_agent_config):
    """Test that ExternalAgentManager can register external agents."""
    external_manager = ExternalAgentManager()
    
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
async def test_agent_manager_deregister_external_agent(sample_agent_config):
    """Test that ExternalAgentManager can deregister external agents."""
    external_manager = ExternalAgentManager()
    
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