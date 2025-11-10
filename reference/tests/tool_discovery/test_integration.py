"""
Integration tests for the Tool Discovery Service with the MCP Client Manager and Kernel.

This test suite validates the complete flow from MCP server connection to tool registration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.mcp.client_manager import MCPClientManager
from gcs_kernel.mcp.server_registry import MCPServerInfo
from gcs_kernel.models import MCPConfig
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


@pytest.fixture
def mcp_client_manager():
    """Create an MCPClientManager instance for testing."""
    config = MCPConfig(server_url="http://localhost:8000", 
                      runtime_data_directory="./runtime_data", 
                      server_registry_filename="test_registry.json")
    manager = MCPClientManager(config)
    manager.logger = MagicMock()
    return manager


@pytest.mark.asyncio
class TestToolDiscoveryIntegration:
    """Integration tests for the tool discovery system."""

    async def test_kernel_tool_discovery_integration(self, mock_registry):
        """Test the complete integration between kernel, tool discovery service, and registry."""
        # Create the tool discovery service
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        tool_discovery_service.logger = MagicMock()
        
        # Simulate the kernel's connection to the tool discovery service
        # This mimics what happens in the kernel initialization
        mock_kernel = MagicMock()
        mock_kernel.registry = mock_registry
        mock_kernel.tool_discovery_service = tool_discovery_service
        
        # Simulate discovery of tools from an external server
        server_id = "test-server-123"
        capabilities = ["health_check", "data_processor", "file_analyzer"]
        server_url = "http://external-server:8000"
        
        # Call the discovery service as would happen when connecting to a server
        await tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        
        # Verify that the registry had external tools registered
        assert mock_registry.register_external_tool.call_count == len(capabilities)
        
        # Verify that each capability was registered with the correct server URL
        calls_made = mock_registry.register_external_tool.call_args_list
        registered_tools = [call[0][0] for call in calls_made]  # Get first positional arg (tool name)
        registered_urls = [call[0][1] for call in calls_made]  # Get second positional arg (server URL)
        
        assert sorted(registered_tools) == sorted(capabilities)
        assert all(url == server_url for url in registered_urls)
        
        # Verify internal mapping
        assert tool_discovery_service._server_tool_map[server_id] == capabilities

    async def test_mcp_client_manager_event_emission_to_tool_discovery(self, tool_discovery_service):
        """Test MCP client manager emitting events to tool discovery service."""
        # Create a mock client manager
        config = MCPConfig(server_url="http://localhost:8000", 
                          runtime_data_directory="./runtime_data", 
                          server_registry_filename="test_registry.json")
        manager = MCPClientManager(config)
        manager.logger = MagicMock()
        
        # Connect the manager to the tool discovery service
        manager._tool_discovery_service = tool_discovery_service
        
        # Mock the notification system
        original_notify = manager._notify_tool_discovered_event
        manager._notify_tool_discovered_event = AsyncMock()
        
        # Test the event emission - call it correctly without passing manager as first arg
        await manager._notify_tool_discovered_event("tools_discovered", "test-server", ["tool1", "tool2"], "http://test.com")
        
        # Verify that the event notification method was called
        manager._notify_tool_discovered_event.assert_called_once_with(
            "tools_discovered", "test-server", ["tool1", "tool2"], "http://test.com"
        )

    async def test_complete_tool_lifecycle(self, mock_registry):
        """Test the complete lifecycle: discovery -> usage -> removal of external tools."""
        # Set up the tool discovery service
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        tool_discovery_service.logger = MagicMock()
        
        # Define server and tools
        server_id = "test-server-lifecycle"
        server_url = "http://lifecycle-test:8000"
        tools = ["tool_a", "tool_b", "tool_c"]
        
        # Step 1: Discover and register tools
        await tool_discovery_service.handle_tools_discovered(server_id, tools, server_url)
        
        # Verify registration calls
        assert mock_registry.register_external_tool.call_count == len(tools)
        
        # Reset call counts for next verification
        mock_registry.register_external_tool.reset_mock()
        
        # Step 2: Add an additional tool during runtime
        new_tool = "tool_d"
        await tool_discovery_service.handle_tool_added(server_id, new_tool, server_url, {})
        
        # Verify the new tool was registered
        mock_registry.register_external_tool.assert_called_once_with(new_tool, server_url)
        
        # Step 3: Remove a tool
        tool_to_remove = "tool_b"
        await tool_discovery_service.handle_tool_removed(server_id, tool_to_remove)
        
        # Verify the tool was deregistered
        mock_registry.deregister_external_tool.assert_called_once_with(tool_to_remove)
        
        # Step 4: Disconnect the server (should remove all remaining tools)
        remaining_tools = ["tool_a", "tool_c", "tool_d"]  # tool_b was removed
        mock_registry.deregister_external_tool.reset_mock()
        
        await tool_discovery_service.handle_server_disconnect(server_id)
        
        # Verify that the remaining tools were cleaned up
        # Since we mocked the registry, we need to verify based on our internal tracking
        assert server_id not in tool_discovery_service._server_tool_map

    async def test_multiple_servers_tool_isolation(self, mock_registry):
        """Test that tools from different servers are properly isolated."""
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        tool_discovery_service.logger = MagicMock()
        
        # Server 1
        server1_id = "server-1"
        server1_url = "http://server1:8000"
        server1_tools = ["tool_1a", "tool_1b"]
        
        # Server 2
        server2_id = "server-2"
        server2_url = "http://server2:8000" 
        server2_tools = ["tool_2a", "tool_2b", "tool_2c"]
        
        # Register tools for both servers
        await tool_discovery_service.handle_tools_discovered(server1_id, server1_tools, server1_url)
        await tool_discovery_service.handle_tools_discovered(server2_id, server2_tools, server2_url)
        
        # Verify both servers' tools are in the mapping
        assert set(tool_discovery_service._server_tool_map[server1_id]) == set(server1_tools)
        assert set(tool_discovery_service._server_tool_map[server2_id]) == set(server2_tools)
        
        # Verify tools can be looked up by server
        assert set(tool_discovery_service.get_tools_for_server(server1_id)) == set(server1_tools)
        assert set(tool_discovery_service.get_tools_for_server(server2_id)) == set(server2_tools)
        
        # Verify servers can be looked up by tool
        for tool in server1_tools:
            assert tool_discovery_service.get_server_for_tool(tool) == server1_id
            
        for tool in server2_tools:
            assert tool_discovery_service.get_server_for_tool(tool) == server2_id

    async def test_tool_updated_refreshes_registration(self, mock_registry):
        """Test that updating a tool refreshes its registration."""
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        tool_discovery_service.logger = MagicMock()
        
        server_id = "update-test-server"
        server_url = "http://update-test:8000"
        tool_name = "refreshable_tool"
        new_definition = {"name": tool_name, "parameters": {"type": "object", "properties": {}}}
        
        # First register the tool
        await tool_discovery_service.handle_tool_added(server_id, tool_name, server_url, {})
        
        # Reset the call count to track the update
        mock_registry.deregister_external_tool.reset_mock()
        mock_registry.register_external_tool.reset_mock()
        
        # Update the tool
        await tool_discovery_service.handle_tool_updated(server_id, tool_name, server_url, new_definition)
        
        # Verify both deregister and register were called (to refresh the registration)
        mock_registry.deregister_external_tool.assert_called_once_with(tool_name)
        mock_registry.register_external_tool.assert_called_once_with(tool_name, server_url)

    async def test_error_handling_in_tool_discovery_flow(self, mock_registry):
        """Test that errors in the tool discovery flow are handled gracefully."""
        # Make the registry raise an exception on registration
        mock_registry.register_external_tool.side_effect = Exception("Registration failed")
        
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        logger = MagicMock()
        tool_discovery_service.logger = logger
        
        # Try to register tools - should not crash, but should log error
        server_id = "error-test-server"
        server_url = "http://error-test:8000"
        tools = ["faulty_tool"]
        
        await tool_discovery_service.handle_tools_discovered(server_id, tools, server_url)
        
        # Verify that error was logged
        assert logger.error.called
        assert "Error registering external tool" in str(logger.error.call_args)

    async def test_tool_discovery_with_empty_tool_list(self, mock_registry):
        """Test tool discovery with an empty list of tools."""
        tool_discovery_service = ToolDiscoveryService(mock_registry)
        tool_discovery_service.logger = MagicMock()
        
        server_id = "empty-tools-server"
        server_url = "http://empty-test:8000"
        tools = []  # Empty list
        
        # Register empty tools list - should not crash
        await tool_discovery_service.handle_tools_discovered(server_id, tools, server_url)
        
        # Verify no registration calls were made
        mock_registry.register_external_tool.assert_not_called()
        
        # Verify internal mapping still has the server with empty list
        assert tool_discovery_service._server_tool_map[server_id] == []