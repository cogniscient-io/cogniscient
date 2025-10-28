"""
Test suite for tool execution in the GCS Kernel.

This module tests the direct execution of various kernel tools and their integration
with the kernel's registry system.
"""
import pytest
import subprocess
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import ToolResult


@pytest.mark.asyncio
async def test_shell_command_tool():
    """Test the shell command tool directly."""
    # Import the tool
    from gcs_kernel.tools.shell_command import ShellCommandTool
    
    # Create an instance of the tool
    shell_tool = ShellCommandTool()
    
    # Test a simple command
    result = await shell_tool.execute({"command": "echo 'Hello from shell command tool!'"})
    
    # Verify the result
    assert result.success is True
    assert "Hello from shell command tool!" in result.return_display
    assert "Hello from shell command tool!" in result.llm_content


@pytest.mark.asyncio
async def test_kernel_tool_registry():
    """Test the kernel's tool registry."""
    kernel = GCSKernel()
    
    # Initialize the kernel components
    await kernel._initialize_components()
    
    try:
        # List all registered tools
        tools = kernel.registry.get_all_tools()
        assert "shell_command" in tools  # Ensure shell command tool is registered
        
        # Try to get and execute the shell command tool directly
        shell_tool = await kernel.registry.get_tool("shell_command")
        assert shell_tool is not None, "shell_command tool should be found in registry"
        
        result = await shell_tool.execute({"command": "echo 'test command'"})
        assert result.success is True
        assert "test command" in result.return_display
    finally:
        # Clean up
        await kernel._cleanup_components()