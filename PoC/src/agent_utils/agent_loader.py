"""
Agent Loader - Handles the loading and initialization of agents from configuration files.
"""

import asyncio
import importlib.util
import json
import os
import re
from typing import Any, Dict, List
from .loader import load_agent_module
from src.agent_utils.agent_config_manager import AgentConfigManager
from src.agent_utils.external_agent_registry import ExternalAgentRegistry


class AgentLoader:
    """Handles loading and managing agent instances based on configuration files."""
    
    def __init__(self, config_dir: str = ".", agents_dir: str = "src/agents"):
        """Initialize the agent loader.
        
        Args:
            config_dir: Directory containing agent configuration files
            agents_dir: Directory where agent modules are located
        """
        self.config_dir = config_dir
        self.agents_dir = agents_dir
        self.config_manager = AgentConfigManager(config_dir=config_dir, agents_dir=agents_dir)
        self.external_agent_registry = ExternalAgentRegistry()
        self.agents: Dict[str, Any] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
    
    def load_agent_from_config(self, config: Dict[str, Any]) -> Any:
        """Load an agent module based on its configuration.
        
        Args:
            config (dict): The agent configuration.
            
        Returns:
            module: The loaded agent module.
        """
        if not config.get("enabled", True):
            return None
            
        name = config["name"]
        # Try to get the module path from the configuration first, then fall back to convention
        module_path = config.get("module_path")
        
        if module_path is None:
            # Convert PascalCase to snake_case for file naming convention
            snake_case_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
            module_path = os.path.join(self.agents_dir, f"{snake_case_name}.py")
        
        # Ensure the module path exists
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Agent module not found at {module_path}")
        
        spec = importlib.util.spec_from_file_location(name, module_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {name}")
        
        module = importlib.util.module_from_spec(spec)
        if spec.loader is not None:
            spec.loader.exec_module(module)
        return module
    
    def initialize_agent(self, config: Dict[str, Any], runtime_ref=None) -> Any:
        """Initialize an agent instance from its loaded module.
        
        Args:
            config (dict): The agent configuration.
            runtime_ref: Reference to the runtime (optional).
            
        Returns:
            Agent: An initialized agent instance.
        """
        module = self.load_agent_from_config(config)
        if module is None:
            return None
            
        # For this PoC, we'll assume the agent class name matches the module name
        class_name = config["name"]
        agent_class = getattr(module, class_name)
        
        # Initialize the agent with the configuration
        agent_instance = agent_class(config)
        
        # If the agent has a method to set the runtime reference, use it
        if hasattr(agent_instance, "set_runtime") and runtime_ref:
            agent_instance.set_runtime(runtime_ref)
            
        return agent_instance
    
    def set_runtime_ref(self, runtime_ref):
        """Set a reference to the runtime for all agents that need it.
        
        Args:
            runtime_ref: Reference to the runtime
        """
        self.runtime_ref = runtime_ref
        # Set the runtime reference for already loaded agents
        for agent in self.agents.values():
            if hasattr(agent, "set_runtime") and runtime_ref:
                agent.set_runtime(runtime_ref)
    
    def load_all_agents(self) -> None:
        """Load all agents based on configuration files."""
        # Use the configuration manager to load all agent configs
        agent_configs = self.config_manager.load_all_agent_configs()
        
        for agent_name, config in agent_configs.items():
            # Only load agents that are enabled
            if config.get("enabled", True):
                try:
                    # Get the merged configuration (defaults from code + values from config file)
                    merged_config = self.config_manager.get_merged_config(agent_name)
                    if merged_config is None:
                        # Fallback to the raw config if merged config fails
                        merged_config = config
                    
                    # Store the agent config
                    self.agent_configs[agent_name] = merged_config
                    agent = self.initialize_agent(merged_config)
                    if agent is not None:
                        self.agents[agent_name] = agent
                        print(f"Loaded agent: {agent_name}")
                except Exception as e:
                    print(f"Failed to load agent {agent_name}: {e}")
    
    def load_specific_agents(self, agent_specs: List[Dict[str, str]]) -> None:
        """Load specific agents based on agent specifications.
        
        Args:
            agent_specs: List of agent specifications, each with name and config_file
        """
        for agent_spec in agent_specs:
            agent_name = agent_spec["name"]
            config_file = agent_spec.get("config_file", f"config_{agent_name}.json")
            
            try:
                # Check if config_file is a relative path or just a filename
                if not os.path.isabs(config_file):
                    config_path = os.path.join(self.config_dir, config_file)
                else:
                    config_path = config_file
                
                # Load the configuration from the specified file
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                else:
                    print(f"Configuration file not found: {config_path}")
                    continue
                
                # Get the merged configuration (defaults from code + values from config file)
                merged_config = self.config_manager.get_merged_config(agent_name)
                # If merged config was created, use it, otherwise use the loaded config
                if merged_config is None:
                    merged_config = config
                
                if merged_config and merged_config.get("enabled", True):
                    self.agent_configs[agent_name] = merged_config
                    agent = self.initialize_agent(merged_config)
                    if agent is not None:
                        self.agents[agent_name] = agent
                        print(f"Loaded agent: {agent_name}")
            except Exception as e:
                print(f"Failed to load agent {agent_name}: {e}")

    def load_specific_agents_by_name(self, agent_names: List[str]) -> None:
        """Load specific agents by name, using the default config_{name}.json files.
        
        Args:
            agent_names: List of agent names to load
        """
        agent_specs = [{"name": name, "config_file": f"config_{name}.json"} for name in agent_names]
        self.load_specific_agents(agent_specs)
    
    def unload_all_agents(self) -> None:
        """Unload all currently loaded agents."""
        for agent_name, agent in self.agents.items():
            if hasattr(agent, "shutdown"):
                agent.shutdown()
        
        # Clear agent collections
        self.agents.clear()
        self.agent_configs.clear()
        print("All agents unloaded.")
    
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent instance or None if not found
        """
        return self.agents.get(name)
    
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents.
        
        Returns:
            Dictionary mapping agent names to agent instances
        """
        return self.agents.copy()
    
    def register_external_agent(self, agent_config: Dict[str, Any]) -> bool:
        """Register an external agent.
        
        Args:
            agent_config: Configuration for the external agent
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        # Register with the external agent registry
        registration_success = self.external_agent_registry.register_agent(agent_config)
        
        if registration_success:
            # Add to our local agents dict as well to maintain a unified interface
            agent_name = agent_config["name"]
            external_agent = self.external_agent_registry.get_agent(agent_name)
            self.agents[agent_name] = external_agent
            self.agent_configs[agent_name] = agent_config
            
        return registration_success
    
    def deregister_external_agent(self, agent_name: str) -> bool:
        """Deregister an external agent.
        
        Args:
            agent_name: Name of the external agent to deregister
            
        Returns:
            bool: True if deregistration was successful, False otherwise
        """
        # Remove from the external agent registry
        deregistration_success = self.external_agent_registry.deregister_agent(agent_name)
        
        if deregistration_success:
            # Remove from our local agents dict as well
            if agent_name in self.agents:
                del self.agents[agent_name]
            if agent_name in self.agent_configs:
                del self.agent_configs[agent_name]
        
        return deregistration_success
    
    def get_external_agent(self, agent_name: str):
        """Get an external agent by name.
        
        Args:
            agent_name: Name of the external agent to retrieve
            
        Returns:
            The external agent or None if not found
        """
        return self.external_agent_registry.get_agent(agent_name)
    
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent.
        
        Args:
            agent_name (str): Name of the agent to run.
            method_name (str): Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        if agent_name not in self.agents:
            # Check if it's an external agent that might have been registered
            external_agent = self.external_agent_registry.get_agent(agent_name)
            if external_agent:
                self.agents[agent_name] = external_agent
            else:
                raise ValueError(f"Agent {agent_name} not loaded")
            
        agent = self.agents[agent_name]
        if not hasattr(agent, method_name):
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
            
        method = getattr(agent, method_name)
        
        # Handle both sync and async methods
        if asyncio.iscoroutinefunction(method):
            # If we're inside an event loop, schedule the async call, otherwise run it
            try:
                loop = asyncio.get_running_loop()
                # If we're inside an event loop, we can't use asyncio.run directly
                # Instead, we need to await the method or run it in a new task
                # For this case, we'll just run the coroutine (the caller should await)
                return method(*args, **kwargs)
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)