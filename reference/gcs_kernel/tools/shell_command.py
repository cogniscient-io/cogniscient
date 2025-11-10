"""
Shell command execution tool implementation for the GCS Kernel.
"""
import subprocess
import json
from typing import Dict, Any

from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class ShellCommandTool:
    """
    Tool to execute shell commands.
    """
    name = "shell_command"
    display_name = "Shell Command"
    description = "Execute a shell command and return the output"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout for the command in seconds (default: 30)",
                "default": 30
            }
        },
        "required": ["command"]
    }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the shell command tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        command = parameters.get("command")
        timeout = parameters.get("timeout", 30)
        
        if not command:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Missing command parameter",
                llm_content="Missing command parameter",
                return_display="Missing command parameter"
            )
        
        try:
            # Execute the command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                output = result.stdout
            else:
                output = f"Command failed with exit code {result.returncode}\n{result.stderr}"
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=output,
                return_display=output
            )
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


async def register_shell_command_tools(kernel) -> bool:
    """
    Register all shell command tools with the kernel registry.
    This should be called after the kernel and registry are initialized.
    
    Args:
        kernel: The GCSKernel instance
        
    Returns:
        True if registration was successful, False otherwise
    """
    import time
    start_time = time.time()
    
    from gcs_kernel.registry import ToolRegistry
    
    # Check if the kernel and registry are available
    if not kernel or not hasattr(kernel, 'registry'):
        if hasattr(kernel, 'logger') and kernel.logger:
            kernel.logger.error("Kernel registry not available for shell command tool registration")
        return False

    registry = kernel.registry
    
    if hasattr(kernel, 'logger') and kernel.logger:
        kernel.logger.debug("Starting shell command tools registration...")
    
    # List of shell command tools to register
    shell_command_tools = [
        ShellCommandTool()
    ]
    
    # Register each shell command tool
    for tool in shell_command_tools:
        if hasattr(kernel, 'logger') and kernel.logger:
            kernel.logger.debug(f"Registering shell command tool: {tool.name}")
        
        success = await registry.register_tool(tool)
        if not success:
            if hasattr(kernel, 'logger') and kernel.logger:
                kernel.logger.error(f"Failed to register shell command tool: {tool.name}")
            return False
    
    elapsed = time.time() - start_time
    if hasattr(kernel, 'logger') and kernel.logger:
        kernel.logger.info(f"Successfully registered {len(shell_command_tools)} shell command tools (elapsed: {elapsed:.2f}s)")
    
    return True