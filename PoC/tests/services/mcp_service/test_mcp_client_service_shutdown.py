"""Test for MCP Client Service Shutdown Functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from cogniscient.engine.services.mcp_client_service import MCPClientService


@pytest.mark.asyncio
async def test_mcp_client_service_shutdown():
    """Test that MCPClientService shutdown properly closes all connections."""
    # Create a mock GCS runtime
    mock_gcs_runtime = MagicMock()
    
    # Create the MCP client service
    mcp_client_service = MCPClientService(mock_gcs_runtime)
    
    # Create mock connection managers
    mock_conn_manager1 = AsyncMock()
    mock_conn_manager2 = AsyncMock()
    
    # Add them to the connection managers dict
    mcp_client_service.connection_managers = {
        "agent1": mock_conn_manager1,
        "agent2": mock_conn_manager2
    }
    
    # Call shutdown
    await mcp_client_service.shutdown()
    
    # Verify that close was called on all connection managers
    assert mock_conn_manager1.close.called
    assert mock_conn_manager2.close.called
    
    # Verify that registries were cleared
    assert len(mcp_client_service.tool_registry) == 0
    assert len(mcp_client_service.tool_types) == 0
    assert len(mcp_client_service.connection_managers) == 0


@pytest.mark.asyncio
async def test_mcp_client_service_shutdown_with_errors():
    """Test that MCPClientService shutdown handles errors gracefully."""
    # Create a mock GCS runtime
    mock_gcs_runtime = MagicMock()
    
    # Create the MCP client service
    mcp_client_service = MCPClientService(mock_gcs_runtime)
    
    # Create mock connection managers, one that raises an exception
    mock_conn_manager1 = AsyncMock()
    mock_conn_manager2 = AsyncMock()
    mock_conn_manager2.close.side_effect = Exception("Connection error")
    
    # Add them to the connection managers dict
    mcp_client_service.connection_managers = {
        "agent1": mock_conn_manager1,
        "agent2": mock_conn_manager2
    }
    
    # Call shutdown - should not raise an exception even if one connection fails
    await mcp_client_service.shutdown()
    
    # Verify that close was attempted on all connection managers
    assert mock_conn_manager1.close.called
    assert mock_conn_manager2.close.called
    
    # Verify that registries were still cleared despite errors
    assert len(mcp_client_service.tool_registry) == 0
    assert len(mcp_client_service.tool_types) == 0
    assert len(mcp_client_service.connection_managers) == 0


if __name__ == "__main__":
    pytest.main([__file__])