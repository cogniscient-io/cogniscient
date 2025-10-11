"""
Agent Orchestrator Service for Adaptive Control System that coordinates
complex multi-agent workflows using MCP-discovered tools.

This service follows the existing codebase patterns for service interfaces and implementations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from cogniscient.engine.services.service_interface import Service
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class AgentOrchestratorService(Service):
    """
    Service that coordinates complex multi-agent workflows using MCP-discovered tools.
    """
    
    def __init__(self, 
                 mcp_service: MCPService,
                 max_concurrent_agents: int = 5,
                 workflow_timeout: int = 300):
        """
        Initialize the agent orchestrator service.
        
        Args:
            mcp_service: MCP service for tool discovery and communication
            max_concurrent_agents: Maximum number of agents that can run concurrently
            workflow_timeout: Timeout in seconds for workflow execution
        """
        self.mcp_service = mcp_service
        self.max_concurrent_agents = max_concurrent_agents
        self.workflow_timeout = workflow_timeout
        self.gcs_runtime = None  # Will be set by runtime
        
        # Track running workflows
        self.active_workflows = {}
        
    async def initialize(self) -> bool:
        """
        Initialize the agent orchestrator service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        return True
        
    async def shutdown(self) -> bool:
        """
        Shutdown the agent orchestrator service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Cancel any active workflows
        for workflow_id, task in self.active_workflows.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.active_workflows.clear()
        return True

    def set_runtime(self, runtime):
        """
        Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    async def coordinate_agents(self, 
                               agent_tasks: List[Dict[str, Any]], 
                               workflow_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Coordinate execution of multiple agent tasks.
        
        Args:
            agent_tasks: List of agent tasks to coordinate
            workflow_context: Context information for the workflow
            
        Returns:
            Dictionary containing coordination results
        """
        workflow_id = f"workflow_{asyncio.get_event_loop().time()}"
        logger.info(f"Starting workflow {workflow_id} with {len(agent_tasks)} agent tasks")
        
        # Create a semaphore to limit concurrent agents
        semaphore = asyncio.Semaphore(self.max_concurrent_agents)
        
        # Create tasks for each agent
        tasks = []
        results = {}
        
        for i, task_spec in enumerate(agent_tasks):
            agent_task = self._execute_agent_task(semaphore, workflow_id, i, task_spec, workflow_context)
            tasks.append(agent_task)
        
        # Execute all tasks with timeout
        try:
            task_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.workflow_timeout
            )
            
            # Process results
            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    results[f"agent_{i}"] = {
                        "status": "error",
                        "error": str(result),
                        "result": None
                    }
                    logger.error(f"Agent task {i} failed: {result}")
                else:
                    results[f"agent_{i}"] = {
                        "status": "success",
                        "result": result,
                        "error": None
                    }
            
            logger.info(f"Workflow {workflow_id} completed with {len([r for r in results.values() if r['status'] == 'success'])} successful tasks")
            
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "results": results,
                "total_tasks": len(agent_tasks),
                "successful_tasks": len([r for r in results.values() if r['status'] == 'success'])
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Workflow {workflow_id} timed out after {self.workflow_timeout} seconds")
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            return {
                "workflow_id": workflow_id,
                "status": "timeout",
                "results": results,
                "total_tasks": len(agent_tasks),
                "successful_tasks": len([r for r in results.values() if r.get('status') == 'success'])
            }

    async def _execute_agent_task(self, 
                                  semaphore: asyncio.Semaphore,
                                  workflow_id: str,
                                  task_index: int,
                                  task_spec: Dict[str, Any],
                                  workflow_context: Optional[Dict[str, Any]]) -> Any:
        """
        Execute a single agent task with concurrency control.
        
        Args:
            semaphore: Semaphore to control concurrency
            workflow_id: ID of the parent workflow
            task_index: Index of this task in the workflow
            task_spec: Specification of what the agent should do
            workflow_context: Context information for the workflow
            
        Returns:
            Result of the agent task execution
        """
        async with semaphore:
            logger.info(f"Executing agent task {task_index} in workflow {workflow_id}")
            
            try:
                # Determine the approach based on task specification
                agent_type = task_spec.get("type", "tool_call")
                
                if agent_type == "tool_call":
                    # Execute using MCP-discovered tools
                    return await self._execute_tool_call(task_spec, workflow_context)
                elif agent_type == "external_agent":
                    # Execute using external agent via MCP
                    return await self._execute_external_agent_call(task_spec, workflow_context)
                else:
                    # Default to tool call approach
                    return await self._execute_tool_call(task_spec, workflow_context)
                    
            except Exception as e:
                logger.error(f"Error executing agent task {task_index}: {e}")
                raise

    async def _execute_tool_call(self, 
                                 task_spec: Dict[str, Any], 
                                 workflow_context: Optional[Dict[str, Any]]) -> Any:
        """
        Execute a tool call using MCP-discovered tools.
        
        Args:
            task_spec: Specification of the tool call
            workflow_context: Context information for the workflow
            
        Returns:
            Result of the tool call
        """
        tool_name = task_spec.get("tool_name")
        tool_parameters = task_spec.get("parameters", {})
        
        if not tool_name:
            raise ValueError("Tool name is required for tool call")
        
        # Check if tool exists in MCP registry
        all_tools_dict = self.mcp_service.get_registered_external_tools()
        all_tools = all_tools_dict.get("external_agent_tools", {})
        tool_found = False
        
        for agent_name, agent_tools in all_tools.items():
            for tool in agent_tools:
                if tool.get("name") == tool_name:
                    tool_found = True
                    break
            if tool_found:
                break
        
        if not tool_found:
            raise ValueError(f"Tool '{tool_name}' not found in MCP registry")
        
        # In a real implementation, we would call the specific tool
        # For now, we'll simulate the call
        logger.info(f"Executing tool call: {tool_name} with parameters: {tool_parameters}")
        
        # This is a simplified simulation - in a real implementation,
        # this would make actual calls to the discovered tools via MCP
        if tool_name.startswith("config."):
            # Simulate configuration service call
            return {"result": f"Simulated config service call: {tool_name}", "parameters": tool_parameters}
        elif tool_name.startswith("system."):
            # Simulate system service call
            return {"result": f"Simulated system service call: {tool_name}", "parameters": tool_parameters}
        else:
            # Generic tool execution
            return {"result": f"Simulated tool execution: {tool_name}", "parameters": tool_parameters}

    async def _execute_external_agent_call(self, 
                                           task_spec: Dict[str, Any], 
                                           workflow_context: Optional[Dict[str, Any]]) -> Any:
        """
        Execute a call to an external agent via MCP.
        
        Args:
            task_spec: Specification of the external agent call
            workflow_context: Context information for the workflow
            
        Returns:
            Result of the external agent call
        """
        agent_id = task_spec.get("agent_id")
        tool_name = task_spec.get("tool_name")
        tool_parameters = task_spec.get("parameters", {})
        
        if not agent_id or not tool_name:
            raise ValueError("Agent ID and tool name are required for external agent call")
        
        logger.info(f"Calling external agent {agent_id}, tool {tool_name} with parameters: {tool_parameters}")
        
        # Check if agent is connected
        connected_agents = self.mcp_service.get_connected_agents()
        if agent_id not in connected_agents.get("agents", []):
            raise ValueError(f"External agent '{agent_id}' is not connected")
        
        # Call the external agent tool via MCP
        result = await self.mcp_service.call_external_agent_tool(
            agent_id=agent_id,
            tool_name=tool_name,
            **tool_parameters
        )
        
        return result

    async def use_mcp_for_tool_discovery(self, 
                                         agent_filter: Optional[str] = None,
                                         tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Use MCP to discover available tools, optionally filtered by agent or tags.
        
        Args:
            agent_filter: Optional agent name to filter tools
            tags: Optional list of tags to filter tools
            
        Returns:
            Dictionary containing discovered tools
        """
        # Discover tools via MCP client
        discovered_tools = self.mcp_service.get_registered_external_tools()
        
        # Extract external agent tools from the returned structure
        external_tools = discovered_tools.get("external_agent_tools", {})
        
        # If agent filter is specified, return tools for that agent only
        if agent_filter:
            agent_tools = external_tools.get(agent_filter, [])
            # Return in the same format as before
            return {agent_filter: agent_tools}
        elif tags:
            # Filter tools by tags (assuming tools have tag information)
            filtered_tools = {}
            for agent_name, agent_tools in external_tools.items():
                filtered_agent_tools = []
                for tool in agent_tools:
                    # Assuming tools have 'tags' field for filtering
                    tool_tags = tool.get("tags", [])
                    if any(tag in tool_tags for tag in tags):
                        filtered_agent_tools.append(tool)
                if filtered_agent_tools:
                    filtered_tools[agent_name] = filtered_agent_tools
            return filtered_tools
        else:
            # Return all external agent tools
            return external_tools

    async def handle_multi_agent_workflows(self, 
                                           workflow_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle complex multi-agent workflows with dependencies and coordination.
        
        Args:
            workflow_spec: Specification of the workflow to execute
            
        Returns:
            Dictionary containing workflow execution results
        """
        # Parse workflow specification
        tasks = workflow_spec.get("tasks", [])
        dependencies = workflow_spec.get("dependencies", {})
        
        # Build execution graph based on dependencies
        execution_graph = self._build_execution_graph(tasks, dependencies)
        
        # Execute workflow based on the graph
        results = await self._execute_workflow_graph(execution_graph, workflow_spec.get("context"))
        
        return {
            "workflow_spec": workflow_spec,
            "results": results,
            "status": "completed"
        }

    def _build_execution_graph(self, tasks: List[Dict[str, Any]], 
                              dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Build execution graph based on task dependencies.
        
        Args:
            tasks: List of tasks in the workflow
            dependencies: Dependencies between tasks
            
        Returns:
            Execution graph with tasks organized by execution order
        """
        # This is a simplified implementation
        # In a real implementation, this would build a proper dependency graph
        
        # Create a mapping of task_id to task definition
        task_map = {task.get("id", f"task_{i}"): task for i, task in enumerate(tasks)}
        
        # Organize tasks by dependency levels
        execution_levels = {}
        
        # For simplicity, we'll group tasks by their dependency level
        # (number of dependencies that must be completed before execution)
        for task_id, task in task_map.items():
            deps = dependencies.get(task_id, [])
            level = len(deps)  # Simplified approach
            
            if level not in execution_levels:
                execution_levels[level] = []
            execution_levels[level].append(task)
        
        return execution_levels

    async def _execute_workflow_graph(self, 
                                     execution_graph: Dict[str, Any],
                                     context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute workflow based on the execution graph.
        
        Args:
            execution_graph: Graph defining task execution order
            context: Context information for the workflow
            
        Returns:
            Dictionary containing execution results
        """
        results = {}
        
        # Execute tasks level by level (simplified approach)
        for level in sorted(execution_graph.keys()):
            level_tasks = execution_graph[level]
            level_results = await self.coordinate_agents(level_tasks, context)
            results[f"level_{level}"] = level_results
        
        return results