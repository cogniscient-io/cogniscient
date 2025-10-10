"""
Simplified MCP-compliant local agent manager.
This manager handles local agents that register their tools directly to the MCP tool registry.
"""

import asyncio
import os
import re
from typing import Any, Dict, List
from .base_agent_manager import BaseAgentManager
from .loader import load_agent_module


class LocalAgentManager(BaseAgentManager):
    """Handles loading and managing MCP-compliant local agents."""
    
    def __init__(self, agents_dir: str = "custom/agents", runtime_ref=None):
        """
        Initialize the local agent manager.
        
        Args:
            agents_dir: Directory where agent modules are located
            runtime_ref: Reference to the runtime for tool registration
        """
        self.agents_dir = agents_dir
        self.runtime_ref = runtime_ref
        self.agents: Dict[str, Any] = {}  # Maps agent names to agent instances
    
    def load_agent(self, agent_name: str, config: Dict[str, Any] = None) -> Any:
        """
        Load a single agent by name.
        
        Args:
            agent_name: Name of the agent to load
            config: Configuration for the agent (optional)
            
        Returns:
            Loaded agent instance
        """
        # Convert PascalCase to snake_case for file naming convention
        snake_case_name = re.sub('([a-z0-9])([A-Z])', r'\\1_\\2', agent_name).lower()
        module_path = os.path.join(self.agents_dir, f"{snake_case_name}.py")
        
        # Ensure the module path exists
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Agent module not found at {module_path}")
        
        # Use the utility function from loader.py
        module = load_agent_module(agent_name, module_path)

        # Get the agent class
        agent_class = getattr(module, agent_name)
        
        # Initialize the agent with the configuration
        agent_instance = agent_class(config or {})
        
        # If the agent has a method to set the runtime reference, use it
        if hasattr(agent_instance, "set_runtime") and self.runtime_ref:
            agent_instance.set_runtime(self.runtime_ref)
        
        # If the agent has MCP-compliant tool registration, call it
        if hasattr(agent_instance, 'register_mcp_tools'):
            agent_instance.register_mcp_tools()
        
        # Store the agent instance
        self.agents[agent_name] = agent_instance
        return agent_instance
    
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name."""
        return self.agents.get(name)
    
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents."""
        return self.agents.copy()
    
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent."""
        agent = self.get_agent(agent_name)
        if agent is None:
            raise ValueError(f"Agent {agent_name} not loaded")
        
        if not hasattr(agent, method_name):
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
        
        method = getattr(agent, method_name)
        
        # Handle both sync and async methods
        if asyncio.iscoroutinefunction(method):
            try:
                # Check if we're inside an event loop
                _ = asyncio.get_running_loop()
                # If we're inside a loop, return the coroutine to be awaited by caller
                return method(*args, **kwargs)
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)
    
    def load_all_agents(self, agent_names: List[str], config: Dict[str, Any] = None) -> None:
        """Load all specified agents."""
        for agent_name in agent_names:
            try:
                self.load_agent(agent_name, config)
            except Exception as e:
                print(f"Failed to load agent {agent_name}: {e}")
    
    def unload_agent(self, agent_name: str) -> bool:
        """Unload a specific agent."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            return True
        return False
    
    def unload_all_agents(self) -> None:
        """Unload all currently loaded agents."""
        self.agents.clear()