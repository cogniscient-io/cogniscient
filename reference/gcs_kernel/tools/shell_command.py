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