"""
Local Agent Manager - Handles loading and management of agents from local files.
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List
from .base_agent_manager import BaseLocalAgentManager
from cogniscient.engine.agent_utils.loader import load_agent_module
from cogniscient.engine.agent_utils.agent_config_manager import AgentConfigManager


class LocalAgentManager(BaseLocalAgentManager):
    """Handles loading and managing agent instances from local files based on configuration files."""
    
    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK", system_parameters_service=None):
        """Initialize the local agent manager.
        
        Args:
            config_dir: Directory containing agent configuration files
            agents_dir: Directory where agent modules are located
            system_parameters_service: Optional reference to system parameters service
        """
        # Validate config_dir and set to default if invalid
        if config_dir and not os.path.exists(config_dir):
            print(f"Warning: Config directory '{config_dir}' does not exist. Using default: '.'")
            self.config_dir = "."
        else:
            self.config_dir = config_dir or "."

        # Validate agents_dir and set to default if invalid
        if agents_dir and not os.path.exists(agents_dir):
            print(f"Warning: Agents directory '{agents_dir}' does not exist. Using default: 'cogniscient/agentSDK'")
            self.agents_dir = "cogniscient/agentSDK"
        else:
            self.agents_dir = agents_dir or "cogniscient/agentSDK"
        
        self.system_parameters_service = system_parameters_service
        # Pass the system_parameters_service to the config manager
        self.config_manager = AgentConfigManager(
            config_dir=self.config_dir, 
            agents_dir=self.agents_dir, 
            system_parameters_service=system_parameters_service
        )
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
            # Get the current agents_dir which might be dynamically updated
            current_agents_dir = self._get_current_agents_dir()
            # Convert PascalCase to snake_case for file naming convention
            snake_case_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
            module_path = os.path.join(current_agents_dir, f"{snake_case_name}.py")
        
        # Ensure the module path exists
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Agent module not found at {module_path}")
        
        # Use the utility function from loader.py
        return load_agent_module(name, module_path)
    
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
    
    def load_all_agents(self) -> None:
        """Load all agents based on configuration files."""
        # Use the configuration manager to load all agent configs
        agent_configs = self.config_manager.load_all_agent_configs()
        
        for agent_name, config in agent_configs.items():
            # Skip system services that are now handled as services, not agents
            if agent_name in ["ConfigManager", "SystemParametersManager"]:
                continue
                
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
            
            # Skip system services that are now handled as services, not agents
            if agent_name in ["ConfigManager", "SystemParametersManager"]:
                continue
                
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
            raise ValueError(f"Agent {agent_name} not loaded")
            
        agent = self.agents[agent_name]
        if not hasattr(agent, method_name):
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
            
        method = getattr(agent, method_name)
        
        # Handle both sync and async methods
        if asyncio.iscoroutinefunction(method):
            # If we're inside an event loop, schedule the async call, otherwise run it
            try:
                _ = asyncio.get_running_loop()
                # If we're inside an event loop, we can't use asyncio.run directly
                # Instead, we need to await the method or run it in a new task
                # For this case, we'll just run the coroutine (the caller should await)
                return method(*args, **kwargs)
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                return asyncio.run(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)