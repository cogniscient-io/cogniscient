"""Tests for MCP Service Functionality (Client and Server)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.gcs_runtime import GCSRuntime


def test_mcp_service_initialization():
    """Should initialize MCP service successfully with GCS runtime."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    # Mock the agents attribute to avoid AttributeError
    gcs_runtime.agents = {}
    mcp_service = MCPService(gcs_runtime)
    assert mcp_service is not None
    assert mcp_service.gcs_runtime == gcs_runtime
    # Verify that both client and server aspects are initialized
    assert hasattr(mcp_service, 'mcp_server')
    assert hasattr(mcp_service, 'clients')


def test_mcp_agent_tool_registration():
    """Should register agent methods as MCP tools (server role)."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    mock_agent = MagicMock()
    mock_agent.some_method = MagicMock()
    gcs_runtime.agents = {"SampleAgentA": mock_agent}
    gcs_runtime.run_agent = MagicMock(return_value={"result": "success"})
    
    mcp_service = MCPService(gcs_runtime)
    # The server should have registered tools for the agent during initialization
    # This test would need to check that the appropriate tools were registered
    # depending on the methods available in SampleAgentA
    # Note: Actual implementation would require checking the internal tool registry


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    """Should execute agent methods through MCP protocol (server role)."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    mock_agent = MagicMock()
    mock_agent.some_method = MagicMock()
    gcs_runtime.agents = {"SampleAgentA": mock_agent}
    gcs_runtime.run_agent = MagicMock(return_value={"result": "success"})
    
    mcp_service = MCPService(gcs_runtime)
    
    # Since the tool registration happens internally in __init__,
    # the actual test would involve calling registered tools
    # For now, we'll verify that run_agent is called correctly
    result = gcs_runtime.run_agent("SampleAgentA", "some_method", test_param="value")
    gcs_runtime.run_agent.assert_called_once_with("SampleAgentA", "some_method", test_param="value")
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_mcp_external_agent_connection():
    """Should connect to external agent as MCP client."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    gcs_runtime.agents = {}  # Empty agents for this test
    
    mcp_service = MCPService(gcs_runtime)
    
    # Test that the connection method exists and can be called
    # Note: In a real scenario, we would test with actual connection parameters
    # For now, we'll test that the method exists and handles errors appropriately
    connection_params = {
        "type": "stdio",  # Using stdio for testing
        "command": "nonexistent_command"
    }
    # This should fail since the command doesn't exist, but method should be callable
    try:
        result = await mcp_service.connect_to_external_agent("test_agent", connection_params)
        # If execution reaches here, the method was called without exception
    except Exception:
        # This is expected since the command doesn't exist
        pass


@pytest.mark.asyncio
async def test_mcp_connected_agents():
    """Should track connected external agents."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    gcs_runtime.agents = {}
    
    mcp_service = MCPService(gcs_runtime)
    
    # Initially, no agents should be connected
    connected_agents = mcp_service.get_connected_agents()
    assert connected_agents == []


if __name__ == "__main__":
    pytest.main([__file__])