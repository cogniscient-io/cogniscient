"""
Simplified unified agent manager - Handles MCP-compliant agents and services.
"""

import os
import re
from typing import Any, Dict
from .base_agent_manager import BaseAgentManager
from .loader import load_agent_module


class UnifiedAgentManager(BaseAgentManager):
    """
    Simplified unified manager for MCP-compliant agents and services.
    """
    
    def __init__(self, agents_dir: str = "custom/agents", runtime_ref=None):
        """
        Initialize the unified agent manager.
        
        Args:
            agents_dir: Directory where agent modules are located
            runtime_ref: Reference to the runtime
        """
        self.agents_dir = agents_dir
        self.runtime_ref = runtime_ref
        self.agents: Dict[str, Any] = {}  # Maps agent names to agent instances

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
            raise ValueError(f"Agent {agent_name} not found")
        
        if not hasattr(agent, method_name):
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
        
        method = getattr(agent, method_name)
        return method(*args, **kwargs)

    def load_agent(self, agent_name: str, config: Dict[str, Any] = None) -> bool:
        """
        Load an agent by name.
        
        Args:
            agent_name: Name of the agent to load
            config: Configuration for the agent (optional)
            
        Returns:
            True if loading was successful, False otherwise
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
        
        # Store the agent instance
        self.agents[agent_name] = agent_instance
        return True

    def unload_agent(self, agent_name: str) -> bool:
        """Unload an agent by name."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            return True
        return False