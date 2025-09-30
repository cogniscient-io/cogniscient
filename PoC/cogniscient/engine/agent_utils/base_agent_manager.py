"""
Base agent manager interfaces for the dynamic control system.

Defines common interfaces for agent management with separate concerns
for local file-based agents and external agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from enum import Enum

class ComponentType(Enum):
    """Enum to distinguish between different types of components"""
    LOCAL_AGENT = "local_agent"
    EXTERNAL_AGENT = "external_agent"
    INTERNAL_SERVICE = "internal_service"

class UnifiedComponent:
    """Represents a unified component that can be an agent or a service"""
    def __init__(self, name: str, component_type: ComponentType, config: dict, load_behavior: str = "dynamic"):
        self.name = name
        self.component_type = component_type
        self.config = config
        self.load_behavior = load_behavior  # "dynamic" or "static"
        self.instance = None
        self.is_loaded = False

class BaseAgentManager(ABC):
    """Abstract base class for all agent managers."""
    
    @abstractmethod
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent instance or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents.
        
        Returns:
            Dictionary mapping agent names to agent instances
        """
        pass
    
    @abstractmethod
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent.
        
        Args:
            agent_name: Name of the agent to run.
            method_name: Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        pass

class BaseUnifiedAgentManager(BaseAgentManager):
    """Abstract base class for the unified agent/service manager"""
    
    @abstractmethod
    def register_component(self, component: UnifiedComponent) -> bool:
        """Register a component (agent or service) in the system"""
        pass
        
    @abstractmethod
    def deregister_component(self, name: str) -> bool:
        """Deregister a component from the system"""
        pass
        
    @abstractmethod
    def load_component(self, name: str) -> bool:
        """Load a component based on its configuration"""
        pass
        
    @abstractmethod
    def unload_component(self, name: str) -> bool:
        """Unload a component from memory"""
        pass
        
    @abstractmethod
    def get_component(self, name: str) -> Any:
        """Get a specific component by name"""
        pass
        
    @abstractmethod
    def get_all_components(self) -> Dict[str, Any]:
        """Get all loaded components"""
        pass
        
    @abstractmethod
    def run_component_method(self, name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on a component"""
        pass

class BaseLocalAgentManager(BaseAgentManager):
    """Abstract base class for local file-based agent managers."""
    
    @abstractmethod
    def load_agent_from_config(self, config: Dict[str, Any]) -> Any:
        """Load an agent module based on its configuration.
        
        Args:
            config: The agent configuration.
            
        Returns:
            The loaded agent module.
        """
        pass
    
    @abstractmethod
    def initialize_agent(self, config: Dict[str, Any], runtime_ref=None) -> Any:
        """Initialize an agent instance from its loaded module.
        
        Args:
            config: The agent configuration.
            runtime_ref: Reference to the runtime (optional).
            
        Returns:
            An initialized agent instance.
        """
        pass
    
    @abstractmethod
    def set_runtime_ref(self, runtime_ref) -> None:
        """Set a reference to the runtime for all agents that need it.
        
        Args:
            runtime_ref: Reference to the runtime
        """
        pass
    
    @abstractmethod
    def load_all_agents(self) -> None:
        """Load all agents based on configuration files."""
        pass
    
    @abstractmethod
    def load_specific_agents(self, agent_specs: List[Dict[str, str]]) -> None:
        """Load specific agents based on agent specifications.
        
        Args:
            agent_specs: List of agent specifications, each with name and config_file
        """
        pass
    
    @abstractmethod
    def load_specific_agents_by_name(self, agent_names: List[str]) -> None:
        """Load specific agents by name.
        
        Args:
            agent_names: List of agent names to load
        """
        pass
    
    @abstractmethod
    def unload_all_agents(self) -> None:
        """Unload all currently loaded agents."""
        pass

class BaseExternalAgentManager(BaseAgentManager):
    """Abstract base class for external agent managers."""
    
    @abstractmethod
    def register_agent(self, agent_config: Dict[str, Any]) -> bool:
        """Register an external agent.
        
        Args:
            agent_config: Configuration for the external agent
            
        Returns:
            True if registration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def deregister_agent(self, agent_name: str) -> bool:
        """Deregister an external agent.
        
        Args:
            agent_name: Name of the external agent to deregister
            
        Returns:
            True if deregistration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_external_agent(self, agent_name: str):
        """Get an external agent by name.
        
        Args:
            agent_name: Name of the external agent to retrieve
            
        Returns:
            The external agent or None if not found
        """
        pass