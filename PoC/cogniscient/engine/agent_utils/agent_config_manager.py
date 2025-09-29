"""
Agent Configuration Manager - Centralized configuration management for agents.
This module consolidates configuration loading, validation, and management to prevent duplication
between code and configuration files.
"""

import json
import os
from typing import Dict, Any, List, Optional
from cogniscient.engine.agent_utils.validator import validate_agent_config, load_schema
from cogniscient.engine.agent_utils.loader import load_agent_module


class AgentConfigManager:
    """Manages agent configurations from JSON files to prevent duplication with code definitions."""
    
    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK", system_parameters_service=None):
        """Initialize the configuration manager.
        
        Args:
            config_dir: Directory to load agent configurations from
            agents_dir: Directory where agent modules are located
            system_parameters_service: Optional reference to system parameters service
        """
        self.config_dir = config_dir
        self.agents_dir = agents_dir
        self.system_parameters_service = system_parameters_service
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.schema = load_schema()
        
    def load_agent_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Load an agent configuration from a JSON file.
        
        Args:
            config_name: Name of the configuration to load (without .json extension)
            
        Returns:
            The loaded configuration or None if not found/invalid
        """
        config_file = os.path.join(self.config_dir, f"config_{config_name}.json")
        
        if not os.path.exists(config_file):
            print(f"Configuration file not found: {config_file}")
            return None
            
        with open(config_file, "r") as f:
            config = json.load(f)
        
        # Validate the configuration against the schema
        if validate_agent_config(config, self.schema):
            self.configs[config_name] = config
            return config
        else:
            print(f"Configuration {config_name} does not match the schema")
            return None
    
    def load_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load all available agent configuration files.
        
        Returns:
            Dictionary mapping config names to their configurations
        """
        config_files = []
        
        # Scan for config files in the config directory
        for file in os.listdir(self.config_dir):
            if file.startswith("config_") and file.endswith(".json"):
                config_files.append(file)
        
        configs = {}
        for config_file in config_files:
            config_name = config_file[7:-5]  # Remove "config_" prefix and ".json" suffix
            config = self.load_agent_config(config_name)
            if config:
                configs[config_name] = config
                
        return configs
    
    def get_merged_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the merged configuration for an agent (combining defaults with config file).
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Merged configuration or None if config not found
        """
        # Try to load the configuration file for this agent
        config = self.load_agent_config(agent_name)
        if not config:
            return None
            
        # Load the agent module to get its self_describe defaults
        try:
            # Convert PascalCase to snake_case for file naming convention
            import re
            snake_case_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', agent_name).lower()
            agent_module_path = os.path.join(self.get_agents_dir(), f"{snake_case_name}.py")
            
            agent_module = load_agent_module(agent_name, agent_module_path)
            
            # Get the agent class
            agent_class = getattr(agent_module, agent_name)
            agent_instance = agent_class()  # Initialize with no config to get defaults
            
            # Get the default configuration from self_describe
            if hasattr(agent_instance, 'self_describe'):
                default_config = agent_instance.self_describe()
                
                # Merge the config file values with the defaults
                merged_config = self._merge_configs(default_config, config)
                return merged_config
        except Exception as e:
            print(f"Error getting merged config for {agent_name}: {e}")
            
        return config
    
    def get_agents_dir(self) -> str:
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

    def _merge_configs(self, default_config: Dict[str, Any], file_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration from file with default values from code.
        
        Args:
            default_config: Default configuration from self_describe
            file_config: Configuration from JSON file
            
        Returns:
            Merged configuration with file values taking precedence
        """
        merged = default_config.copy()
        
        for key, value in file_config.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                # If both are dictionaries, merge them recursively
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # Otherwise, use the value from the file config
                merged[key] = value
                
        return merged
    
    def validate_all_configs(self) -> List[str]:
        """Validate all loaded configurations against the schema.
        
        Returns:
            List of configuration names that failed validation
        """
        invalid_configs = []
        
        for name, config in self.configs.items():
            if not validate_agent_config(config, self.schema):
                invalid_configs.append(name)
                
        return invalid_configs