"""
Unit tests for the Tool Registry system in the GCS Kernel.
"""
import pytest
import pytest_asyncio
import asyncio
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool
from gcs_kernel.tools.shell_command import ShellCommandTool


class MockTool:
    """Mock tool for testing purposes."""
    name = "mock_tool"
    display_name = "Mock Tool"
    description = "A mock tool for testing"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        },
        "required": ["param1"]
    }
    
    async def execute(self, parameters):
        from gcs_kernel.models import ToolResult
        return ToolResult(
            tool_name=self.name,
            success=True,
            llm_content=f"Executed mock tool with param1={parameters.get('param1')}",
            return_display=f"Executed mock tool with param1={parameters.get('param1')}"
        )


@pytest.mark.asyncio
class TestToolRegistry:
    """Test cases for the ToolRegistry class."""
    
    @pytest_asyncio.fixture
    async def registry(self):
        """Create a ToolRegistry instance for testing."""
        registry = ToolRegistry()
        await registry.initialize()
        yield registry
        await registry.shutdown()
    
    async def test_register_tool(self, registry):
        """Test registering a tool with the registry."""
        mock_tool = MockTool()
        result = await registry.register_tool(mock_tool)
        
        assert result is True
        assert mock_tool.name in registry.tools
        assert registry.tools[mock_tool.name] == mock_tool
    
    async def test_deregister_tool(self, registry):
        """Test deregistering a tool from the registry."""
        mock_tool = MockTool()
        await registry.register_tool(mock_tool)
        
        result = await registry.deregister_tool(mock_tool.name)
        
        assert result is True
        assert mock_tool.name not in registry.tools
    
    async def test_get_tool(self, registry):
        """Test getting a tool by name."""
        mock_tool = MockTool()
        await registry.register_tool(mock_tool)
        
        retrieved_tool = await registry.get_tool(mock_tool.name)
        
        assert retrieved_tool == mock_tool
    
    async def test_get_all_tools(self, registry):
        """Test getting all registered tools."""
        # Check initial state - should have no built-in tools by default (new architecture)
        initial_tools = registry.get_all_tools()
        initial_count = len(initial_tools)
        assert initial_count == 0  # No built-in tools in new architecture
        
        mock_tool = MockTool()
        await registry.register_tool(mock_tool)
        
        all_tools = registry.get_all_tools()
        
        assert len(all_tools) == initial_count + 1  # Should now have 1 tool
        assert mock_tool.name in all_tools
    
    async def test_register_builtin_tools(self, registry):
        """Test that built-in tools can be registered manually."""
        tools = registry.get_all_tools()
        # Initially, no tools are registered in the new architecture
        assert len(tools) == 0

        # Register the built-in tools manually to test functionality
        from gcs_kernel.tools.file_operations import ReadFileTool, WriteFileTool, ListDirectoryTool
        from gcs_kernel.tools.shell_command import ShellCommandTool

        await registry.register_tool(ReadFileTool())
        await registry.register_tool(WriteFileTool())
        await registry.register_tool(ListDirectoryTool())
        await registry.register_tool(ShellCommandTool())

        tools = registry.get_all_tools()

        # Check that built-in tools are now registered
        expected_tools = ["read_file", "write_file", "list_directory", "shell_command"]
        for tool_name in expected_tools:
            assert tool_name in tools.keys()
    
    async def test_read_file_tool_registration(self, registry):
        """Test that ReadFileTool is properly registered."""
        # First register the tool
        await registry.register_tool(ReadFileTool())
        tools = registry.get_all_tools()
        assert "read_file" in tools.keys()
        assert isinstance(tools["read_file"], ReadFileTool)
    
    async def test_write_file_tool_registration(self, registry):
        """Test that WriteFileTool is properly registered."""
        # First register the tool
        await registry.register_tool(WriteFileTool())
        tools = registry.get_all_tools()
        assert "write_file" in tools.keys()
        assert isinstance(tools["write_file"], WriteFileTool)
    
    async def test_list_directory_tool_registration(self, registry):
        """Test that ListDirectoryTool is properly registered."""
        # First register the tool
        await registry.register_tool(ListDirectoryTool())
        tools = registry.get_all_tools()
        assert "list_directory" in tools.keys()
        assert isinstance(tools["list_directory"], ListDirectoryTool)
    
    async def test_shell_command_tool_registration(self, registry):
        """Test that ShellCommandTool is properly registered."""
        # First register the tool
        await registry.register_tool(ShellCommandTool())
        tools = registry.get_all_tools()
        assert "shell_command" in tools.keys()
        assert isinstance(tools["shell_command"], ShellCommandTool)
    
    async def test_discover_command_based_tools(self, registry):
        """Test command-based tool discovery."""
        discovered_tools = await registry.discover_command_based_tools()
        
        # At least git or docker should be available in most environments
        # If not, the function should return an empty dict
        assert isinstance(discovered_tools, dict)
        # The function should return at least an empty dict without errors