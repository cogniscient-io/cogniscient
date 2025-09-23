"""System Parameters Manager Agent for dynamic system parameter adjustment."""

from agents.base import Agent
from src.config.settings import settings


class SystemParametersManager(Agent):
    """Agent for managing system parameters dynamically."""

    def __init__(self, config=None):
        """Initialize the system parameters manager agent.
        
        Args:
            config (dict, optional): Configuration for the agent.
        """
        # Start with the self-describe definition as the base
        base_config = self.self_describe()
        
        # Merge with provided config, allowing config file to override defaults
        if config:
            # Update the base config with values from the config file
            for key, value in config.items():
                if isinstance(value, dict) and key in base_config and isinstance(base_config[key], dict):
                    # If both are dictionaries, merge them
                    base_config[key].update(value)
                else:
                    # Otherwise, replace the value
                    base_config[key] = value
        
        self.config = base_config
        self.ucs_runtime = None

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration and methods.
        """
        return {
            "name": "SystemParametersManager",
            "version": "1.0",
            "enabled": True,
            "description": "Agent for managing system parameters dynamically",
            "methods": {
                "get_system_parameters": {
                    "description": "Get current system parameter values",
                    "parameters": {}
                },
                "set_system_parameter": {
                    "description": "Set a system parameter value",
                    "parameters": {
                        "parameter_name": {
                            "type": "string",
                            "description": "Name of the parameter to set",
                            "required": True
                        },
                        "parameter_value": {
                            "type": "string",
                            "description": "New value for the parameter",
                            "required": True
                        }
                    }
                },
                "get_parameter_descriptions": {
                    "description": "Get descriptions of all system parameters",
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

    def get_system_parameters(self) -> dict:
        """Get current system parameter values.
        
        Returns:
            dict: Current system parameter values.
        """
        try:
            # Get parameters from settings
            parameters = {
                "max_context_size": settings.max_context_size,
                "max_history_length": settings.max_history_length,
                "compression_threshold": settings.compression_threshold,
                "llm_model": settings.llm_model,
                "llm_base_url": settings.llm_base_url,
                "log_level": settings.log_level
            }
            
            # Get parameters from orchestrator if available
            if self.ucs_runtime and hasattr(self.ucs_runtime, 'orchestrator'):
                orchestrator = self.ucs_runtime.orchestrator
                if hasattr(orchestrator, 'max_context_size'):
                    parameters["orchestrator_max_context_size"] = orchestrator.max_context_size
            
            # Get parameters from chat interfaces if available
            if self.ucs_runtime and hasattr(self.ucs_runtime, 'chat_interfaces'):
                chat_interfaces = self.ucs_runtime.chat_interfaces
                if chat_interfaces:
                    chat_interface = chat_interfaces[0]  # Get first chat interface
                    parameters["chat_max_history_length"] = chat_interface.max_history_length
                    parameters["chat_compression_threshold"] = chat_interface.compression_threshold
            
            return {
                "status": "success",
                "parameters": parameters,
                "message": "Current system parameters retrieved successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get system parameters: {str(e)}"
            }

    def set_system_parameter(self, parameter_name: str, parameter_value: str) -> dict:
        """Set a system parameter value.
        
        Args:
            parameter_name (str): Name of the parameter to set.
            parameter_value (str): New value for the parameter.
            
        Returns:
            dict: Result of the parameter setting operation.
        """
        try:
            # Convert string value to appropriate type
            converted_value = self._convert_parameter_value(parameter_name, parameter_value)
            
            # Set parameter based on name
            if parameter_name == "max_context_size":
                # Update settings (this won't persist, but we can update runtime objects)
                if self.ucs_runtime and hasattr(self.ucs_runtime, 'orchestrator'):
                    self.ucs_runtime.orchestrator.max_context_size = converted_value
                return {
                    "status": "success",
                    "message": f"Max context size set to {converted_value}"
                }
            elif parameter_name == "max_history_length":
                # Update chat interfaces
                if self.ucs_runtime and hasattr(self.ucs_runtime, 'chat_interfaces'):
                    for chat_interface in self.ucs_runtime.chat_interfaces:
                        chat_interface.max_history_length = converted_value
                        # Ensure compression threshold is valid
                        if chat_interface.compression_threshold >= converted_value:
                            chat_interface.compression_threshold = max(1, converted_value - 1)
                return {
                    "status": "success",
                    "message": f"Max history length set to {converted_value}"
                }
            elif parameter_name == "compression_threshold":
                # Update chat interfaces
                if self.ucs_runtime and hasattr(self.ucs_runtime, 'chat_interfaces'):
                    for chat_interface in self.ucs_runtime.chat_interfaces:
                        chat_interface.compression_threshold = converted_value
                        # Ensure threshold is valid relative to max history length
                        if converted_value >= chat_interface.max_history_length:
                            chat_interface.max_history_length = converted_value + 1
                return {
                    "status": "success",
                    "message": f"Compression threshold set to {converted_value}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unknown parameter: {parameter_name}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set parameter {parameter_name}: {str(e)}"
            }

    def get_parameter_descriptions(self) -> dict:
        """Get descriptions of all system parameters.
        
        Returns:
            dict: Descriptions of all system parameters.
        """
        descriptions = {
            "max_context_size": "Maximum context window size in characters for the LLM orchestrator",
            "max_history_length": "Maximum number of conversation turns to keep in chat history",
            "compression_threshold": "Compress chat history when it reaches this number of turns",
            "llm_model": "Current LLM model being used",
            "llm_base_url": "Base URL for the LLM API",
            "log_level": "Current logging level"
        }
        
        return {
            "status": "success",
            "descriptions": descriptions,
            "message": "Parameter descriptions retrieved successfully"
        }

    def _convert_parameter_value(self, parameter_name: str, parameter_value: str):
        """Convert parameter value string to appropriate type.
        
        Args:
            parameter_name (str): Name of the parameter.
            parameter_value (str): Value as string.
            
        Returns:
            Converted value.
        """
        # Define parameter types
        int_parameters = ["max_context_size", "max_history_length", "compression_threshold"]
        
        if parameter_name in int_parameters:
            return int(parameter_value)
        else:
            return parameter_value