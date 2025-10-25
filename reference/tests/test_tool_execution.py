#!/usr/bin/env python3
"""
Test script to verify tool execution in the GCS Kernel.
"""
import asyncio
import subprocess
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import ToolResult


async def test_shell_command_tool():
    """Test the shell command tool directly."""
    print("Testing shell command tool directly...")
    
    # Import the tool
    from gcs_kernel.tools.shell_command import ShellCommandTool
    
    # Create an instance of the tool
    shell_tool = ShellCommandTool()
    
    # Test a simple command
    result = await shell_tool.execute({"command": "echo 'Hello from shell command tool!'"})
    
    print(f"Tool execution result: {result.success}")
    print(f"Tool output: {result.return_display}")
    
    # Test a command that might take longer
    result2 = await shell_tool.execute({"command": "uname -a"})
    
    print(f"System info result: {result2.success}")
    print(f"System info: {result2.return_display}")


async def test_kernel_tool_registry():
    """Test the kernel's tool registry."""
    print("\nTesting kernel tool registry...")
    
    kernel = GCSKernel()
    
    # Initialize the kernel components
    await kernel._initialize_components()
    
    # List all registered tools
    tools = kernel.registry.get_all_tools()
    print(f"Registered tools: {list(tools.keys())}")
    
    # Try to get and execute the shell command tool directly
    shell_tool = await kernel.registry.get_tool("shell_command")
    if shell_tool:
        print("Found shell_command tool, testing execution...")
        result = await shell_tool.execute({"command": "date"})
        print(f"Shell command result: {result.return_display}")
    else:
        print("shell_command tool not found in registry")
    
    # Clean up
    await kernel._cleanup_components()


if __name__ == "__main__":
    print("Testing GCS Kernel tool functionality...")
    
    # Test direct tool execution
    asyncio.run(test_shell_command_tool())
    
    # Test through kernel registry
    asyncio.run(test_kernel_tool_registry())