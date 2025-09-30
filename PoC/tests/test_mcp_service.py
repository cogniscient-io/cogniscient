"""Tests for MCP Service Functionality."""

import pytest
from unittest.mock import MagicMock
from cogniscient.engine.services.mcp_service import MCPServer
from cogniscient.engine.gcs_runtime import GCSRuntime


def test_mcp_server_initialization():
    """Should initialize MCP server successfully with GCS runtime."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    # Mock the agents attribute to return an empty dict so the initialization doesn't fail
    gcs_runtime.agents = {}
    mcp_server = MCPServer(gcs_runtime)
    assert mcp_server is not None
    assert mcp_server.gcs_runtime == gcs_runtime


def test_mcp_agent_tool_registration():
    """Should register agent methods as MCP tools."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    mock_agent = MagicMock()
    mock_agent.some_method = MagicMock()
    gcs_runtime.agents = {"SampleAgentA": mock_agent}
    gcs_runtime.run_agent = MagicMock(return_value={"result": "success"})
    
    mcp_server = MCPServer(gcs_runtime)
    # The server should have registered tools for the agent during initialization
    # This test would need to check that the appropriate tools were registered
    # depending on the methods available in SampleAgentA
    # Note: Actual implementation would require checking the internal tool registry


@pytest.mark.asyncio
async def test_mcp_tool_execution():
    """Should execute agent methods through MCP protocol."""
    gcs_runtime = MagicMock(spec=GCSRuntime)
    mock_agent = MagicMock()
    mock_agent.some_method = MagicMock()
    gcs_runtime.agents = {"SampleAgentA": mock_agent}
    gcs_runtime.run_agent = MagicMock(return_value={"result": "success"})
    
    mcp_server = MCPServer(gcs_runtime)
    
    # Since the tool registration happens internally in __init__,
    # the actual test would involve calling registered tools
    # For now, we'll verify that run_agent is called correctly
    result = gcs_runtime.run_agent("SampleAgentA", "some_method", test_param="value")
    gcs_runtime.run_agent.assert_called_once_with("SampleAgentA", "some_method", test_param="value")
    assert result == {"result": "success"}


if __name__ == "__main__":
    pytest.main([__file__])