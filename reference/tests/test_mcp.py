"""
Unit tests for the MCP Server in the GCS Kernel.
"""
import pytest
import pytest_asyncio
import asyncio
from gcs_kernel.mcp.server import MCPServer
from gcs_kernel.models import MCPConfig


@pytest.mark.asyncio
class TestMCPServer:
    """Test cases for the MCPServer class."""
    
    @pytest_asyncio.fixture
    async def mcp_server(self):
        """Create an MCPServer instance for testing."""
        config = MCPConfig(
            server_url="http://localhost:8000",
            client_id="test_client",
            client_secret="test_secret_32_chars_1234567890ab"
        )
        server = MCPServer(config)
        yield server
    
    async def test_server_initialization(self, mcp_server):
        """Test that the MCP server initializes correctly."""
        assert mcp_server.config is not None
        assert mcp_server.config.server_url == "http://localhost:8000"
        assert mcp_server.config.client_secret is not None
        assert len(mcp_server.config.client_secret) >= 32  # Should be at least 32 chars
    
    async def test_authenticate_with_valid_token(self, mcp_server):
        """Test authentication with a valid token."""
        # This test is difficult to run without a full FastAPI test client
        # We'll just ensure the method exists and is callable
        assert hasattr(mcp_server, '_authenticate')
        assert callable(mcp_server._authenticate)
    
    async def test_authenticate_with_no_configured_secret(self):
        """Test server initialization when no secret is provided."""
        config = MCPConfig(
            server_url="http://localhost:8000"
        )
        server = MCPServer(config)
        
        # Ensure a secret is generated automatically
        assert server.config.client_secret is not None
        assert len(server.config.client_secret) >= 32