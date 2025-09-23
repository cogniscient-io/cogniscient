"""
Agent Coordinator - Coordinates multiple agents and handles complex multi-agent operations.
"""

from typing import Any, Dict, List
from src.agent_utils.agent_loader import AgentLoader


class AgentCoordinator:
    """Coordinates agent operations and manages complex multi-agent scenarios."""
    
    def __init__(self, agent_loader: AgentLoader):
        """Initialize the agent coordinator.
        
        Args:
            agent_loader: An instance of AgentLoader to manage agents
        """
        self.agent_loader = agent_loader
    
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
                result = self.agent_loader.run_agent(agent_name, method_name, **params)
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
                result = self.agent_loader.run_agent(agent_name, method_name, **params)
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
        """Get the capabilities of all loaded agents.
        
        Returns:
            Dictionary mapping agent names to their capabilities
        """
        capabilities = {}
        for name, agent in self.agent_loader.get_all_agents().items():
            if hasattr(agent, 'self_describe'):
                description = agent.self_describe()
                capabilities[name] = {
                    "name": description.get("name"),
                    "version": description.get("version"),
                    "methods": description.get("methods", {}),
                    "description": description.get("description", "No description available")
                }
        
        return capabilities