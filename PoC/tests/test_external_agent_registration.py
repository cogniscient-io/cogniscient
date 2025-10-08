"""Unit tests for MCP-based external agent registration functionality."""

import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.services.mcp_client_service import MCPClientService
from cogniscient.engine.services.mcp_registry import MCPConnectionRegistry
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.system_parameters_service import SystemParametersService
from cogniscient.engine.config.settings import settings


@pytest.fixture
def sample_agent_config():
    """Sample external agent configuration for MCP testing."""
    return {
        "type": "stdio",
        "command": "echo",
        "args": [],
        "env": {}
    }


@pytest.fixture
def sample_gcs_runtime():
    """Fixture to create a test GCSRuntime instance."""
    # Create a mock GCS runtime for testing
    gcs_runtime = MagicMock(spec=GCSRuntime)
    return gcs_runtime


@pytest.mark.asyncio
async def test_mcp_client_service_initialization(sample_gcs_runtime):
    """Test that MCPClientService can be initialized."""
    client_service = MCPClientService(sample_gcs_runtime)
    
    assert client_service.gcs_runtime == sample_gcs_runtime
    assert client_service.connection_managers == {}
    assert client_service.tool_registry == {}
    assert client_service.mcp_registry is not None


@pytest.mark.asyncio
async def test_mcp_service_connect_to_external_agent(sample_gcs_runtime):
    """Test connecting to an external agent via MCP service."""
    mcp_service = MCPService(sample_gcs_runtime)
    
    # Mock connection parameters
    connection_params = {
        "type": "stdio",
        "command": "echo",
        "args": ["hello"]
    }
    
    # Mock the connection manager to avoid actual connections
    with patch("cogniscient.engine.services.mcp_client_service.StdioConnectionManager") as mock_conn_manager:
        mock_instance = AsyncMock()
        mock_instance.initialize.return_value = None
        mock_instance.list_tools.return_value = {"tools": []}
        mock_conn_manager.return_value = mock_instance
        
        result = await mcp_service.connect_to_external_agent("TestAgent", connection_params)
        
        assert result["success"] is True
        assert "capabilities" in result
        # Verify the connection manager was created and initialized
        mock_instance.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_service_disconnect_from_external_agent(sample_gcs_runtime):
    """Test disconnecting from an external agent via MCP service."""
    mcp_service = MCPService(sample_gcs_runtime)
    
    # First, add a mock connection to disconnect from
    mock_connection_manager = AsyncMock()
    mock_connection_manager.close.return_value = None
    
    mcp_service.mcp_client.connection_managers["TestAgent"] = mock_connection_manager
    
    result = await mcp_service.disconnect_from_external_agent("TestAgent")
    
    assert result["success"] is True
    mock_connection_manager.close.assert_called_once()
    assert "TestAgent" not in mcp_service.mcp_client.connection_managers


@pytest.mark.asyncio
async def test_mcp_service_get_connected_agents(sample_gcs_runtime):
    """Test getting connected agents via MCP service."""
    mcp_service = MCPService(sample_gcs_runtime)
    
    # Add a mock connection
    mock_connection_manager = AsyncMock()
    mcp_service.mcp_client.connection_managers["TestAgent"] = mock_connection_manager
    
    result = mcp_service.get_connected_agents()
    
    assert result["success"] is True
    assert "TestAgent" in result["connected_agents"]
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_mcp_connection_registry_functionality():
    """Test basic MCP connection registry operations."""
    registry = MCPConnectionRegistry()
    
    # Test saving connection
    connection_data = {
        "agent_id": "TestAgent",
        "connection_params": {"type": "stdio", "command": "test"},
        "status": "connected"
    }
    
    registry.save_connection(MagicMock(**connection_data))
    
    # Test retrieving connection
    retrieved = registry.get_connection("TestAgent")
    assert retrieved is not None


if __name__ == "__main__":
    # For running tests directly with Python (not pytest)
    import sys
    
    if "pytest" not in sys.modules:
        pytest.main([__file__])