"""
Test for the unified agent manager implementation.
This test verifies that the consolidation of local agent registration and internal services works correctly.
"""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.agent_utils.base_agent_manager import ComponentType, UnifiedComponent
from cogniscient.engine.agent_utils.unified_agent_manager import UnifiedAgentManager


def test_unified_component_creation():
    """Test creating unified components for different types."""
    # Test creating a local agent component
    local_agent = UnifiedComponent(
        name="TestLocalAgent",
        component_type=ComponentType.LOCAL_AGENT,
        config={"name": "TestLocalAgent", "enabled": True},
        load_behavior="dynamic"
    )
    assert local_agent.name == "TestLocalAgent"
    assert local_agent.component_type == ComponentType.LOCAL_AGENT
    assert local_agent.load_behavior == "dynamic"

    # Test creating an internal service component
    internal_service = UnifiedComponent(
        name="TestService",
        component_type=ComponentType.INTERNAL_SERVICE,
        config={"name": "TestService", "service_type": "config"},
        load_behavior="static"
    )
    assert internal_service.name == "TestService"
    assert internal_service.component_type == ComponentType.INTERNAL_SERVICE
    assert internal_service.load_behavior == "static"


def test_unified_manager_functionality():
    """Test the unified manager can handle all component types."""
    manager = UnifiedAgentManager()
    
    # Create components of different types
    local_agent_comp = UnifiedComponent(
        name="TestLocalAgent",
        component_type=ComponentType.LOCAL_AGENT,
        config={"name": "TestLocalAgent", "enabled": True, "module_path": "./test_agent.py"},
        load_behavior="dynamic"
    )
    
    service_comp = UnifiedComponent(
        name="TestService",
        component_type=ComponentType.INTERNAL_SERVICE,
        config={"name": "TestService", "service_type": "config"},
        load_behavior="static"
    )
    
    # Register components
    assert manager.register_component(local_agent_comp) is True
    assert manager.register_component(service_comp) is True
    
    # Check that components are registered
    assert "TestLocalAgent" in manager.components
    assert "TestService" in manager.components
    
    # Test loading behavior - static component should be loaded automatically
    if service_comp.load_behavior == "static":
        assert service_comp.is_loaded is True


def test_gcs_runtime_uses_unified_manager():
    """Test that GCSRuntime now uses the unified manager."""
    gcs = GCSRuntime()
    
    # Check unified manager is present and initialized
    assert hasattr(gcs, 'unified_agent_manager')
    assert gcs.unified_agent_manager is not None
    
    # Check that services are registered in the unified manager
    components = gcs.unified_agent_manager.components
    assert "ConfigManager" in components
    assert "SystemParametersManager" in components
    
    # Check that the services have the correct component type
    config_comp = components["ConfigManager"]
    system_comp = components["SystemParametersManager"]
    assert config_comp.component_type == ComponentType.INTERNAL_SERVICE
    assert system_comp.component_type == ComponentType.INTERNAL_SERVICE


def test_backward_compatibility():
    """Test that existing interfaces still work."""
    gcs = GCSRuntime()
    
    # Test that legacy managers still exist for backward compatibility
    assert hasattr(gcs, 'local_agent_manager')
    # The external_agent_manager has been replaced by MCP service
    assert hasattr(gcs, 'mcp_service')
    # The mcp_service has both client (for connecting to external agents) and server functionality
    assert hasattr(gcs.mcp_service, 'mcp_client')
    assert hasattr(gcs.mcp_service, 'mcp_server')
    
    # Test that agents property still works and filters out services
    agents = gcs.agents
    assert isinstance(agents, dict)
    # The agents property should not include services for backward compatibility
    for agent_name in agents.keys():
        assert agent_name not in ["ConfigManager", "SystemParametersManager"]
    
    # Test that services still work separately
    config_result = gcs.run_agent("ConfigManager", "list_configurations")
    assert config_result["status"] == "success"
    
    params_result = gcs.run_agent("SystemParametersManager", "get_system_parameters")
    assert params_result["status"] == "success"


if __name__ == "__main__":
    test_unified_component_creation()
    test_unified_manager_functionality()
    test_gcs_runtime_uses_unified_manager()
    test_backward_compatibility()
    print("All unified system tests passed!")