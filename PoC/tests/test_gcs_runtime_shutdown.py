"""Test for GCS Runtime Shutdown Functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from cogniscient.engine.gcs_runtime import GCSRuntime


def test_gcs_runtime_shutdown_calls_cleanup_methods():
    """Test that GCSRuntime shutdown properly calls cleanup methods."""
    # Create a GCSRuntime instance and then mock its components
    gcs_runtime = GCSRuntime(config_dir=".", agents_dir="cogniscient/agentSDK")
    
    # Mock the components instead of replacing them
    gcs_runtime.unified_agent_manager = MagicMock()
    gcs_runtime.local_agent_manager = MagicMock()
    
    # Mock the MCP service and its client
    mock_mcp_service = MagicMock()
    mock_mcp_client = AsyncMock()
    mock_mcp_service.mcp_client = mock_mcp_client
    gcs_runtime.mcp_service = mock_mcp_service
    
    # Mock the unload methods
    gcs_runtime.unified_agent_manager.components = {"test": MagicMock()}
    gcs_runtime.unified_agent_manager.unload_component = MagicMock()
    gcs_runtime.local_agent_manager.unload_all_agents = MagicMock()
    
    # Call shutdown
    gcs_runtime.shutdown()
    
    # Verify that the cleanup methods were called
    assert gcs_runtime.unified_agent_manager.unload_component.called
    assert gcs_runtime.local_agent_manager.unload_all_agents.called


def test_gcs_runtime_shutdown_without_mcp_service():
    """Test that GCSRuntime shutdown works even without MCP service."""
    # Create a GCSRuntime instance and then mock its components
    gcs_runtime = GCSRuntime(config_dir=".", agents_dir="cogniscient/agentSDK")
    
    # Mock the components
    gcs_runtime.unified_agent_manager = MagicMock()
    gcs_runtime.local_agent_manager = MagicMock()
    gcs_runtime.mcp_service = None
    
    # Mock the unload methods
    gcs_runtime.unified_agent_manager.components = {"test": MagicMock()}
    gcs_runtime.unified_agent_manager.unload_component = MagicMock()
    gcs_runtime.local_agent_manager.unload_all_agents = MagicMock()
    
    # This should not raise an exception
    gcs_runtime.shutdown()
    
    # Verify that the cleanup methods were called
    assert gcs_runtime.unified_agent_manager.unload_component.called
    assert gcs_runtime.local_agent_manager.unload_all_agents.called


if __name__ == "__main__":
    pytest.main([__file__])