"""
Test for the updated MCP Client Service with Streamable HTTP Connection Manager.

This test verifies that the StreamableHttpConnectionManager correctly uses 
the official MCP SDK pattern with proper async context managers.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from mcp.client.session import ClientSession
from mcp.types import ListToolsResult

from cogniscient.engine.services.mcp_client_service import StreamableHttpConnectionManager


class TestStreamableHttpConnectionManager:
    """Tests for the updated StreamableHttpConnectionManager."""

    @pytest.mark.asyncio
    async def test_call_tool_with_sdk_pattern(self):
        """Test that calling tools uses the official SDK pattern."""
        connection_params = {
            "type": "http", 
            "url": "http://127.0.0.1:8080/mcp",
            "timeout": 10.0,
            "sse_read_timeout": 30.0
        }
        
        manager = StreamableHttpConnectionManager(connection_params)
        
        # Mock the _execute_with_session method to avoid actual connection
        mock_result = {"test": "result"}
        with patch.object(manager, '_execute_with_session') as mock_execute:
            mock_execute.return_value = mock_result
            
            # Call a tool
            result = await manager.call_tool("test_tool", {"param": "value"})
            
            # Verify that _execute_with_session was called with the right operation
            assert mock_execute.called
            # Check that the operation function passed to _execute_with_session 
            # calls session.call_tool with correct parameters
            args, kwargs = mock_execute.call_args
            operation_func = args[0]
            
            # Create a mock session to test the operation
            mock_session = AsyncMock()
            mock_session.call_tool.return_value = mock_result
            operation_result = await operation_func(mock_session)
            
            # Verify the call was made properly
            mock_session.call_tool.assert_called_once_with("test_tool", {"param": "value"})
            assert operation_result == mock_result
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_list_tools_with_sdk_pattern(self):
        """Test that listing tools uses the official SDK pattern."""
        connection_params = {
            "type": "http",
            "url": "http://127.0.0.1:8080/mcp", 
            "timeout": 10.0,
            "sse_read_timeout": 30.0
        }
        
        manager = StreamableHttpConnectionManager(connection_params)
        
        # Mock the _execute_with_session method to avoid actual connection
        # Creating a mock that resembles the structure without requiring full validation
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        
        with patch.object(manager, '_execute_with_session') as mock_execute:
            mock_execute.return_value = mock_result
            
            # List tools
            result = await manager.list_tools()
            
            # Verify that _execute_with_session was called with the right operation
            assert mock_execute.called
            # Check that the operation function passed to _execute_with_session 
            # calls session.list_tools
            args, kwargs = mock_execute.call_args
            operation_func = args[0]
            
            # Create a mock session to test the operation
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = mock_result
            operation_result = await operation_func(mock_session)
            
            # Verify the call was made properly
            mock_session.list_tools.assert_called_once()
            assert operation_result == mock_result
            assert result == mock_result

    def test_initialization_properties(self):
        """Test that the manager initializes with correct properties."""
        connection_params = {
            "type": "http",
            "url": "http://127.0.0.1:8080/mcp",
            "timeout": 15.0,
            "sse_read_timeout": 45.0,
            "headers": {"Authorization": "Bearer token123"},
            "authorization": "Bearer token123"
        }
        
        manager = StreamableHttpConnectionManager(connection_params)
        
        # Verify properties are set correctly
        assert manager.url == "http://127.0.0.1:8080/mcp"
        assert manager.timeout == 15.0
        assert manager.sse_read_timeout == 45.0
        assert manager.headers["Authorization"] == "Bearer token123"