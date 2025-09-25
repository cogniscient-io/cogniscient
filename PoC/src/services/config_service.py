"""Configuration Service for handling configuration loading and management."""

import os
import json
from typing import Dict, Any, List
from src.config.settings import settings


class ConfigService:
    """Singleton service for managing system configurations."""

    _instance = None

    def __new__(cls):
        """Create or return the singleton instance of the ConfigService."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the configuration service."""
        if self._initialized:
            return
        
        self._initialized = True
        self.config_dir = settings.config_dir if hasattr(settings, 'config_dir') else "."
        self._config_cache = {}
        # Store optional reference to runtime for accessing runtime functionality
        self.ucs_runtime = None

    def set_runtime(self, runtime):
        """Set the UCS runtime reference.
        
        Args:
            runtime: The UCS runtime instance.
        """
        self.ucs_runtime = runtime

    def list_configurations(self) -> Dict[str, Any]:
        """List all available system configurations.

        Returns:
            dict: Result with list of available configurations.
        """
        try:
            configurations = self._get_available_configurations()
            config_list = [{"name": config, "description": self._get_config_description(config)} 
                          for config in configurations]
            return {
                "status": "success",
                "configurations": config_list,
                "message": f"Available configurations: {', '.join(configurations)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list configurations: {str(e)}"
            }

    def load_configuration(self, config_name: str) -> Dict[str, Any]:
        """Load a specific system configuration.

        Args:
            config_name (str): Name of the configuration to load.

        Returns:
            dict: Result of the configuration loading operation.
        """
        try:
            config_path = os.path.join(self.config_dir, "configs", f"{config_name}.json")
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
        
        return self.load_configuration(config_name).get("configuration", {})

    def _get_available_configurations(self) -> List[str]:
        """Get list of available configuration files.

        Returns:
            List[str]: List of available configuration names.
        """
        configs_dir = os.path.join(self.config_dir, "configs")
        if not os.path.exists(configs_dir):
            return []
            
        config_files = []
        for file in os.listdir(configs_dir):
            if file.endswith(".json"):
                config_files.append(file[:-5])  # Remove .json extension
                
        return config_files

    def _get_config_description(self, config_name: str) -> str:
        """Get a description for a configuration from its config file.

        Args:
            config_name (str): Name of the configuration.

        Returns:
            str: Description of the configuration.
        """
        try:
            # Try to load the configuration file to get its description
            config_path = os.path.join(self.config_dir, "configs", f"{config_name}.json")
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