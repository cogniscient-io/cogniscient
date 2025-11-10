"""
Tests for CLI UI Components
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ui.common.kernel_api import KernelAPIClient
from ui.cli.cli import main
from ui.common.cli_ui import CLIUI


class MockKernelAPI:
    """Mock implementation of KernelAPI for CLI tests."""
    
    def __init__(self):
        self.prompt_responses = {}
    
    async def send_user_prompt(self, prompt: str) -> str:
        return f"Response to: {prompt}"
    
    def stream_user_prompt(self, prompt: str):
        # This should be an async generator (not a coroutine that returns generator)
        async def async_gen():
            yield f"Streaming response to: {prompt}"
        return async_gen()
    
    def get_kernel_status(self) -> str:
        return "Mock kernel running: True"
    
    def list_registered_tools(self) -> list:
        return ["test_tool_1", "test_tool_2"]
    
    async def get_available_tools(self):
        return {
            "test_tool_1": MagicMock(description="A test tool"),
            "test_tool_2": MagicMock(description="Another test tool")
        }
    
    async def execute_tool(self, tool_name: str, params: dict):
        return f"execution_{tool_name}"
    
    async def get_tool_result(self, execution_id: str):
        from gcs_kernel.models import ToolResult
        return ToolResult(
            tool_name="test_tool",
            llm_content="Test result content",
            return_display="Test display display result",
            success=True
        )


@pytest.mark.asyncio
class TestCLIUI:
    """Test cases for CLI UI functionality."""
    
    async def test_cli_ui_display_streaming_response(self):
        """Test CLI UI streaming response."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        # Test streaming response
        response = await cli_ui.display_streaming_response("test prompt")
        assert response == "Streaming response to: test prompt"
    
    async def test_cli_ui_display_response(self):
        """Test CLI UI response display."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        response = await cli_ui.display_response("test prompt")
        assert response == "Response to: test prompt"
    
    async def test_cli_ui_help_command(self):
        """Test CLI UI help command."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        # Check that help method doesn't raise an exception
        cli_ui.show_help()  # This method prints help to stdout
    
    async def test_cli_ui_list_tools(self):
        """Test CLI UI list tools functionality."""
        mock_api = MockKernelAPI()
        cli_ui = CLIUI(mock_api)
        
        # We'll test by mocking the kernel API
        mock_api = MagicMock()
        mock_api.get_available_tools = AsyncMock(return_value={
            "test_tool": MagicMock(description="A test tool")
        })
        
        # Replace the kernel API in cli_ui
        original_api = cli_ui.kernel_api
        cli_ui.kernel_api = mock_api
        
        # This should not raise an exception
        await cli_ui._list_tools()
        
        # Restore original api
        cli_ui.kernel_api = original_api


@pytest.mark.asyncio
class TestCLICommands:
    """Test specific CLI commands."""
    
    @pytest.mark.skip(reason="Main function is complex to test directly")
    async def test_cli_main_function(self):
        """Test the CLI main function."""
        # This is complex to test due to argument parsing and kernel initialization
        # Skip for now as it's better tested via integration tests
        pass
    
    @pytest.mark.skip(reason="Interactive loop is complex to test")
    async def test_cli_interactive_loop(self):
        """Test the CLI interactive loop."""
        # This is complex to test as it involves user input
        # Skip for now as it's better tested via integration tests
        pass