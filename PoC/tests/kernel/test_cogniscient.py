"""
Tests for the cogniscient package.

These tests verify that the package can be imported and that core components work correctly.
"""
import pytest
from cogniscient import GCSRuntime
from cogniscient.engine.kernel import Kernel

def test_import():
    """Test that the main components can be imported correctly."""
    assert GCSRuntime is not None
    assert Kernel is not None

def test_gcs_runtime_initialization():
    """Test that GCSRuntime can be initialized."""
    gcs = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    assert gcs is not None
    
    # Verify that the kernel is properly initialized
    assert hasattr(gcs, 'kernel')
    assert isinstance(gcs.kernel, Kernel)
    
    # Verify that services are properly initialized
    assert hasattr(gcs, 'config_service')
    assert gcs.config_service.config_dir == "plugins/sample_internal/config"


@pytest.mark.asyncio
async def test_gcs_runtime_with_mock_agents():
    """Test that GCSRuntime can be initialized and run basic operations."""
    gcs = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    
    # Since we don't have actual agents in the test environment, 
    # we'll just test that initialization works
    assert gcs is not None
    
    # Verify that the kernel is properly initialized
    assert hasattr(gcs, 'kernel')
    assert isinstance(gcs.kernel, Kernel)
    
    # Verify that the services are initialized
    assert hasattr(gcs, 'config_service')
    assert hasattr(gcs, 'system_parameters_service')
    assert hasattr(gcs, 'llm_service')
    
    # Verify that agent service is initialized
    assert hasattr(gcs, 'agent_service')
    # The external_agent_manager and agent_coordinator have been replaced by MCP service
    assert hasattr(gcs, 'mcp_service')
    # The mcp_service has both client (for connecting to external agents) and server functionality
    assert hasattr(gcs.mcp_service, 'mcp_client')
    assert hasattr(gcs.mcp_service, 'mcp_server')
    
    # Basic unload test using the agent service
    gcs.agent_service.unload_all_agents()
    assert len(gcs.agents) == 0

def test_kernel_functionality():
    """Test direct kernel functionality."""
    gcs = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    
    # Verify kernel has expected functionality
    assert hasattr(gcs.kernel, 'service_registry')
    assert hasattr(gcs.kernel, 'register_service')
    assert hasattr(gcs.kernel, 'get_service')
    
    # Verify that services are registered with the kernel
    assert 'config' in gcs.kernel.service_registry
    assert 'agent' in gcs.kernel.service_registry
    assert 'llm' in gcs.kernel.service_registry
    assert 'auth' in gcs.kernel.service_registry
    assert 'storage' in gcs.kernel.service_registry
    assert 'system_params' in gcs.kernel.service_registry

def test_cli_import():
    """Test that the CLI module can be imported."""
    from cogniscient import cli
    assert cli is not None
    assert hasattr(cli, 'main')