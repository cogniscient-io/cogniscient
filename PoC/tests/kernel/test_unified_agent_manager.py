"""
Test for the unified agent manager implementation.
This test verifies that the consolidation of local agent registration and internal services works correctly.
"""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.agent_utils.unified_agent_manager import UnifiedAgentManager


def test_unified_manager_creation():
    """Test creating unified agent manager."""
    # Test creating a unified agent manager
    manager = UnifiedAgentManager(agents_dir="plugins/sample_internal/agents")
    
    assert manager is not None
    assert hasattr(manager, 'agents_dir')
    assert manager.agents_dir == "plugins/sample_internal/agents"
    assert hasattr(manager, 'agents')
    assert isinstance(manager.agents, dict)
    assert len(manager.agents) == 0


def test_unified_manager_functionality():
    """Test the unified manager can handle agent operations."""
    manager = UnifiedAgentManager(agents_dir="plugins/sample_internal/agents")
    
    # Test that the manager implements the BaseAgentManager interface
    assert hasattr(manager, 'get_agent')
    assert hasattr(manager, 'get_all_agents')
    assert hasattr(manager, 'run_agent')
    assert hasattr(manager, 'load_agent')
    assert hasattr(manager, 'unload_agent')


def test_gcs_runtime_uses_unified_manager():
    """Test that GCSRuntime now uses the unified manager."""
    gcs = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    
    # Check unified manager is present and initialized
    assert hasattr(gcs, 'agent_service')
    assert gcs.agent_service is not None
    
    # Check that the unified agent manager is used within the agent service
    assert hasattr(gcs.agent_service, 'unified_agent_manager')
    assert isinstance(gcs.agent_service.unified_agent_manager, UnifiedAgentManager)


def test_backward_compatibility():
    """Test that existing interfaces still work."""
    gcs = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    
    # Test that legacy managers still exist for backward compatibility
    assert hasattr(gcs, 'agent_service')
    # The external_agent_manager and agent_coordinator have been replaced by MCP service
    assert hasattr(gcs, 'mcp_service')
    # The mcp_service has both client (for connecting to external agents) and server functionality
    assert hasattr(gcs.mcp_service, 'mcp_client')
    assert hasattr(gcs.mcp_service, 'mcp_server')
    
    # Test that agents property still works
    agents = gcs.agents
    assert isinstance(agents, dict)


if __name__ == "__main__":
    test_unified_manager_creation()
    test_unified_manager_functionality()
    test_gcs_runtime_uses_unified_manager()
    test_backward_compatibility()
    print("All unified system tests passed!")