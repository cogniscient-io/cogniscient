"""
Tool Execution Scheduler implementation for the GCS Kernel.

This module implements the ToolExecutionScheduler class which manages
the complete lifecycle of tool execution with validation, approval, scheduling,
and execution states.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from gcs_kernel.models import ToolDefinition, ToolExecution, ToolState, ToolResult


class ToolExecutionScheduler:
    """
    Tool Execution Scheduler that manages the complete lifecycle of tool execution
    with validation, approval, scheduling, and execution states.
    """
    
    def __init__(self):
        """Initialize the scheduler with necessary components."""
        self.executions: Dict[str, ToolExecution] = {}
        self.approval_queue = asyncio.Queue()
        self.logger = None  # Will be set by kernel
        self.tool_registry = None  # Will be set by kernel

    async def initialize(self):
        """Initialize the scheduler."""
        # Start the approval processing task
        asyncio.create_task(self.process_approval_queue())

    async def shutdown(self):
        """Shutdown the scheduler."""
        # Cancel all pending approvals and executions
        pass

    async def submit_tool_execution(self, tool_def: ToolDefinition, params: Dict[str, Any]) -> str:
        """
        Submit a new tool execution.
        
        Args:
            tool_def: The tool definition to execute
            params: Parameters for the tool execution
            
        Returns:
            The execution ID of the submitted tool execution
        """
        execution = ToolExecution(
            tool_name=tool_def.name,
            parameters=params,
            state=ToolState.VALIDATING
        )
        
        # Validate parameters against schema first
        if not await self._validate_parameters(tool_def, params):
            execution.state = ToolState.COMPLETED
            execution.result = ToolResult(
                tool_name=tool_def.name,
                success=False,
                error="Invalid parameters",
                llm_content="Tool execution failed due to invalid parameters",
                return_display="Tool execution failed due to invalid parameters"
            )
            self.executions[execution.id] = execution
            return execution.id
        
        # Determine if approval is needed
        if self._requires_approval(tool_def, execution):
            execution.state = ToolState.AWAITING_APPROVAL
            await self.approval_queue.put(execution)
        else:
            execution.state = ToolState.SCHEDULED
            # Schedule for immediate execution
            await self._execute_tool(execution)
        
        self.executions[execution.id] = execution
        return execution.id

    async def process_approval_queue(self):
        """Process tools awaiting approval."""
        while True:
            try:
                execution = await asyncio.wait_for(self.approval_queue.get(), timeout=0.1)
                # Process approval based on mode
                approved = await self._approve_tool_execution(execution)
                if approved:
                    execution.approved = True
                    execution.state = ToolState.SCHEDULED
                    await self._execute_tool(execution)
            except asyncio.TimeoutError:
                continue

    async def _validate_parameters(self, tool_def: ToolDefinition, params: Dict[str, Any]) -> bool:
        """
        Validate parameters against the tool definition's schema.
        
        Args:
            tool_def: The tool definition containing the schema
            params: The parameters to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Validate against the parameter schema
            schema = tool_def.parameter_schema
            # This is a simplified validation - in a real system, we would use
            # a proper JSON Schema validator
            for param_name, param_details in schema.get("properties", {}).items():
                if param_details.get("type") == "string":
                    if param_name in params and not isinstance(params[param_name], str):
                        return False
                elif param_details.get("type") == "integer":
                    if param_name in params and not isinstance(params[param_name], int):
                        return False
                elif param_details.get("type") == "number":
                    if param_name in params and not isinstance(params[param_name], (int, float)):
                        return False
                elif param_details.get("type") == "boolean":
                    if param_name in params and not isinstance(params[param_name], bool):
                        return False
                # Add more validation as needed based on schema
                
            # Check required parameters
            required_params = schema.get("required", [])
            for param in required_params:
                if param not in params:
                    return False
            
            return True
        except Exception:
            return False

    def _requires_approval(self, tool_def: ToolDefinition, execution: ToolExecution) -> bool:
        """
        Determine if a tool execution requires approval.
        
        Args:
            tool_def: The tool definition
            execution: The tool execution
            
        Returns:
            True if approval is required, False otherwise
        """
        return tool_def.approval_required

    async def _approve_tool_execution(self, execution: ToolExecution) -> bool:
        """
        Approve a tool execution based on its approval mode.
        
        Args:
            execution: The tool execution to approve
            
        Returns:
            True if approved, False otherwise
        """
        # In a real system, this would implement different approval mechanisms
        # based on the approval mode (DEFAULT, PLAN, AUTO_EDIT, YOLO)
        return True  # For now, approve everything

    async def _execute_tool(self, execution: ToolExecution):
        """
        Execute a tool with the given parameters.
        
        Args:
            execution: The tool execution to perform
        """
        execution.state = ToolState.EXECUTING
        execution.executed_at = datetime.now()
        
        try:
            # Look up the tool in the registry
            if self.tool_registry:
                tool = await self.tool_registry.get_tool(execution.tool_name)
                if tool:
                    # Execute the tool
                    result = await tool.execute(execution.parameters)
                    execution.result = result
                else:
                    execution.result = ToolResult(
                        tool_name=execution.tool_name,
                        success=False,
                        error=f"Tool '{execution.tool_name}' not found in registry",
                        llm_content=f"Tool '{execution.tool_name}' not found",
                        return_display=f"Tool '{execution.tool_name}' not found"
                    )
            else:
                execution.result = ToolResult(
                    tool_name=execution.tool_name,
                    success=False,
                    error="Tool registry not available",
                    llm_content="Tool registry not available",
                    return_display="Tool registry not available"
                )
        except Exception as e:
            execution.result = ToolResult(
                tool_name=execution.tool_name,
                success=False,
                error=str(e),
                llm_content=f"Tool execution failed: {str(e)}",
                return_display=f"Tool execution failed: {str(e)}"
            )
        
        execution.state = ToolState.COMPLETED
        execution.completed_at = datetime.now()

    def get_execution(self, execution_id: str) -> ToolExecution:
        """
        Get a tool execution by its ID.
        
        Args:
            execution_id: The ID of the execution to retrieve
            
        Returns:
            The ToolExecution object
        """
        return self.executions.get(execution_id)

    def get_execution_result(self, execution_id: str) -> ToolResult:
        """
        Get the result of a tool execution by its ID.
        
        Args:
            execution_id: The ID of the execution to retrieve the result for
            
        Returns:
            The ToolResult object
        """
        execution = self.executions.get(execution_id)
        if execution:
            return execution.result
        else:
            return None