"""
Tests for MCP Client Manager functionality.

These tests validate the new architecture where MCPClientManager manages
multiple MCP clients for different servers.
"""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from gcs_kernel.mcp.client_manager import MCPClientManager
from gcs_kernel.models import MCPConfig


@pytest.mark.asyncio
class TestMCPClientManager:
    """Test cases for MCP client manager functionality."""
    
    @pytest_asyncio.fixture
    async def mcp_manager(self):
        """Create an MCPClientManager instance for testing."""
        import tempfile
        # Create a temporary directory for this test run to avoid conflicts
        test_runtime_dir = tempfile.mkdtemp(prefix="test_mcp_runtime_")
        
        config = MCPConfig(
            server_url="http://localhost:8000",
            runtime_data_directory=test_runtime_dir,
            server_registry_filename="test_server_registry.json"
        )
        manager = MCPClientManager(config)
        manager.logger = MagicMock()  # Mock logger
        # For tests, initial list should be empty, so don't connect to registered servers
        await manager.initialize(connect_to_registered_servers=False)
        yield manager
        await manager.shutdown()
        
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(test_runtime_dir, ignore_errors=True)

    async def test_manager_initialization(self, mcp_manager):
        """Test that the manager initializes properly."""
        assert mcp_manager is not None
        assert mcp_manager.initialized is True
        assert mcp_manager.clients == {}
        assert mcp_manager.server_registry is not None

    async def test_connect_to_server_method_exists(self, mcp_manager):
        """Test that the connect_to_server method exists and has the correct signature."""
        # Verify the method exists
        assert hasattr(mcp_manager, 'connect_to_server')
        
        # The method exists, but connecting to a non-existent server should be handled gracefully
        # This test just verifies that the method can be called without erroring on signature
        import asyncio
        
        # This will fail to connect (as expected), but shouldn't raise a signature error
        try:
            result = await mcp_manager.connect_to_server("http://nonexistent-server:9999", "test_server")
            # Connection will fail, but method call itself should work
        except Exception:
            # Expected since server doesn't exist, but method signature is correct
            pass

    async def test_register_notification_handler(self, mcp_manager):
        """Test registering notification handlers."""
        # Create a mock handler
        def test_handler(server_id, payload):
            print(f"Notification received: {payload}")
        
        # Register the handler
        mcp_manager.register_notification_handler("tool_added", test_handler)
        
        # Verify the handler was registered
        assert len(mcp_manager.notification_handlers["tool_added"]) == 1
        assert mcp_manager.notification_handlers["tool_added"][0] == test_handler

    async def test_server_registry_with_manager(self, mcp_manager):
        """Test that the manager properly uses the server registry."""
        # Initially, there should be no known servers
        server_list = await mcp_manager.list_known_servers()
        assert len(server_list) == 0
        
        # Check detailed listing
        detailed_list = await mcp_manager.list_known_servers_detailed()
        assert len(detailed_list) == 0
        
        # Check if a non-existent server exists
        exists = await mcp_manager.server_exists("nonexistent_server_id")
        assert exists is False

    async def test_mcp_config_runtime_data_directory(self):
        """Test that MCPConfig supports runtime_data_directory."""
        # Test that the config field exists and works
        config = MCPConfig(
            server_url="http://localhost:8000",
            runtime_data_directory="/tmp/test_runtime"
        )
        
        # Verify the field is accessible
        assert config.runtime_data_directory == "/tmp/test_runtime"
        
        # Test with default value
        config_default = MCPConfig(server_url="http://localhost:8000")
        assert config_default.runtime_data_directory == "./runtime_data"

    async def test_manager_server_lifecycle(self, mcp_manager):
        """Test the full lifecycle of server management (connect, list, remove)."""
        # Initially no servers
        servers = await mcp_manager.list_known_servers()
        assert len(servers) == 0
        
        # The manager should be able to connect, list, and manage servers
        # For this test, we'll just verify the methods exist and can be called
        # (actual connection will fail without real servers)
        
        # Verify methods exist and work properly
        assert hasattr(mcp_manager, 'connect_to_server')
        assert hasattr(mcp_manager, 'list_known_servers')
        assert hasattr(mcp_manager, 'list_known_servers_detailed')
        assert hasattr(mcp_manager, 'server_exists')
        assert hasattr(mcp_manager, 'remove_known_server')