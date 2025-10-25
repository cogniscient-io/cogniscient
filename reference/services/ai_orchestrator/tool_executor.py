"""
Tool Executor for GCS Kernel AI Orchestrator.

This module implements the ToolExecutor which handles non-interactive tool execution
as per Qwen architecture patterns.
"""

import asyncio
from typing import Any, Dict, Optional
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult, ToolDefinition


class ToolExecutor:
    """
    Executes tools in a non-interactive manner following Qwen patterns.
    Handles both local and remote tool execution with proper error handling.
    """
    
    def __init__(self, kernel_client: MCPClient, kernel=None):
        """
        Initialize the tool executor.
        
        Args:
            kernel_client: MCP client for communicating with the kernel
            kernel: Optional direct reference to kernel for registry access
        """
        self.kernel_client = kernel_client
        self.kernel = kernel
        self.registry = None  # Will be set via set_kernel_services
        self.scheduler = None  # Will be set via set_kernel_services

    async def execute_tool_call(self, 
                               tool_name: str, 
                               parameters: Dict[str, Any], 
                               signal: Optional[asyncio.Event] = None) -> ToolResult:
        """
        Execute a single tool call in non-interactive mode using kernel services.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            signal: Optional abort signal
            
        Returns:
            ToolResult containing the execution result
        """
        try:
            if signal and signal.is_set():
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error="Tool execution cancelled by user",
                    llm_content="Tool execution cancelled by user",
                    return_display="Tool execution cancelled by user"
                )
            
            # Use the kernel's registry to get the tool definition
            if self.registry:
                tool_def = await self.registry.get_tool(tool_name)
                if tool_def:
                    # Use the kernel's scheduler for execution
                    if self.scheduler:
                        # Submit the tool execution through the scheduler
                        execution_id = await self.scheduler.submit_tool_execution(tool_def, parameters)
                        
                        # Wait for the execution to complete using the scheduler
                        max_wait = 60  # seconds
                        start_time = asyncio.get_event_loop().time()
                        
                        while (asyncio.get_event_loop().time() - start_time) < max_wait:
                            result = self.scheduler.get_execution_result(execution_id)
                            if result:
                                return result
                            await asyncio.sleep(0.5)  # Check every 0.5 seconds
                        
                        # Timeout case
                        return ToolResult(
                            tool_name=tool_name,
                            success=False,
                            error=f"Tool execution {execution_id} did not return a result within timeout",
                            llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                            return_display=f"Tool execution {execution_id} did not return a result within timeout"
                        )
                    else:
                        # Fallback: execute directly if scheduler not available
                        return await tool_def.execute(parameters)
                else:
                    # Tool not found in registry
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Tool '{tool_name}' not found in registry",
                        llm_content=f"Tool '{tool_name}' not found in registry",
                        return_display=f"Tool '{tool_name}' not found in registry"
                    )
            else:
                # Use MCP client as fallback
                execution_id = await self.kernel_client.submit_tool_execution(
                    tool_name,
                    parameters
                )
                
                # Wait for tool execution to complete with timeout
                result = await self._wait_for_execution_result(execution_id, timeout=60)
                if result:
                    return result
                else:
                    # Handle the case where no result was returned
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"Tool execution {execution_id} did not return a result within timeout",
                        llm_content=f"Tool execution {execution_id} did not return a result within timeout",
                        return_display=f"Tool execution {execution_id} did not return a result within timeout"
                    )
                    
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Error executing tool {tool_name}: {str(e)}",
                llm_content=f"Error executing tool {tool_name}: {str(e)}",
                return_display=f"Error executing tool {tool_name}: {str(e)}"
            )

    async def _wait_for_execution_result(self, execution_id: str, timeout: int = 60):
        """
        Wait for an execution to complete and return its result.
        
        Args:
            execution_id: The ID of the execution to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            The execution result or None if timeout occurs
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            result = await self.kernel_client.get_execution_result(execution_id)
            if result:
                return result
            await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
        return None

    async def execute_multiple_tool_calls(self, 
                                        tool_calls: list, 
                                        signal: Optional[asyncio.Event] = None) -> Dict[str, ToolResult]:
        """
        Execute multiple tool calls concurrently in non-interactive mode.
        
        Args:
            tool_calls: List of tool calls to execute, each with name and parameters
            signal: Optional abort signal
            
        Returns:
            Dictionary mapping tool call IDs to their results
        """
        if signal and signal.is_set():
            return {}
        
        # Create tasks for all tool calls
        tasks = []
        for tool_call in tool_calls:
            task = self.execute_tool_call(
                tool_call.get("name", ""),
                tool_call.get("arguments", {}),
                signal
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results back to tool call IDs
        result_map = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exception case
                tool_name = tool_calls[i].get("name", f"unknown_tool_{i}")
                result_map[tool_calls[i].get("id", f"call_{i}")] = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Error executing tool: {str(result)}",
                    llm_content=f"Error executing tool {tool_name}: {str(result)}",
                    return_display=f"Error executing tool {tool_name}: {str(result)}"
                )
            else:
                result_map[tool_calls[i].get("id", f"call_{i}")] = result
        
        return result_map