"""System Parameters Service for dynamic system parameter adjustment."""

import os
from cogniscient.engine.config.settings import settings
from typing import Dict, Any
from cogniscient.engine.services.service_interface import Service


class SystemParametersService(Service):
    """Singleton service for managing system parameters dynamically."""

    _instance = None

    def __new__(cls):
        """Create or return the singleton instance of the SystemParametersService."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the system parameters service."""
        if self._initialized:
            return
        
        self._initialized = True
        # Store optional reference to runtime for updating runtime objects
        self.gcs_runtime = None

    async def initialize(self) -> bool:
        """Initialize the system parameters service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # For now, initialization is just confirming the service is ready
        return True

    async def shutdown(self) -> bool:
        """Shutdown the system parameters service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # For now, there's nothing specific to do on shutdown
        return True

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def get_system_parameters(self) -> Dict[str, Any]:
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
            
            # Add agents_dir parameter if runtime reference is available
            if self.gcs_runtime and hasattr(self.gcs_runtime, 'agents_dir'):
                parameters["agents_dir"] = self.gcs_runtime.agents_dir
                
            # Add config_dir parameter if runtime reference is available
            if self.gcs_runtime and hasattr(self.gcs_runtime, 'config_dir'):
                parameters["config_dir"] = self.gcs_runtime.config_dir
                
            # Include LLM settings in parameters
            parameters["llm_model"] = settings.llm_model
            parameters["llm_base_url"] = settings.llm_base_url
            
            # Include runtime data directory setting
            parameters["runtime_data_dir"] = settings.runtime_data_dir
            
            # Get parameters from orchestrator if available
            if self.gcs_runtime and hasattr(self.gcs_runtime, 'orchestrator'):
                orchestrator = self.gcs_runtime.orchestrator
                if hasattr(orchestrator, 'max_context_size'):
                    # Include orchestrator value to verify it matches settings
                    parameters["orchestrator_max_context_size"] = orchestrator.max_context_size
            
            # Get parameters from chat interfaces if available
            if self.gcs_runtime and hasattr(self.gcs_runtime, 'chat_interfaces'):
                chat_interfaces = self.gcs_runtime.chat_interfaces
                if chat_interfaces:
                    chat_interface = chat_interfaces[0]  # Get first chat interface
                    # Include chat interface values to verify they match settings
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

    def set_system_parameter(self, parameter_name: str, parameter_value: str) -> Dict[str, Any]:
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
            
            # Import settings here to avoid circular imports
            from cogniscient.engine.config.settings import settings
            
            # Set parameter based on name
            if parameter_name == "max_context_size":
                # Update both the global settings and runtime objects
                settings.max_context_size = converted_value
                
                if self.gcs_runtime and hasattr(self.gcs_runtime, 'orchestrator'):
                    self.gcs_runtime.orchestrator.max_context_size = converted_value
                return {
                    "status": "success",
                    "message": f"Max context size set to {converted_value}"
                }
            elif parameter_name == "max_history_length":
                # Update both the global settings and chat interfaces
                settings.max_history_length = converted_value
                
                if self.gcs_runtime and hasattr(self.gcs_runtime, 'chat_interfaces'):
                    for chat_interface in self.gcs_runtime.chat_interfaces:
                        chat_interface.max_history_length = converted_value
                        # Ensure compression threshold is valid
                        if chat_interface.compression_threshold >= converted_value:
                            chat_interface.compression_threshold = max(1, converted_value - 1)
                return {
                    "status": "success",
                    "message": f"Max history length set to {converted_value}"
                }
            elif parameter_name == "compression_threshold":
                # Update both the global settings and chat interfaces
                settings.compression_threshold = converted_value
                
                if self.gcs_runtime and hasattr(self.gcs_runtime, 'chat_interfaces'):
                    for chat_interface in self.gcs_runtime.chat_interfaces:
                        chat_interface.compression_threshold = converted_value
                        # Ensure threshold is valid relative to max history length
                        if converted_value >= chat_interface.max_history_length:
                            chat_interface.max_history_length = converted_value + 1
                return {
                    "status": "success",
                    "message": f"Compression threshold set to {converted_value}"
                }
            elif parameter_name == "llm_model":
                # Update the global settings
                settings.llm_model = converted_value
                return {
                    "status": "success",
                    "message": f"LLM model set to {converted_value}"
                }
            elif parameter_name == "llm_base_url":
                # Update the global settings
                settings.llm_base_url = converted_value
                return {
                    "status": "success",
                    "message": f"LLM base URL set to {converted_value}"
                }
            elif parameter_name == "log_level":
                # Update the global settings
                settings.log_level = converted_value
                return {
                    "status": "success",
                    "message": f"Log level set to {converted_value}"
                }
            elif parameter_name == "agents_dir":
                # Validate the agents_dir exists before updating
                if parameter_value and not os.path.exists(parameter_value):
                    return {
                        "status": "error",
                        "message": f"Agents directory '{parameter_value}' does not exist. Please provide a valid directory path."
                    }
                # Update the runtime's agents_dir
                if self.gcs_runtime:
                    self.gcs_runtime.agents_dir = parameter_value
                    # Also need to update the local agent manager's agents_dir
                    if hasattr(self.gcs_runtime, 'local_agent_manager'):
                        self.gcs_runtime.local_agent_manager.agents_dir = parameter_value
                        # Update the config manager's agents_dir as well
                        self.gcs_runtime.local_agent_manager.config_manager.agents_dir = parameter_value
                return {
                    "status": "success",
                    "message": f"Agents directory set to {parameter_value}"
                }
            elif parameter_name == "config_dir":
                # Validate the config_dir exists before updating
                if parameter_value and not os.path.exists(parameter_value):
                    return {
                        "status": "error",
                        "message": f"Config directory '{parameter_value}' does not exist. Please provide a valid directory path."
                    }
                # Update the runtime's config_dir
                if self.gcs_runtime:
                    self.gcs_runtime.config_dir = parameter_value
                    # Also need to update the config service's config_dir
                    if hasattr(self.gcs_runtime, 'config_service'):
                        self.gcs_runtime.config_service.update_config_dir(parameter_value)
                return {
                    "status": "success",
                    "message": f"Config directory set to {parameter_value}"
                }

            elif parameter_name == "runtime_data_dir":
                # Update the runtime data directory setting
                settings.runtime_data_dir = parameter_value
                return {
                    "status": "success",
                    "message": f"Runtime data directory set to {parameter_value}"
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

    def get_parameter_descriptions(self) -> Dict[str, Any]:
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
            "log_level": "Current logging level",
            "agents_dir": "Directory where agent modules are located",
            "config_dir": "Directory where configuration files are located",
            "runtime_data_dir": "Directory where runtime data files are stored"
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

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the system parameters service.
        """
        if not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register get system parameters tool
        get_params_tool = {
            "name": "system_get_parameters",
            "description": "Get current system parameter values",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "type": "function"
        }

        # Register set system parameter tool
        set_param_tool = {
            "name": "system_set_parameter",
            "description": "Set a system parameter value",
            "input_schema": {
                "type": "object",
                "properties": {
                    "parameter_name": {"type": "string", "description": "Name of the parameter to set"},
                    "parameter_value": {"type": "string", "description": "New value for the parameter"}
                },
                "required": ["parameter_name", "parameter_value"]
            },
            "type": "function"
        }

        # Register get parameter descriptions tool
        get_param_descs_tool = {
            "name": "system_get_parameter_descriptions",
            "description": "Get descriptions of all system parameters",
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
            get_params_tool, 
            set_param_tool, 
            get_param_descs_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            get_params_tool, 
            set_param_tool, 
            get_param_descs_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool