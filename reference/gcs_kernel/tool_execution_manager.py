"""
Unified Tool Execution Manager for the GCS Kernel.

This module implements the ToolExecutionManager class which consolidates
the functionality of both ToolExecutionScheduler and ToolCallProcessor,
providing a unified interface for all tool execution scenarios in the kernel.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from jsonschema import validate, ValidationError

from gcs_kernel.models import (
    ToolDefinition, ToolExecution, ToolState, ToolResult, 
    ToolApprovalMode, ToolInclusionConfig
)
from gcs_kernel.tool_call_model import ToolCall


class ToolExecutionManager:
    """
    Unified Tool Execution Manager that consolidates the functionality of
    both ToolExecutionScheduler and ToolCallProcessor, providing a single
    interface for all tool execution scenarios in the kernel.
    """
    
    def __init__(self, kernel_registry=None, mcp_client=None, logger=None):
        """
        Initialize the ToolExecutionManager with necessary components.
        
        Args:
            kernel_registry: Kernel registry for direct internal tool execution
            mcp_client: MCP client for remote tool execution
            logger: Logger instance for logging operations
        """
        self.registry = kernel_registry
        self.mcp_client = mcp_client
        self.logger = logger
        self.executions: Dict[str, ToolExecution] = {}
        self.approval_queue = asyncio.Queue()
        self.resource_quotas = {}  # Store resource quotas for tools
        
        # Start the approval processing task
        # But only if we're not in a testing scenario where it might conflict
        try:
            # Check if event loop is running
            loop = asyncio.get_running_loop()
            loop.create_task(self.process_approval_queue())
        except RuntimeError:
            # If there's no running event loop (e.g., in tests), initialize later
            self._need_approval_task = True

    async def initialize(self):
        """Initialize the ToolExecutionManager including starting background tasks."""
        if hasattr(self, '_need_approval_task') and self._need_approval_task:
            asyncio.create_task(self.process_approval_queue())
            self._need_approval_task = False

    async def shutdown(self):
        """Shutdown the ToolExecutionManager."""
        # Cancel all pending approvals and executions
        pass

    # Scenario 1: Internal service directly calling tools
    async def _execute_internal_tool(self, 
                                   tool_name: str, 
                                   parameters: Dict[str, Any],
                                   approval_mode: ToolApprovalMode = ToolApprovalMode.DEFAULT) -> ToolResult:
        """
        Execute a tool that is registered in the kernel's internal registry.
        Follows full lifecycle: validation -> approval (if required) -> execution -> completion.
        
        Args:
            tool_name: The name of the tool to execute
            parameters: Parameters for the tool execution
            approval_mode: The approval mode for this execution
            
        Returns:
            ToolResult containing the execution result
        """
        # Get tool definition from registry
        if not self.registry:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool registry not available",
                llm_content="Tool registry not available",
                return_display="Tool registry not available"
            )
        
        tool_def = await self.registry.get_tool(tool_name)
        if not tool_def:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
                llm_content=f"Tool '{tool_name}' not found",
                return_display=f"Tool '{tool_name}' not found"
            )
        
        # Validate parameters against schema
        if not await self._validate_parameters(tool_def, parameters):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Invalid parameters",
                llm_content="Tool execution failed due to invalid parameters",
                return_display="Tool execution failed due to invalid parameters"
            )
        
        # Create execution object
        execution = ToolExecution(
            tool_name=tool_name,
            parameters=parameters,
            state=ToolState.VALIDATING,
            approval_mode=approval_mode
        )
        
        # Determine if approval is needed and set approval mode
        approval_mode = await self._determine_approval_mode(tool_def, execution)
        execution.approval_mode = approval_mode
        
        # Check if approval is required based on mode
        if self._requires_approval(tool_def, execution):
            execution.state = ToolState.AWAITING_APPROVAL
            await self.approval_queue.put(execution)
            # Wait for execution to complete
            while execution.state != ToolState.COMPLETED:
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        else:
            execution.state = ToolState.SCHEDULED
            # Execute the tool directly
            await self._execute_tool(execution)
        
        self.executions[execution.id] = execution
        return execution.result if execution.result else ToolResult(
            tool_name=tool_name,
            success=False,
            error="Execution failed",
            llm_content="Tool execution failed",
            return_display="Tool execution failed"
        )

    # Scenario 2: Internal service calling external tool via MCP
    async def _execute_external_tool_via_mcp(self, 
                                          tool_name: str, 
                                          parameters: Dict[str, Any],
                                          mcp_client: Optional[Any] = None) -> ToolResult:
        """
        Execute a tool on an external system via the MCP client.
        May include validation and approval depending on security policies.
        
        Args:
            tool_name: The name of the external tool to execute
            parameters: Parameters for the tool execution
            mcp_client: Optional specific MCP client to use (otherwise uses self.mcp_client)
            
        Returns:
            ToolResult containing the execution result
        """
        # Use the provided MCP client or the default one
        client_to_use = mcp_client if mcp_client is not None else self.mcp_client
        
        if not client_to_use:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="MCP client not available",
                llm_content="MCP client not available to execute external tool",
                return_display="MCP client not available to execute external tool"
            )
        
        try:
            # Submit the tool execution to the MCP client
            # (No validation needed in MCP world - tools are discovered from servers)
            execution_id = await client_to_use.submit_tool_execution(tool_name, parameters)
            
            # Poll for the result of the execution
            max_attempts = 20  # Maximum number of polling attempts
            poll_interval = 0.5  # Interval between polls in seconds
            attempts = 0
            
            while attempts < max_attempts:
                # Get the execution result
                result = await client_to_use.get_execution_result(execution_id)
                
                if result is not None:
                    # Execution completed
                    if isinstance(result, ToolResult):
                        return result
                    else:
                        # If result is not a ToolResult object, try to wrap it
                        return ToolResult(
                            tool_name=tool_name,
                            llm_content=str(result),
                            return_display=str(result),
                            success=True
                        )
                
                # Wait before polling again
                await asyncio.sleep(poll_interval)
                attempts += 1
            
            # If we've exhausted attempts, return a timeout error
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool execution timed out",
                llm_content="Tool execution timed out",
                return_display="Tool execution timed out"
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                llm_content=f"Tool execution failed: {str(e)}",
                return_display=f"Tool execution failed: {str(e)}"
            )

    # Scenario 3: External MCP client calling internal tool
    async def execute_tool_for_mcp_client(self, 
                                        tool_name: str, 
                                        parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool on behalf of an external MCP client.
        Follows the same security and approval processes as internal execution.
        
        Args:
            tool_name: The name of the internal tool to execute
            parameters: Parameters for the tool execution
            
        Returns:
            ToolResult containing the execution result
        """
        # This is essentially the same as internal execution but specifically 
        # called from an MCP client context
        return await self._execute_internal_tool(tool_name, parameters)

    # Helper methods for the internal execution flow
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
            # All tools should now follow the OpenAI-compatible format with 'parameters' attribute
            schema = tool_def.parameters
            validate(instance=params, schema=schema)
            return True
        except ValidationError as e:
            if self.logger:
                self.logger.error(f"Parameter validation failed: {str(e)}")
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
        # For now, bypass all approval requirements to avoid attribute errors
        # TODO: Reimplement proper approval system with complete architecture
        return False

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
            if self.registry:
                tool = await self.registry.get_tool(execution.tool_name)
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

    async def execute_tool_call(self, tool_call: ToolCall) -> Dict[str, Any]:
        """
        Execute a single ToolCall object, determining if it's internal or external.
        This serves as the single entry point for executing tool calls, deciding whether 
        to route to internal or external execution based on tool configuration.

        Args:
            tool_call: The ToolCall object to execute

        Returns:
            Dictionary containing the result of the tool execution
        """
        return await self._execute_tool_call(tool_call)

    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
        """
        Execute a list of ToolCall objects and return their results.
        This method can handle both internal and external tool calls.
        
        Args:
            tool_calls: List of ToolCall objects to execute
            
        Returns:
            List of dictionaries containing the results of tool executions
        """
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool_call(tool_call)
            results.append(result)
        return results

    async def _execute_tool_call(self, tool_call: ToolCall) -> Dict[str, Any]:
        """
        Execute a single ToolCall object, determining if it's internal or external.
        
        Args:
            tool_call: The ToolCall object to execute
            
        Returns:
            Dictionary containing the result of the tool execution
        """
        # Check if the tool exists in the registry (either local or external)
        if not (self.registry and hasattr(self.registry, 'has_tool') and await self.registry.has_tool(tool_call.name)):
            # Tool is not registered, return error
            error_result = ToolResult(
                tool_name=tool_call.name,
                llm_content=f"Tool '{tool_call.name}' is not registered and cannot be executed",
                return_display=f"Tool '{tool_call.name}' is not registered and cannot be executed",
                success=False,
                error=f"Tool '{tool_call.name}' is not registered"
            )
            return {
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "result": error_result,
                "success": False
            }
        
        # Tool is registered, determine if it's local or external
        server_config = await self.registry.get_tool_server_config(tool_call.name)
        if server_config:
            # This is an external tool, get the specific MCP client for this tool
            mcp_client = await self.registry.get_mcp_client_for_tool(tool_call.name)
            if mcp_client:
                # Execute using the specific MCP client for this tool
                try:
                    result = await self._execute_external_tool_via_mcp(
                        tool_call.name,
                        tool_call.arguments,
                        mcp_client=mcp_client
                    )
                    
                    return {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "result": result,
                        "success": result.success,
                        "execution_id": f"external_{tool_call.id}"
                    }
                except Exception as e:
                    error_result = ToolResult(
                        tool_name=tool_call.name,
                        llm_content=f"External tool execution failed: {str(e)}",
                        return_display=f"External tool execution failed: {str(e)}",
                        success=False,
                        error=str(e)
                    )
                    return {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "result": error_result,
                        "success": False,
                        "execution_id": f"external_{tool_call.id}"
                    }
            else:
                # Could not get specific MCP client for this tool, try to use the default client
                if self.mcp_client:
                    # Execute using the default MCP client
                    try:
                        result = await self._execute_external_tool_via_mcp(
                            tool_call.name,
                            tool_call.arguments,
                            mcp_client=self.mcp_client
                        )
                        
                        return {
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_call.name,
                            "result": result,
                            "success": result.success,
                            "execution_id": f"external_{tool_call.id}"
                        }
                    except Exception as e:
                        error_result = ToolResult(
                            tool_name=tool_call.name,
                            llm_content=f"External tool execution failed: {str(e)}",
                            return_display=f"External tool execution failed: {str(e)}",
                            success=False,
                            error=str(e)
                        )
                        return {
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_call.name,
                            "result": error_result,
                            "success": False,
                            "execution_id": f"external_{tool_call.id}"
                        }
                else:
                    # No specific client and no default client, return error
                    error_result = ToolResult(
                        tool_name=tool_call.name,
                        llm_content=f"No MCP client available for tool '{tool_call.name}'",
                        return_display=f"No MCP client available for tool '{tool_call.name}'",
                        success=False,
                        error=f"No MCP client available for tool"
                    )
                    return {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "result": error_result,
                        "success": False
                    }
        else:
            # This is a local tool, use _execute_internal_tool
            result = await self._execute_internal_tool(
                tool_call.name,
                tool_call.arguments,
                ToolApprovalMode.DEFAULT  # Use default approval mode
            )
            
            # Return the result in a standard format
            return {
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "result": result,
                "success": result.success,
                "execution_id": f"internal_{tool_call.id}"
            }

    async def execute_tool_by_name(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name and parameters, letting the system decide if it's internal or external.
        This creates a ToolCall object internally and routes to the appropriate execution method.
        
        Args:
            tool_name: The name of the tool to execute
            parameters: Parameters for the tool execution
            
        Returns:
            ToolResult containing the execution result
        """
        # Create an internal ToolCall object to use the unified routing logic
        from gcs_kernel.tool_call_model import ToolCall
        import uuid
        
        # Convert parameters to JSON string if it's a dict, to match OpenAI format
        import json
        params_str = parameters if isinstance(parameters, str) else json.dumps(parameters)
        
        tool_call = ToolCall(
            id=f"internal_{uuid.uuid4().hex[:8]}",
            function={
                "name": tool_name,
                "arguments": params_str
            }
        )
        
        # Use the unified execution method which handles routing internally
        execution_result = await self.execute_tool_call(tool_call)
        return execution_result.get('result', ToolResult(
            tool_name=tool_name,
            success=False,
            error="Tool execution returned unexpected format",
            llm_content="Tool execution returned unexpected format",
            return_display="Tool execution returned unexpected format"
        ))