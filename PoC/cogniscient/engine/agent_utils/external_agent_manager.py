"""
External Agent Manager - Handles registration and management of external agents.
"""

from typing import Any, Dict, List
from .base_agent_manager import BaseExternalAgentManager
from .external_agent_registry import ExternalAgentRegistry


class ExternalAgentManager(BaseExternalAgentManager):
    """Handles registration, management, and access to external agents."""
    
    def __init__(self, registry_file: str = None, runtime_data_dir: str = None):
        """Initialize the external agent manager.
        
        Args:
            registry_file: Path to the file where external agent configurations are stored
            runtime_data_dir: Directory where runtime data files are stored
        """
        self.external_agent_registry = ExternalAgentRegistry(registry_file, runtime_data_dir)
        self._agents: Dict[str, Any] = {}
    
    def register_agent(self, agent_config: Dict[str, Any]) -> bool:
        """Register an external agent.
        
        Args:
            agent_config: Configuration for the external agent
            
        Returns:
            True if registration was successful, False otherwise
        """
        # Register with the external agent registry
        registration_success = self.external_agent_registry.register_agent(agent_config)
        
        if registration_success:
            # Add to our local agents dict as well to maintain a unified interface
            agent_name = agent_config["name"]
            external_agent = self.external_agent_registry.get_agent(agent_name)
            self._agents[agent_name] = external_agent
            
        return registration_success
    
    def deregister_agent(self, agent_name: str) -> bool:
        """Deregister an external agent.
        
        Args:
            agent_name: Name of the external agent to deregister
            
        Returns:
            True if deregistration was successful, False otherwise
        """
        # Remove from the external agent registry
        deregistration_success = self.external_agent_registry.deregister_agent(agent_name)
        
        if deregistration_success:
            # Remove from our local agents dict as well
            if agent_name in self._agents:
                del self._agents[agent_name]
        
        return deregistration_success
    
    def get_agent(self, name: str) -> Any:
        """Get an external agent by name.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent instance or None if not found
        """
        return self._agents.get(name)
    
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all registered external agents.
        
        Returns:
            Dictionary mapping agent names to agent instances
        """
        return self._agents.copy()
    
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an external agent.
        
        Args:
            agent_name: Name of the agent to run.
            method_name: Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        if agent_name not in self._agents:
            external_agent = self.external_agent_registry.get_agent(agent_name)
            if external_agent:
                self._agents[agent_name] = external_agent
            else:
                raise ValueError(f"External agent {agent_name} not registered")
        
        agent = self._agents[agent_name]
        if not hasattr(agent, method_name):
            raise ValueError(f"External agent {agent_name} does not have method {method_name}")
            
        method = getattr(agent, method_name)
        return method(*args, **kwargs)
    
    def get_external_agent(self, agent_name: str):
        """Get an external agent by name.
        
        Args:
            agent_name: Name of the external agent to retrieve
            
        Returns:
            The external agent or None if not found
        """
        return self.external_agent_registry.get_agent(agent_name)