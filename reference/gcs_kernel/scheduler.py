"""
Tool Execution Scheduler implementation for the GCS Kernel.

This module implements the ToolExecutionScheduler class which manages
the complete lifecycle of tool execution with validation, approval, scheduling,
and execution states.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from jsonschema import validate, ValidationError
from gcs_kernel.models import ToolDefinition, ToolExecution, ToolState, ToolResult, ToolApprovalMode


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
        self.resource_quotas = {} # Store resource quotas for tools

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
        
        # Determine if approval is needed and set approval mode
        approval_mode = await self._determine_approval_mode(tool_def, execution)
        execution.approval_mode = approval_mode
        
        # Check if approval is required based on mode
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
        Validate parameters against the tool definition's schema using JSON Schema validation.
        
        Args:
            tool_def: The tool definition containing the schema
            params: The parameters to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Use the jsonschema library to validate parameters against the schema
            validate(instance=params, schema=tool_def.parameter_schema)
            return True
        except ValidationError as e:
            if self.logger:
                self.logger.error(f"Parameter validation failed: {e.message}")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error during parameter validation: {str(e)}")
            return False

    async def _determine_approval_mode(self, tool_def: ToolDefinition, execution: ToolExecution) -> ToolApprovalMode:
        """
        Determine the approval mode for a tool execution.
        
        Args:
            tool_def: The tool definition
            execution: The tool execution
            
        Returns:
            The appropriate ToolApprovalMode
        """
        # In a real system, this would determine the approval mode based on
        # tool definition, execution parameters, and possibly security policies
        # For now, return the default mode unless overridden in tool definition
        if hasattr(tool_def, 'approval_mode') and tool_def.approval_mode:
            return tool_def.approval_mode
        return ToolApprovalMode.DEFAULT

    def _requires_approval(self, tool_def: ToolDefinition, execution: ToolExecution) -> bool:
        """
        Determine if a tool execution requires approval based on the mode.
        
        Args:
            tool_def: The tool definition
            execution: The tool execution
            
        Returns:
            True if approval is required, False otherwise
        """
        # Approval is not required based on mode
        if execution.approval_mode == ToolApprovalMode.YOLO:
            return False
        elif execution.approval_mode == ToolApprovalMode.AUTO_EDIT:
            # Auto-edit may have specific conditions where approval is not required
            return tool_def.approval_required
        elif execution.approval_mode == ToolApprovalMode.PLAN:
            # Plan mode may require approval for certain operations
            return tool_def.approval_required
        else:  # DEFAULT
            return tool_def.approval_required

    async def _approve_tool_execution(self, execution: ToolExecution) -> bool:
        """
        Approve a tool execution based on its approval mode.
        
        Args:
            execution: The tool execution to approve
            
        Returns:
            True if approved, False otherwise
        """
        if execution.approval_mode == ToolApprovalMode.YOLO:
            # In YOLO mode, auto-approve without user interaction
            return True
        elif execution.approval_mode == ToolApprovalMode.AUTO_EDIT:
            # For auto-edit mode, check if it's a safe operation
            # In a real system, you'd have more complex logic here
            return True
        elif execution.approval_mode == ToolApprovalMode.PLAN:
            # For plan mode, you might want to approve or reject based on
            # whether the tool execution aligns with the current plan
            # For now, always approve
            return True
        else:  # DEFAULT
            # Default mode - for now, approve everything
            # In a real system, this would involve user interaction
            return True

    async def _execute_tool(self, execution: ToolExecution):
        """
        Execute a tool with the given parameters.
        
        Args:
            execution: The tool execution to perform
        """
        execution.state = ToolState.EXECUTING
        execution.executed_at = datetime.now()
        
        # Check resource quotas before executing the tool
        if not await self._check_resource_quotas(execution):
            execution.result = ToolResult(
                tool_name=execution.tool_name,
                success=False,
                error="Resource quota exceeded",
                llm_content="Tool execution denied due to resource quota limits",
                return_display="Tool execution denied due to resource quota limits"
            )
            execution.state = ToolState.COMPLETED
            execution.completed_at = datetime.now()
            return
        
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

    async def _check_resource_quotas(self, execution: ToolExecution) -> bool:
        """
        Check if the tool execution complies with resource quotas.
        
        Args:
            execution: The tool execution to check
            
        Returns:
            True if within quotas, False otherwise
        """
        # For now, just return True to allow all executions
        # In a real system, this would check CPU, memory, execution time, etc. against defined limits
        return True

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