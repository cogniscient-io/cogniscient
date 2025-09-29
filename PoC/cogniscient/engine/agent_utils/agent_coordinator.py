"""
Agent Coordinator - Coordinates multiple agents and handles complex multi-agent operations.
"""

from typing import Any, Dict, List
from .local_agent_manager import LocalAgentManager
from .external_agent_manager import ExternalAgentManager


class AgentCoordinator:
    """Coordinates agent operations and manages complex multi-agent scenarios."""
    
    def __init__(self, local_agent_manager: LocalAgentManager, external_agent_manager: ExternalAgentManager = None):
        """Initialize the agent coordinator.
        
        Args:
            local_agent_manager: An instance of LocalAgentManager to manage local agents
            external_agent_manager: An instance of ExternalAgentManager to manage external agents (optional)
        """
        self.local_agent_manager = local_agent_manager
        self.external_agent_manager = external_agent_manager
    
    def _get_agent_manager(self, agent_name: str):
        """Get the appropriate agent manager for the agent name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            The appropriate agent manager or None if not found
        """
        # First, try local agents
        if self.local_agent_manager.get_agent(agent_name):
            return self.local_agent_manager
        
        # If not found locally, try external agents if available
        if self.external_agent_manager and self.external_agent_manager.get_agent(agent_name):
            return self.external_agent_manager
        
        # Agent not found in either manager
        return None
    
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent, regardless of whether it's local or external.
        
        Args:
            agent_name: Name of the agent to run.
            method_name: Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        manager = self._get_agent_manager(agent_name)
        if not manager:
            raise ValueError(f"Agent {agent_name} not found in local or external managers")
        
        return manager.run_agent(agent_name, method_name, *args, **kwargs)
    
    def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complex workflow involving multiple agents.
        
        Args:
            workflow_config: Configuration specifying which agents to use and in what order
            
        Returns:
            Dictionary with workflow results
        """
        results = {}

        for step in workflow_config.get("steps", []):
            agent_name = step["agent"]
            method_name = step["method"]
            params = step.get("params", {})
            
            try:
                result = self.run_agent(agent_name, method_name, **params)
                results[f"{agent_name}.{method_name}"] = result
            except Exception as e:
                results[f"{agent_name}.{method_name}"] = {"error": str(e)}
        
        return {
            "status": "completed",
            "results": results,
            "workflow_name": workflow_config.get("name", "unnamed_workflow")
        }
    
    def run_agents_in_parallel(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple agent tasks in parallel (simulated as sequential for this PoC).
        
        Args:
            tasks: List of tasks, each with agent, method, and params
            
        Returns:
            List of results from each task
        """
        results = []
        for task in tasks:
            agent_name = task["agent"]
            method_name = task["method"]
            params = task.get("params", {})
            
            try:
                result = self.run_agent(agent_name, method_name, **params)
                results.append({
                    "agent": agent_name,
                    "method": method_name,
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "agent": agent_name,
                    "method": method_name,
                    "error": str(e),
                    "status": "error"
                })
        
        return results
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get the capabilities of all loaded agents (both local and external).
        
        Returns:
            Dictionary mapping agent names to their capabilities
        """
        capabilities = {}
        
        # Get capabilities from local agents
        for name, agent in self.local_agent_manager.get_all_agents().items():
            if hasattr(agent, 'self_describe'):
                description = agent.self_describe()
                capabilities[name] = {
                    "name": description.get("name"),
                    "version": description.get("version"),
                    "methods": description.get("methods", {}),
                    "description": description.get("description", "No description available")
                }
        
        # Get capabilities from external agents if available
        if self.external_agent_manager:
            for name, agent in self.external_agent_manager.get_all_agents().items():
                if hasattr(agent, 'self_describe'):
                    description = agent.self_describe()
                    capabilities[name] = {
                        "name": description.get("name"),
                        "version": description.get("version"),
                        "methods": description.get("methods", {}),
                        "description": description.get("description", "No description available")
                    }
        
        return capabilities