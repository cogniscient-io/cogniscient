"""
Unified Agent Manager - Handles loading and management of both local agents and internal services.
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List
from .base_agent_manager import BaseUnifiedAgentManager, UnifiedComponent, ComponentType
from cogniscient.engine.agent_utils.loader import load_agent_module
from cogniscient.engine.agent_utils.agent_config_manager import AgentConfigManager
from cogniscient.engine.services.config_service import ConfigService
from cogniscient.engine.services.system_parameters_service import SystemParametersService


class UnifiedAgentManager(BaseUnifiedAgentManager):
    """Handles loading and managing both agent and service components with unified interfaces."""

    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK", system_parameters_service=None):
        """Initialize the unified agent manager.
        
        Args:
            config_dir: Directory containing agent configuration files
            agents_dir: Directory where agent modules are located
            system_parameters_service: Optional reference to system parameters service
        """
        self.config_dir = config_dir
        self.agents_dir = agents_dir
        self.system_parameters_service = system_parameters_service
        # Pass the system_parameters_service to the config manager
        self.config_manager = AgentConfigManager(
            config_dir=config_dir,
            agents_dir=agents_dir,
            system_parameters_service=system_parameters_service
        )
        self.components: Dict[str, UnifiedComponent] = {}
        self.runtime_ref = None

    def register_component(self, component: UnifiedComponent) -> bool:
        """Register a component (agent or service) in the system.
        
        Args:
            component: The component to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            self.components[component.name] = component
            # If the component has static loading behavior, load it immediately
            if component.load_behavior == "static":
                self.load_component(component.name)
            return True
        except Exception as e:
            print(f"Failed to register component {component.name}: {e}")
            return False

    def deregister_component(self, name: str) -> bool:
        """Deregister a component from the system.
        
        Args:
            name: Name of the component to deregister
            
        Returns:
            True if deregistration was successful, False otherwise
        """
        if name not in self.components:
            return False

        # If the component is loaded, unload it first
        if self.components[name].is_loaded:
            self.unload_component(name)

        # Remove the component
        del self.components[name]
        return True

    def load_component(self, name: str) -> bool:
        """Load a component based on its configuration.
        
        Args:
            name: Name of the component to load
            
        Returns:
            True if loading was successful, False otherwise
        """
        if name not in self.components:
            raise ValueError(f"Component {name} not registered")

        component = self.components[name]

        # Load based on component type
        if component.component_type == ComponentType.LOCAL_AGENT:
            # Load local agent using existing pattern
            component.instance = self._load_local_agent(component.config)
        elif component.component_type == ComponentType.EXTERNAL_AGENT:
            # Load external agent using existing pattern
            component.instance = self._load_external_agent(component.config)
        elif component.component_type == ComponentType.INTERNAL_SERVICE:
            # Load internal service using existing pattern
            component.instance = self._load_internal_service(component.config)

        component.is_loaded = True
        return True

    def unload_component(self, name: str) -> bool:
        """Unload a component from memory.
        
        Args:
            name: Name of the component to unload
            
        Returns:
            True if unloading was successful, False otherwise
        """
        if name not in self.components:
            raise ValueError(f"Component {name} not registered")

        component = self.components[name]
        if not component.is_loaded:
            return True  # Already unloaded

        # Call shutdown if available
        if hasattr(component.instance, "shutdown"):
            component.instance.shutdown()

        # Clear the instance and mark as unloaded
        component.instance = None
        component.is_loaded = False
        return True

    def get_component(self, name: str) -> Any:
        """Get a specific component by name.
        
        Args:
            name: Name of the component
            
        Returns:
            The component instance or None if not found
        """
        if name not in self.components:
            # Try to fetch from registry if not in components
            external_agent = self._get_external_agent_from_registry(name)
            if external_agent:
                # Add to components if found in registry
                component = UnifiedComponent(
                    name=name,
                    component_type=ComponentType.EXTERNAL_AGENT,
                    config={},
                    load_behavior="dynamic"
                )
                component.instance = external_agent
                component.is_loaded = True
                self.components[name] = component
                return component
            return None

        component = self.components[name]
        if not component.is_loaded:
            # Load the component if it's not loaded
            self.load_component(name)
        return component

    def get_all_components(self) -> Dict[str, Any]:
        """Get all loaded components.
        
        Returns:
            Dictionary mapping component names to component instances
        """
        # Ensure all dynamically loadable components are loaded before returning
        for name, component in self.components.items():
            if not component.is_loaded and component.load_behavior == "dynamic":
                self.load_component(name)
        return {name: comp for name, comp in self.components.items()}

    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents.
        
        Returns:
            Dictionary mapping agent names to agent instances
        """
        all_components = self.get_all_components()
        return {name: comp.instance for name, comp in all_components.items() if comp.instance is not None}

    def run_component_method(self, name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on a component.
        
        Args:
            name: Name of the component to run.
            method_name: Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        if name not in self.components:
            # Try to get the component from the registry
            component = self.get_component(name)
            if component is None:
                raise ValueError(f"Component {name} not registered")
        else:
            component = self.components[name]

        if not component.is_loaded:
            # Load the component if it's not loaded
            self.load_component(name)

        if not hasattr(component.instance, method_name):
            raise ValueError(f"Component {name} does not have method {method_name}")

        method = getattr(component.instance, method_name)

        # Handle both sync and async methods
        if asyncio.iscoroutinefunction(method):
            # If we're inside an event loop, we need to handle the async call appropriately
            try:
                loop = asyncio.get_running_loop()
                # If we're inside an event loop, return the coroutine for the caller to await
                return method(*args, **kwargs)
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)

    def _load_local_agent(self, config: Dict[str, Any]) -> Any:
        """Load a local agent based on its configuration."""
        if not config.get("enabled", True):
            return None

        name = config["name"]
        # Try to get the module path from the configuration first, then fall back to convention
        module_path = config.get("module_path")

        if module_path is None:
            # Get the current agents_dir which might be dynamically updated
            current_agents_dir = self._get_current_agents_dir()
            # Convert PascalCase to snake_case for file naming convention
            snake_case_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
            module_path = os.path.join(current_agents_dir, f"{snake_case_name}.py")

        # Ensure the module path exists
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Agent module not found at {module_path}")

        # Use the utility function from loader.py
        module = load_agent_module(name, module_path)

        # For this PoC, we'll assume the agent class name matches the module name
        class_name = config["name"]
        agent_class = getattr(module, class_name)

        # Initialize the agent with the configuration
        agent_instance = agent_class(config)

        # If the agent has a method to set the runtime reference, use it
        if hasattr(agent_instance, "set_runtime") and self.runtime_ref:
            agent_instance.set_runtime(self.runtime_ref)

        return agent_instance

    def _load_external_agent(self, config: Dict[str, Any]) -> Any:
        """Load an external agent based on its configuration."""
        # For now, this is a placeholder. In a real implementation, this would
        # communicate with an external service to register and access the agent.
        # Since we don't have the actual external agent adapter in the PRP, 
        # we'll just return a placeholder.
        from .external_agent_manager import ExternalAgentManager
        from .external_agent_registry import ExternalAgentRegistry

        # Create an external agent registry and register the agent
        registry = ExternalAgentRegistry()
        registry.register_agent(config)

        # Create an external agent manager and get the agent
        external_manager = ExternalAgentManager()
        return external_manager.get_external_agent(config["name"])

    def _load_internal_service(self, config: Dict[str, Any]) -> Any:
        """Load an internal service based on its configuration."""
        service_type = config.get("service_type", "unknown")
        if service_type == "config":
            return ConfigService()
        elif service_type == "system_parameters":
            return SystemParametersService()
        # Add more service types as needed
        else:
            raise ValueError(f"Unknown service type: {service_type}")

    def _get_current_agents_dir(self) -> str:
        """Get the current agents directory, potentially from system parameters service.
        
        Returns:
            Current agents directory path
        """
        if self.system_parameters_service:
            try:
                # Try to get the agents_dir from system parameters
                params_result = self.system_parameters_service.get_system_parameters()
                if params_result["status"] == "success" and "agents_dir" in params_result["parameters"]:
                    return params_result["parameters"]["agents_dir"]
            except Exception as e:
                # If there's an error getting the parameter, fall back to the default
                print(f"Error getting agents_dir from system parameters: {e}")

        return self.agents_dir

    # Implementation of the BaseAgentManager abstract methods
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent instance or None if not found
        """
        component = self.get_component(name)
        if component:
            return component.instance
        return None

    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents.
        
        Returns:
            Dictionary mapping agent names to agent instances
        """
        all_components = self.get_all_components()
        return {name: comp.instance for name, comp in all_components.items() if comp.instance is not None}

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
        return self.run_component_method(agent_name, method_name, *args, **kwargs)

    def set_runtime_ref(self, runtime_ref) -> None:
        """Set a reference to the runtime for all components that need it.
        
        Args:
            runtime_ref: Reference to the runtime
        """
        self.runtime_ref = runtime_ref
        # Set the runtime reference for all loaded components
        for component in self.components.values():
            if component.is_loaded and hasattr(component.instance, "set_runtime") and runtime_ref:
                component.instance.set_runtime(runtime_ref)