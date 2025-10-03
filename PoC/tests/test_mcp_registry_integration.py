"""Integration test to validate MCP registry functionality."""

from unittest.mock import MagicMock
from datetime import datetime
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.mcp_registry import MCPConnectionData


def test_registry_integration():
    """Test that the MCP service properly integrates with the registry."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    gcs_runtime.agents = {}
    
    # Initialize the MCP service which should initialize the registry
    mcp_service = MCPService(gcs_runtime)
    
    # Verify that the registry was initialized
    assert hasattr(mcp_service, 'mcp_registry')
    assert mcp_service.mcp_registry is not None
    
    # Test saving a connection to the registry
    connection_data = MCPConnectionData(
        agent_id="test_integration_agent",
        connection_params={"type": "stdio", "command": "test_command"}
    )
    
    result = mcp_service.mcp_registry.save_connection(connection_data)
    assert result is True
    
    # Verify the connection can be retrieved
    retrieved_data = mcp_service.mcp_registry.get_connection("test_integration_agent")
    assert retrieved_data is not None
    assert retrieved_data.agent_id == "test_integration_agent"
    assert retrieved_data.connection_params == {"type": "stdio", "command": "test_command"}
    
    # Test registry lookup functionality
    is_valid = mcp_service.mcp_registry.is_connection_valid(
        "test_integration_agent", 
        {"type": "stdio", "command": "test_command"}
    )
    assert is_valid is True
    
    # Test with different connection params (should be invalid)
    is_valid = mcp_service.mcp_registry.is_connection_valid(
        "test_integration_agent", 
        {"type": "http", "url": "test_url"}
    )
    assert is_valid is False
    
    print("✅ MCP Registry integration test passed!")


if __name__ == "__main__":
    test_registry_integration()
    print("All integration tests passed!")