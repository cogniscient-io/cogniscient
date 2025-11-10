"""
Unit tests for the MCP tools in the GCS Kernel.

These tests validate the functionality of MCP-related tools including:
- MCPServerListTool
- MCPServerStatusTool
- MCPServerConnectTool
- MCPServerDisconnectTool
- MCPServerRemoveTool
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from gcs_kernel.tools.mcp_tools import (
    MCPServerListTool,
    MCPServerStatusTool,
    MCPServerConnectTool,
    MCPServerDisconnectTool,
    MCPServerRemoveTool
)
from gcs_kernel.models import ToolResult


@pytest.mark.asyncio
class TestMCPServerListTool:
    """Test cases for the MCPServerListTool."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.mcp_client_manager = MagicMock()
        return kernel
    
    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create an MCPServerListTool instance for testing."""
        return MCPServerListTool(mock_kernel)
    
    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = MCPServerListTool(MagicMock())
        
        assert tool.name == "list_mcp_servers"
        assert tool.display_name == "List MCP Servers"
        assert "List all registered MCP servers" in tool.description
        assert tool.parameters["type"] == "object"
        assert tool.parameters["required"] == []
    
    async def test_execute_with_no_servers(self, tool, mock_kernel):
        """Test executing the tool when no servers are registered."""
        # Mock the client manager to return an empty list
        mock_kernel.mcp_client_manager.list_known_servers_detailed = AsyncMock(return_value=[])
        
        result = await tool.execute({})
        
        assert result.tool_name == "list_mcp_servers"
        assert result.success is True
        assert "No MCP servers are currently registered" in result.llm_content
        assert result.llm_content == result.return_display
    
    async def test_execute_with_servers(self, tool, mock_kernel):
        """Test executing the tool when servers are registered."""
        # Create mock server info
        from gcs_kernel.mcp.server_registry import MCPServerInfo
        from datetime import datetime
        
        server_info = MCPServerInfo(
            server_id="test_server_123",
            server_url="http://localhost:8080",
            name="Test Server",
            description="A test server",
            capabilities=["test_capability"],
            last_connected=datetime.now(),
            status="active"
        )
        
        # Mock the client manager to return server info
        mock_kernel.mcp_client_manager.list_known_servers_detailed = AsyncMock(
            return_value=[server_info]
        )
        
        result = await tool.execute({})
        
        assert result.tool_name == "list_mcp_servers"
        assert result.success is True
        assert "Registered MCP Servers:" in result.llm_content
        assert "test_server_123" in result.llm_content
        assert "http://localhost:8080" in result.llm_content
        assert "Test Server" in result.llm_content
        assert "active" in result.llm_content
        assert result.llm_content == result.return_display
    
    async def test_execute_with_kernel_error(self, tool, mock_kernel):
        """Test executing the tool when kernel is not available."""
        # Mock the kernel to not have mcp_client_manager
        kernel_without_manager = MagicMock()
        kernel_without_manager.mcp_client_manager = None
        tool.kernel = kernel_without_manager
        
        result = await tool.execute({})
        
        assert result.tool_name == "list_mcp_servers"
        assert result.success is False
        assert "MCP client manager not available" in result.error
        assert "MCP client manager not available" in result.llm_content
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestMCPServerStatusTool:
    """Test cases for the MCPServerStatusTool."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.mcp_client_manager = MagicMock()
        return kernel
    
    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create an MCPServerStatusTool instance for testing."""
        return MCPServerStatusTool(mock_kernel)
    
    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = MCPServerStatusTool(MagicMock())
        
        assert tool.name == "get_mcp_server_status"
        assert tool.display_name == "Get MCP Server Status"
        assert "Get the connection status" in tool.description
        assert tool.parameters["type"] == "object"
        assert "server_id" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["server_id"]
    
    async def test_execute_with_missing_server_id(self, tool):
        """Test executing the tool without required server_id parameter."""
        result = await tool.execute({})
        
        assert result.tool_name == "get_mcp_server_status"
        assert result.success is False
        assert "Missing required parameter: server_id" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_nonexistent_server(self, tool, mock_kernel):
        """Test executing the tool for a server that doesn't exist."""
        # Mock that the server doesn't exist in registry
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=False)
        
        result = await tool.execute({"server_id": "nonexistent_server"})
        
        assert result.tool_name == "get_mcp_server_status"
        assert result.success is False
        assert "not found in registry" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_valid_server(self, tool, mock_kernel):
        """Test executing the tool for a valid server."""
        from gcs_kernel.mcp.server_registry import MCPServerInfo
        from datetime import datetime
        
        server_info = MCPServerInfo(
            server_id="valid_server_123",
            server_url="http://localhost:8080",
            name="Valid Server",
            description="A valid server",
            capabilities=["capability1", "capability2"],
            last_connected=datetime.now(),
            status="active"
        )
        
        # Mock the methods to simulate a valid server
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=True)
        mock_kernel.mcp_client_manager.list_known_servers_detailed = AsyncMock(
            return_value=[server_info]
        )
        
        result = await tool.execute({"server_id": "valid_server_123"})
        
        assert result.tool_name == "get_mcp_server_status"
        assert result.success is True
        assert "MCP Server Status:" in result.llm_content
        assert "valid_server_123" in result.llm_content
        assert "http://localhost:8080" in result.llm_content
        assert "Valid Server" in result.llm_content
        assert "active" in result.llm_content
        assert "capability1" in result.llm_content
        assert "capability2" in result.llm_content
        assert result.llm_content == result.return_display


@pytest.mark.asyncio
class TestMCPServerConnectTool:
    """Test cases for the MCPServerConnectTool."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.mcp_client_manager = MagicMock()
        return kernel
    
    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create an MCPServerConnectTool instance for testing."""
        return MCPServerConnectTool(mock_kernel)
    
    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = MCPServerConnectTool(MagicMock())
        
        assert tool.name == "connect_mcp_server"
        assert tool.display_name == "Connect MCP Server"
        assert "Connect to an MCP server" in tool.description
        assert tool.parameters["type"] == "object"
        assert "server_url" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["server_url"]
    
    async def test_execute_with_missing_server_url(self, tool):
        """Test executing the tool without required server_url parameter."""
        result = await tool.execute({})
        
        assert result.tool_name == "connect_mcp_server"
        assert result.success is False
        assert "Missing required parameter: server_url" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_successful_connection(self, tool, mock_kernel):
        """Test executing the tool for a successful connection."""
        # Mock successful connection
        mock_kernel.mcp_client_manager.connect_to_server = AsyncMock(return_value=True)
        
        result = await tool.execute({
            "server_url": "http://localhost:8081",
            "server_name": "Test Server",
            "description": "A test server"
        })
        
        assert result.tool_name == "connect_mcp_server"
        assert result.success is True
        assert "Successfully connected to MCP server" in result.llm_content
        assert "http://localhost:8081" in result.llm_content
        assert result.llm_content == result.return_display
    
    async def test_execute_with_failed_connection(self, tool, mock_kernel):
        """Test executing the tool for a failed connection."""
        # Mock failed connection
        mock_kernel.mcp_client_manager.connect_to_server = AsyncMock(return_value=False)
        
        result = await tool.execute({
            "server_url": "http://localhost:8081"
        })
        
        assert result.tool_name == "connect_mcp_server"
        assert result.success is False
        assert "Failed to connect to MCP server" in result.error
        assert "http://localhost:8081" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestMCPServerDisconnectTool:
    """Test cases for the MCPServerDisconnectTool."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.mcp_client_manager = MagicMock()
        return kernel
    
    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create an MCPServerDisconnectTool instance for testing."""
        return MCPServerDisconnectTool(mock_kernel)
    
    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = MCPServerDisconnectTool(MagicMock())
        
        assert tool.name == "disconnect_mcp_server"
        assert tool.display_name == "Disconnect MCP Server"
        assert "Disconnect from an MCP server" in tool.description
        assert tool.parameters["type"] == "object"
        assert "server_id" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["server_id"]
    
    async def test_execute_with_missing_server_id(self, tool):
        """Test executing the tool without required server_id parameter."""
        result = await tool.execute({})
        
        assert result.tool_name == "disconnect_mcp_server"
        assert result.success is False
        assert "Missing required parameter: server_id" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_nonexistent_server(self, tool, mock_kernel):
        """Test executing the tool for a server that doesn't exist."""
        # Mock that the server doesn't exist in registry
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=False)
        
        result = await tool.execute({"server_id": "nonexistent_server"})
        
        assert result.tool_name == "disconnect_mcp_server"
        assert result.success is False
        assert "not found in registry" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_successful_disconnection(self, tool, mock_kernel):
        """Test executing the tool for a successful disconnection."""
        # Mock that the server exists and disconnection is successful
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=True)
        mock_kernel.mcp_client_manager.disconnect_from_server = AsyncMock(return_value=True)
        
        result = await tool.execute({"server_id": "existing_server"})
        
        assert result.tool_name == "disconnect_mcp_server"
        assert result.success is True
        assert "Successfully disconnected from MCP server" in result.llm_content
        assert "existing_server" in result.llm_content
        assert result.llm_content == result.return_display
    
    async def test_execute_with_failed_disconnection(self, tool, mock_kernel):
        """Test executing the tool for a failed disconnection."""
        # Mock that the server exists but disconnection fails
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=True)
        mock_kernel.mcp_client_manager.disconnect_from_server = AsyncMock(return_value=False)
        
        result = await tool.execute({"server_id": "existing_server"})
        
        assert result.tool_name == "disconnect_mcp_server"
        assert result.success is False
        assert "Failed to disconnect from MCP server" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestMCPServerRemoveTool:
    """Test cases for the MCPServerRemoveTool."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.mcp_client_manager = MagicMock()
        return kernel
    
    @pytest_asyncio.fixture
    def tool(self, mock_kernel):
        """Create an MCPServerRemoveTool instance for testing."""
        return MCPServerRemoveTool(mock_kernel)
    
    async def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = MCPServerRemoveTool(MagicMock())
        
        assert tool.name == "remove_mcp_server"
        assert tool.display_name == "Remove MCP Server"
        assert "Remove an MCP server from the registry" in tool.description
        assert tool.parameters["type"] == "object"
        assert "server_id" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["server_id"]
    
    async def test_execute_with_missing_server_id(self, tool):
        """Test executing the tool without required server_id parameter."""
        result = await tool.execute({})
        
        assert result.tool_name == "remove_mcp_server"
        assert result.success is False
        assert "Missing required parameter: server_id" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_nonexistent_server(self, tool, mock_kernel):
        """Test executing the tool for a server that doesn't exist."""
        # Mock that the server doesn't exist in registry
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=False)
        
        result = await tool.execute({"server_id": "nonexistent_server"})
        
        assert result.tool_name == "remove_mcp_server"
        assert result.success is False
        assert "not found in registry" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display
    
    async def test_execute_with_successful_removal(self, tool, mock_kernel):
        """Test executing the tool for a successful server removal."""
        # Mock that the server exists and removal is successful
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=True)
        mock_kernel.mcp_client_manager.remove_known_server = AsyncMock(return_value=True)
        
        result = await tool.execute({"server_id": "existing_server"})
        
        assert result.tool_name == "remove_mcp_server"
        assert result.success is True
        assert "Successfully removed MCP server" in result.llm_content
        assert "existing_server" in result.llm_content
        assert result.llm_content == result.return_display
    
    async def test_execute_with_failed_removal(self, tool, mock_kernel):
        """Test executing the tool for a failed server removal."""
        # Mock that the server exists but removal fails
        mock_kernel.mcp_client_manager.server_exists = AsyncMock(return_value=True)
        mock_kernel.mcp_client_manager.remove_known_server = AsyncMock(return_value=False)
        
        result = await tool.execute({"server_id": "existing_server"})
        
        assert result.tool_name == "remove_mcp_server"
        assert result.success is False
        assert "Failed to remove MCP server" in result.error
        assert result.error == result.llm_content
        assert result.error == result.return_display


@pytest.mark.asyncio
class TestMCPToolsRegistration:
    """Test cases for MCP tools registration function."""
    
    @pytest_asyncio.fixture
    def mock_kernel(self):
        """Create a mock kernel for testing."""
        kernel = MagicMock()
        kernel.registry = MagicMock()
        kernel.logger = MagicMock()
        return kernel
    
    async def test_register_mcp_tools_success(self, mock_kernel):
        """Test successful registration of all MCP tools."""
        # Mock successful registration for all tools
        mock_kernel.registry.register_tool = AsyncMock(return_value=True)
        
        from gcs_kernel.tools.mcp_tools import register_mcp_tools
        success = await register_mcp_tools(mock_kernel)
        
        assert success is True
        # Verify that register_tool was called 5 times (for the 5 MCP tools)
        assert mock_kernel.registry.register_tool.call_count == 5
        assert mock_kernel.logger.info.called
        assert "Successfully registered 5 MCP tools" in str(mock_kernel.logger.info.call_args)
    
    async def test_register_mcp_tools_failure(self, mock_kernel):
        """Test failure during registration of MCP tools."""
        # Mock the registry to fail on the first tool registration
        mock_kernel.registry.register_tool = AsyncMock(return_value=False)
        
        from gcs_kernel.tools.mcp_tools import register_mcp_tools
        success = await register_mcp_tools(mock_kernel)
        
        assert success is False
        assert mock_kernel.registry.register_tool.call_count == 1  # Stops after first failure
        assert mock_kernel.logger.error.called
    
    async def test_register_mcp_tools_no_registry(self):
        """Test MCP tools registration when registry is not available."""
        # Create kernel with no registry
        kernel_without_registry = MagicMock()
        # Set the registry attribute to None to trigger the hasattr check
        kernel_without_registry.registry = None
        kernel_without_registry.logger = MagicMock()
        
        from gcs_kernel.tools.mcp_tools import register_mcp_tools
        success = await register_mcp_tools(kernel_without_registry)
        
        assert success is False
        assert kernel_without_registry.logger.error.called
        assert "Kernel registry not available" in str(kernel_without_registry.logger.error.call_args)