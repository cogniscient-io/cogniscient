"""
File operations tool implementations for the GCS Kernel.
"""
import os
import json
from typing import Dict, Any
from pathlib import Path

from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class ReadFileTool:
    """
    Tool to read the contents of a file.
    """
    name = "read_file"
    display_name = "Read File"
    description = "Read the contents of a specified file"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to read"
            }
        },
        "required": ["file_path"]
    }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the read file tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        file_path = parameters.get("file_path")
        
        if not file_path:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Missing file_path parameter",
                llm_content="Missing file_path parameter",
                return_display="Missing file_path parameter"
            )
        
        try:
            # Verify the path is safe (basic check - in a real system, use more robust validation)
            if ".." in file_path or file_path.startswith("/"):
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="Invalid file path",
                    llm_content="Invalid file path",
                    return_display="Invalid file path"
                )
            
            # Combine with current directory for security
            safe_path = Path.cwd() / file_path
            if not safe_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"File {file_path} does not exist",
                    llm_content=f"File {file_path} does not exist",
                    return_display=f"File {file_path} does not exist"
                )
                
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            result = f"Contents of file {file_path}:\n{content}"
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error reading file {file_path}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class WriteFileTool:
    """
    Tool to write content to a file.
    """
    name = "write_file"
    display_name = "Write File"
    description = "Write content to a specified file"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the write file tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        file_path = parameters.get("file_path")
        content = parameters.get("content", "")
        
        if not file_path:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Missing file_path parameter",
                llm_content="Missing file_path parameter",
                return_display="Missing file_path parameter"
            )
        
        try:
            # Verify the path is safe (basic check - in a real system, use more robust validation)
            if ".." in file_path or file_path.startswith("/"):
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="Invalid file path",
                    llm_content="Invalid file path",
                    return_display="Invalid file path"
                )
            
            # Combine with current directory for security
            safe_path = Path.cwd() / file_path
            
            # Create parent directories if they don't exist
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            result = f"Successfully wrote content to file {file_path}"
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error writing file {file_path}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class ListDirectoryTool:
    """
    Tool to list the contents of a directory.
    """
    name = "list_directory"
    display_name = "List Directory"
    description = "List the contents of a specified directory"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "directory_path": {
                "type": "string",
                "description": "Path to the directory to list (default: current directory)"
            }
        },
        "required": []
    }

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the list directory tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        directory_path = parameters.get("directory_path", ".")
        
        try:
            # Verify the path is safe (basic check - in a real system, use more robust validation)
            if ".." in directory_path or directory_path.startswith("/"):
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="Invalid directory path",
                    llm_content="Invalid directory path",
                    return_display="Invalid directory path"
                )
            
            # Combine with current directory for security
            safe_path = Path.cwd() / directory_path
            if not safe_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Directory {directory_path} does not exist",
                    llm_content=f"Directory {directory_path} does not exist",
                    return_display=f"Directory {directory_path} does not exist"
                )
                
            if not safe_path.is_dir():
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"{directory_path} is not a directory",
                    llm_content=f"{directory_path} is not a directory",
                    return_display=f"{directory_path} is not a directory"
                )
            
            contents = [item.name for item in safe_path.iterdir()]
            result = f"Contents of directory {directory_path}:\n" + "\n".join(contents)
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error listing directory {directory_path}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )