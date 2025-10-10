"""Configuration Service implementation following the ringed architecture."""

import os
import json
from typing import Dict, Any, List
from cogniscient.engine.services.service_interface import ConfigServiceInterface


class ConfigServiceImpl(ConfigServiceInterface):
    """Implementation of ConfigService following the ringed architecture."""

    def __init__(self, config_dir: str = "."):
        """Initialize the configuration service.
        
        Args:
            config_dir: Directory to look for configuration files
        """
        self.config_dir = config_dir
        self._config_cache = {}
        # Store optional reference to runtime for accessing runtime functionality
        self.gcs_runtime = None
        
    async def initialize(self) -> bool:
        """Initialize the config service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Load configurations from config_dir
        try:
            # Just validate that the directory exists and is accessible
            if not os.path.exists(self.config_dir):
                print(f"Warning: Config directory '{self.config_dir}' does not exist.")
            
            return True
        except Exception as e:
            print(f"Error initializing config service: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the config service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Clear the cache on shutdown
        self._config_cache.clear()
        return True

    def update_config_dir(self, config_dir: str) -> None:
        """Update the config directory."""
        # Validate config_dir exists before updating
        if config_dir and not os.path.exists(config_dir):
            print(f"Warning: Config directory '{config_dir}' does not exist. Keeping current directory: {self.config_dir}")
            return
        self.config_dir = config_dir

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def list_configurations(self) -> List[str]:
        """List all available system configurations.

        Returns:
            list: List of available configuration names.
        """
        try:
            configurations = self._get_available_configurations()
            return configurations
        except Exception as e:
            print(f"Error listing configurations: {e}")
            return []

    async def load_configuration(self, config_name: str) -> Dict[str, Any]:
        """Load a specific system configuration.

        Args:
            config_name (str): Name of the configuration to load.

        Returns:
            dict: Result of the configuration loading operation.
        """
        try:
            # First try the 'configs' subdirectory (existing behavior)
            config_path = os.path.join(self.config_dir, "configs", f"{config_name}.json")
            if not os.path.exists(config_path):
                # If not found in 'configs' subdirectory, try the config_dir directly
                config_path = os.path.join(self.config_dir, f"{config_name}.json")
                
            if not os.path.exists(config_path):
                return {
                    "status": "error",
                    "message": f"Configuration '{config_name}' not found at {config_path}"
                }
            
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Cache the loaded configuration
            self._config_cache[config_name] = config_data
            
            return {
                "status": "success",
                "configuration": config_data,
                "message": f"Configuration '{config_name}' loaded successfully."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load configuration '{config_name}': {str(e)}"
            }

    def get_configuration(self, config_name: str) -> Dict[str, Any]:
        """Get a specific system configuration from cache or file.

        Args:
            config_name (str): Name of the configuration to get.

        Returns:
            dict: The requested configuration.
        """
        if config_name in self._config_cache:
            return self._config_cache[config_name]
        
        # Return the configuration part of the load_configuration result
        result = self.load_configuration_sync(config_name)
        return result.get("configuration", {})

    def load_configuration_sync(self, config_name: str) -> Dict[str, Any]:
        """Synchronous version of load_configuration for internal use."""
        try:
            # First try the 'configs' subdirectory (existing behavior)
            config_path = os.path.join(self.config_dir, "configs", f"{config_name}.json")
            if not os.path.exists(config_path):
                # If not found in 'configs' subdirectory, try the config_dir directly
                config_path = os.path.join(self.config_dir, f"{config_name}.json")
                
            if not os.path.exists(config_path):
                return {
                    "status": "error",
                    "message": f"Configuration '{config_name}' not found at {config_path}"
                }
            
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Cache the loaded configuration
            self._config_cache[config_name] = config_data
            
            return {
                "status": "success",
                "configuration": config_data,
                "message": f"Configuration '{config_name}' loaded successfully."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load configuration '{config_name}': {str(e)}"
            }

    def _get_available_configurations(self) -> List[str]:
        """Get list of available configuration files.

        Returns:
            List[str]: List of available configuration names.
        """
        configs = []
        
        # Look in 'configs' subdirectory first (existing behavior)
        configs_dir = os.path.join(self.config_dir, "configs")
        if os.path.exists(configs_dir):
            for file in os.listdir(configs_dir):
                if file.endswith(".json"):
                    configs.append(file[:-5])  # Remove .json extension
        
        # Also look in the config_dir directly
        for file in os.listdir(self.config_dir):
            if file.endswith(".json") and file != "configs":  # Avoid directory name
                config_name = file[:-5]  # Remove .json extension
                if config_name not in configs:  # Avoid duplicates
                    configs.append(config_name)
                
        return configs

    def _get_config_description(self, config_name: str) -> str:
        """Get a description for a configuration from its config file.

        Args:
            config_name (str): Name of the configuration.

        Returns:
            str: Description of the configuration.
        """
        try:
            # Try to load the configuration file to get its description
            # First try the 'configs' subdirectory (existing behavior)
            config_path = os.path.join(self.config_dir, "configs", f"{config_name}.json")
            if not os.path.exists(config_path):
                # If not found in 'configs' subdirectory, try the config_dir directly
                config_path = os.path.join(self.config_dir, f"{config_name}.json")
            
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                    return config_data.get("description", f"Configuration {config_name}")
            
            # Fallback to hardcoded descriptions if we can't load the file
            descriptions = {
                "dns_only": "Configuration for DNS lookups only",
                "website_only": "Configuration for website checking only",
                "combined": "Configuration for both DNS lookups and website checking"
            }
            return descriptions.get(config_name, f"Configuration {config_name}")
        except Exception:
            # If anything goes wrong, return a generic description
            return f"Configuration {config_name}"

    def get_all_cached_configs(self) -> Dict[str, Any]:
        """Get all currently cached configurations.

        Returns:
            Dict[str, Any]: All cached configurations.
        """
        return self._config_cache.copy()

    def clear_config_cache(self) -> None:
        """Clear the configuration cache."""
        self._config_cache.clear()

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the config service.
        """
        if not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register list configurations tool
        list_configs_tool = {
            "name": "config_list_configurations",
            "description": "List all available system configurations",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "type": "function"
        }

        # Register load configuration tool
        load_config_tool = {
            "name": "config_load_configuration",
            "description": "Load a specific system configuration by name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "config_name": {"type": "string", "description": "Name of the configuration to load"}
                },
                "required": ["config_name"]
            },
            "type": "function"
        }

        # Register get configuration tool
        get_config_tool = {
            "name": "config_get_configuration",
            "description": "Get a specific system configuration from cache or file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "config_name": {"type": "string", "description": "Name of the configuration to get"}
                },
                "required": ["config_name"]
            },
            "type": "function"
        }

        # Register get all cached configs tool
        get_all_cached_configs_tool = {
            "name": "config_get_all_cached_configs",
            "description": "Get all currently cached configurations",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "type": "function"
        }

        # Register clear config cache tool
        clear_config_cache_tool = {
            "name": "config_clear_config_cache",
            "description": "Clear the configuration cache",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            list_configs_tool, 
            load_config_tool, 
            get_config_tool, 
            get_all_cached_configs_tool, 
            clear_config_cache_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            list_configs_tool, 
            load_config_tool, 
            get_config_tool, 
            get_all_cached_configs_tool, 
            clear_config_cache_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool