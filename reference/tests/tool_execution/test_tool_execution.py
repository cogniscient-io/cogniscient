#!/usr/bin/env python3
"""
Test script to verify tool execution in the GCS Kernel.
"""
import asyncio
import pytest
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
    
    # Assertions to validate the test
    assert result is not None
    assert result.success is True
    assert "Hello from shell command tool!" in result.return_display
    
    # Test a command that might take longer
    result2 = await shell_tool.execute({"command": "uname -a"})
    
    assert result2 is not None
    assert result2.success is True
    assert result2.return_display is not None


@pytest.mark.asyncio
async def test_kernel_tool_registry():
    """Test the kernel's tool registry."""
    kernel = GCSKernel()
    
    # Initialize the kernel components
    await kernel._initialize_components()
    
    # List all registered tools
    tools = kernel.registry.get_all_tools()
    registered_tool_names = list(tools.keys())
    
    # Verify that at least some tools are registered
    assert len(registered_tool_names) > 0
    
    # Try to get and execute the shell command tool directly
    shell_tool = await kernel.registry.get_tool("shell_command")
    if shell_tool:
        result = await shell_tool.execute({"command": "echo test"})
        assert result is not None
        assert result.success is True
    else:
        # If shell command is not available, at least verify that some tool exists
        assert len(registered_tool_names) > 0
    
    # Clean up
    await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing GCS Kernel tool functionality...")
    
    # Test direct tool execution
    asyncio.run(test_shell_command_tool())
    
    # Test through kernel registry
    asyncio.run(test_kernel_tool_registry())