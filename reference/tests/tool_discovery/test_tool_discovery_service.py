"""
Tests for the Tool Discovery Service functionality.

This test suite validates the ToolDiscoveryService implementation,
ensuring that external tools from MCP servers are properly discovered,
registered, and managed by the centralized discovery service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from gcs_kernel.registry import ToolRegistry
from services.tool_discovery.mcp_discovery import ToolDiscoveryService


@pytest.fixture
def mock_registry():
    """Create a mock tool registry for testing."""
    registry = AsyncMock(spec=ToolRegistry)
    # Mock methods that we'll use
    registry.register_external_tool = AsyncMock(return_value=True)
    registry.deregister_external_tool = AsyncMock(return_value=True)
    registry.unregister_tool = AsyncMock(return_value=True)
    return registry


@pytest.fixture
def tool_discovery_service(mock_registry):
    """Create a ToolDiscoveryService instance for testing."""
    service = ToolDiscoveryService(mock_registry)
    service.logger = MagicMock()  # Mock logger
    return service


@pytest.mark.asyncio
class TestToolDiscoveryService:
    """Test cases for the ToolDiscoveryService class."""

    async def test_tool_discovery_service_initialization(self, mock_registry):
        """Test that ToolDiscoveryService initializes correctly."""
        service = ToolDiscoveryService(mock_registry)
        
        assert service.registry == mock_registry
        assert service._server_tool_map == {}
        assert "tools_discovered" in service._event_handlers
        assert "tool_added" in service._event_handlers
        assert "tool_removed" in service._event_handlers
        assert "tool_updated" in service._event_handlers

    async def test_handle_tools_discovered_registers_tools(self, tool_discovery_service, mock_registry):
        """Test handling tools discovered event registers tools properly."""
        server_id = "test-server-id"
        capabilities = ["tool1", "tool2", "tool3"]
        server_url = "http://test-server:8000"
        
        # Handle the tools discovered event
        await tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        
        # Verify that register_external_tool was called for each tool
        assert mock_registry.register_external_tool.call_count == 3
        calls = mock_registry.register_external_tool.call_args_list
        expected_calls = [
            (("tool1", server_url),),
            (("tool2", server_url),),
            (("tool3", server_url),)
        ]
        for i, expected in enumerate(expected_calls):
            # Each call should be (tool_name, server_url)
            args, kwargs = calls[i]
            assert args == expected[0]  # Compare positional arguments
        
        # Verify that the server-tool mapping was updated
        assert tool_discovery_service._server_tool_map[server_id] == capabilities

    async def test_handle_tools_discovered_with_empty_capabilities(self, tool_discovery_service, mock_registry):
        """Test handling tools discovered event with no capabilities."""
        server_id = "test-server-id"
        capabilities = []
        server_url = "http://test-server:8000"
        
        # Handle the tools discovered event with empty capabilities
        await tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        
        # Verify that register_external_tool was not called
        mock_registry.register_external_tool.assert_not_called()
        
        # Verify that the server-tool mapping was updated (even if empty)
        assert tool_discovery_service._server_tool_map[server_id] == capabilities

    async def test_handle_tool_added(self, tool_discovery_service, mock_registry):
        """Test handling tool added event."""
        server_id = "test-server-id"
        tool_name = "new_tool"
        server_url = "http://test-server:8000"
        
        # Handle the tool added event
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Verify that register_external_tool was called
        mock_registry.register_external_tool.assert_called_once_with(tool_name, server_url)
        
        # Verify that the server-tool mapping was updated
        assert tool_name in tool_discovery_service._server_tool_map[server_id]

    async def test_handle_tool_added_duplicate(self, tool_discovery_service, mock_registry):
        """Test handling tool added event for a tool that already exists."""
        server_id = "test-server-id"
        tool_name = "existing_tool"
        server_url = "http://test-server:8000"
        
        # First, add the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Reset the mock to check the second call
        mock_registry.register_external_tool.reset_mock()
        
        # Add the same tool again
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Verify that register_external_tool was called again (should be registered again)
        mock_registry.register_external_tool.assert_called_once_with(tool_name, server_url)
        
        # Verify that the server-tool mapping still contains the tool once
        assert tool_discovery_service._server_tool_map[server_id].count(tool_name) == 1

    async def test_handle_tool_removed(self, tool_discovery_service, mock_registry):
        """Test handling tool removed event."""
        server_id = "test-server-id"
        tool_name = "tool_to_remove"
        server_url = "http://test-server:8000"
        
        # First add the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Then remove the tool
        await tool_discovery_service.handle_tool_removed(server_id, tool_name)
        
        # Verify that deregister_external_tool was called
        mock_registry.deregister_external_tool.assert_called_once_with(tool_name)
        
        # Verify that the tool is no longer in the server-tool mapping
        assert tool_name not in tool_discovery_service._server_tool_map[server_id]

    async def test_handle_tool_updated(self, tool_discovery_service, mock_registry):
        """Test handling tool updated event."""
        server_id = "test-server-id"
        tool_name = "tool_to_update"
        server_url = "http://test-server:8000"
        tool_definition = {"name": "tool_to_update", "parameters": {"type": "object"}}
        
        # First add the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Reset mock to check update operation
        mock_registry.deregister_external_tool.reset_mock()
        mock_registry.register_external_tool.reset_mock()
        
        # Update the tool
        await tool_discovery_service.handle_tool_updated(server_id, tool_name, server_url, tool_definition)
        
        # Verify that both deregister and register were called
        mock_registry.deregister_external_tool.assert_called_once_with(tool_name)
        mock_registry.register_external_tool.assert_called_once_with(tool_name, server_url)

    async def test_handle_server_disconnect_removes_all_tools(self, tool_discovery_service, mock_registry):
        """Test handling server disconnect removes all associated tools."""
        server_id = "test-server-id"
        server_url = "http://test-server:8000"
        
        # Add multiple tools to the server
        tools = ["tool1", "tool2", "tool3"]
        for tool_name in tools:
            await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Verify tools were added to the mapping
        assert len(tool_discovery_service._server_tool_map[server_id]) == 3
        
        # Reset mock to check the disconnection operation
        mock_registry.deregister_external_tool.reset_mock()
        
        # Disconnect the server
        await tool_discovery_service.handle_server_disconnect(server_id)
        
        # Verify that deregister_external_tool was called for each tool
        assert mock_registry.deregister_external_tool.call_count == 3
        
        # Verify that the server entry was removed from the mapping
        assert server_id not in tool_discovery_service._server_tool_map

    async def test_get_tools_for_server(self, tool_discovery_service):
        """Test getting tools for a specific server."""
        server_id = "test-server-id"
        server_url = "http://test-server:8000"
        
        # Add tools to the server
        tools = ["tool1", "tool2", "tool3"]
        for tool_name in tools:
            await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Get tools for the server
        server_tools = tool_discovery_service.get_tools_for_server(server_id)
        
        # Verify that the correct tools are returned
        assert sorted(server_tools) == sorted(tools)

    async def test_get_server_for_tool(self, tool_discovery_service):
        """Test getting the server for a specific tool."""
        server_id = "test-server-id"
        tool_name = "tool1"
        server_url = "http://test-server:8000"
        
        # Add the tool to the server
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        
        # Get the server for the tool
        result_server_id = tool_discovery_service.get_server_for_tool(tool_name)
        
        # Verify that the correct server ID is returned
        assert result_server_id == server_id

    async def test_get_server_for_tool_not_found(self, tool_discovery_service):
        """Test getting the server for a tool that doesn't exist."""
        # Try to get server for a non-existent tool
        result_server_id = tool_discovery_service.get_server_for_tool("nonexistent_tool")
        
        # Verify that None is returned
        assert result_server_id is None

    async def test_handle_tools_discovered_logs_success(self, tool_discovery_service, mock_registry):
        """Test that handling tools discovered logs appropriately."""
        server_id = "test-server-id"
        capabilities = ["tool1", "tool2"]
        server_url = "http://test-server:8000"
        
        # Set up logger mock
        logger = MagicMock()
        tool_discovery_service.logger = logger
        
        # Handle the tools discovered event
        await tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        
        # Verify that the logger was called to indicate success
        assert logger.info.called

    async def test_handle_tool_removed_logs_success(self, tool_discovery_service, mock_registry):
        """Test that handling tool removed logs appropriately."""
        server_id = "test-server-id"
        tool_name = "tool_to_remove"
        server_url = "http://test-server:8000"
        
        # Set up logger
        logger = MagicMock()
        tool_discovery_service.logger = logger
        
        # Add and then remove the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        await tool_discovery_service.handle_tool_removed(server_id, tool_name)
        
        # Verify that the logger was called to indicate success
        assert logger.info.called

    async def test_error_handling_in_register_external_tool(self, tool_discovery_service, mock_registry):
        """Test error handling when register_external_tool fails."""
        # Configure the mock to raise an exception
        mock_registry.register_external_tool.side_effect = Exception("Registration failed")
        
        server_id = "test-server-id"
        capabilities = ["tool1"]
        server_url = "http://test-server:8000"
        
        # Set up logger mock
        logger = MagicMock()
        tool_discovery_service.logger = logger
        
        # Handle the tools discovered event - should not crash
        await tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        
        # Verify that the logger was called to log the error
        assert logger.error.called

    async def test_error_handling_in_deregister_external_tool(self, tool_discovery_service, mock_registry):
        """Test error handling when deregister_external_tool fails."""
        # Configure the mock to raise an exception
        mock_registry.deregister_external_tool.side_effect = Exception("Deregistration failed")
        
        server_id = "test-server-id"
        tool_name = "tool_to_remove"
        server_url = "http://test-server:8000"
        
        # Set up logger
        logger = MagicMock()
        tool_discovery_service.logger = logger
        
        # Add and then attempt to remove the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url)
        await tool_discovery_service.handle_tool_removed(server_id, tool_name)
        
        # Verify that the logger was called to log the error
        assert logger.error.called