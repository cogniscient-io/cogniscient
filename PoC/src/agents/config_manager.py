"""Configuration Manager Agent for handling configuration loading and management."""

from agents.base import Agent


class ConfigManager(Agent):
    """Agent for managing system configurations."""

    def __init__(self, config=None):
        """Initialize the configuration manager agent.
        
        Args:
            config (dict, optional): Configuration for the agent.
        """
        self.config = config or self.self_describe()
        self.ucs_runtime = None

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration and methods.
        """
        return {
            "name": "ConfigManager",
            "version": "1.0",
            "enabled": True,
            "methods": {
                "list_configurations": {
                    "description": "List all available system configurations",
                    "parameters": {}
                },
                "load_configuration": {
                    "description": "Load a specific system configuration",
                    "parameters": {
                        "config_name": {
                            "type": "string",
                            "description": "Name of the configuration to load",
                            "required": True
                        }
                    }
                },
                "list_loaded_agents": {
                    "description": "List all currently loaded agents",
                    "parameters": {}
                }
            }
        }

    def set_runtime(self, runtime):
        """Set the UCS runtime reference.
        
        Args:
            runtime: The UCS runtime instance.
        """
        self.ucs_runtime = runtime

    def list_configurations(self) -> dict:
        """List all available system configurations.
        
        Returns:
            dict: Result with list of available configurations.
        """
        try:
            if self.ucs_runtime is None:
                return {
                    "status": "error",
                    "message": "UCS runtime not available"
                }
                
            configurations = self.ucs_runtime.list_available_configurations()
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

    def load_configuration(self, config_name: str) -> dict:
        """Load a specific system configuration.
        
        Args:
            config_name (str): Name of the configuration to load.
            
        Returns:
            dict: Result of the configuration loading operation.
        """
        try:
            if self.ucs_runtime is None:
                return {
                    "status": "error",
                    "message": "UCS runtime not available"
                }
                
            self.ucs_runtime.load_configuration(config_name)
            agents_list = list(self.ucs_runtime.agents.keys())
            return {
                "status": "success",
                "loaded_agents": agents_list,
                "message": f"Configuration '{config_name}' loaded successfully. Available agents: {', '.join(agents_list)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load configuration '{config_name}': {str(e)}"
            }

    def list_loaded_agents(self) -> dict:
        """List all currently loaded agents.
        
        Returns:
            dict: Result with list of loaded agents.
        """
        try:
            if self.ucs_runtime is None:
                return {
                    "status": "error",
                    "message": "UCS runtime not available"
                }
                
            agents = list(self.ucs_runtime.agents.keys())
            agent_details = []
            for agent_name, agent_instance in self.ucs_runtime.agents.items():
                if hasattr(agent_instance, 'self_describe'):
                    agent_info = agent_instance.self_describe()
                    agent_details.append({
                        "name": agent_name,
                        "description": agent_info.get("description", "No description available")
                    })
                else:
                    agent_details.append({
                        "name": agent_name,
                        "description": "No description available"
                    })
            
            if agents:
                return {
                    "status": "success",
                    "agents": agent_details,
                    "message": f"Currently loaded agents: {', '.join(agents)}"
                }
            else:
                return {
                    "status": "success",
                    "agents": [],
                    "message": "No agents currently loaded."
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list loaded agents: {str(e)}"
            }

    def _get_config_description(self, config_name: str) -> str:
        """Get a description for a configuration.
        
        Args:
            config_name (str): Name of the configuration.
            
        Returns:
            str: Description of the configuration.
        """
        descriptions = {
            "dns_only": "Configuration for DNS lookups only",
            "website_only": "Configuration for website checking only",
            "combined": "Configuration for both DNS lookups and website checking"
        }
        return descriptions.get(config_name, "No description available")