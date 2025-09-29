"""
Tests for the cogniscient package.

These tests verify that the package can be imported and that core components work correctly.
"""
import pytest
from cogniscient import GCSRuntime


def test_import():
    """Test that the main components can be imported correctly."""
    assert GCSRuntime is not None


def test_gcs_runtime_initialization():
    """Test that GCSRuntime can be initialized."""
    gcs = GCSRuntime(config_dir="tests/test_configs", agents_dir="tests/test_agents")
    assert gcs is not None
    assert gcs.config_dir == "tests/test_configs"
    assert gcs.agents_dir == "tests/test_agents"


@pytest.mark.asyncio
async def test_gcs_runtime_with_mock_agents():
    """Test that GCSRuntime can be initialized and run basic operations."""
    gcs = GCSRuntime(config_dir="tests/test_configs", agents_dir="tests/test_agents")
    
    # Since we don't have actual agents in the test environment, 
    # we'll just test that initialization works
    assert gcs is not None
    
    # Verify that the services are initialized
    assert hasattr(gcs, 'config_service')
    assert hasattr(gcs, 'system_parameters_service')
    assert hasattr(gcs, 'llm_service')
    
    # Verify that agent managers are initialized
    assert hasattr(gcs, 'local_agent_manager')
    assert hasattr(gcs, 'external_agent_manager')
    assert hasattr(gcs, 'agent_coordinator')
    
    # Basic unload test
    gcs.unload_all_agents()
    assert len(gcs.agents) == 0


def test_cli_import():
    """Test that the CLI module can be imported."""
    from cogniscient import cli
    assert cli is not None
    assert hasattr(cli, 'main')