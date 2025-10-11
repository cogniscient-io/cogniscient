"""
Control & Configuration Service for Adaptive Control System that manages
parameter management and approval workflows.

This service handles configuration management, parameter validation,
and approval workflows in the new LLM architecture.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from cogniscient.engine.services.service_interface import Service, ConfigServiceInterface
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class ControlConfigService(ConfigServiceInterface):
    """
    Service that manages configuration and control parameters with approval workflows.
    """
    
    def __init__(self, config_dir: str = "."):
        """
        Initialize the control & configuration service.
        
        Args:
            config_dir: Directory to load configurations from
        """
        self.config_dir = config_dir
        self._config_cache = {}
        self._pending_approvals = {}
        self._parameter_descriptions = {}
        self.gcs_runtime = None  # Will be set by runtime
        
        # Statistics for monitoring
        self.total_config_loads = 0
        self.total_approvals = 0
        self.denied_approvals = 0
        
    async def initialize(self) -> bool:
        """
        Initialize the configuration service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Initialize parameter descriptions with defaults
            self._parameter_descriptions = {
                "llm_model": {
                    "description": "Default LLM model to use",
                    "type": "string",
                    "default": settings.llm_model
                },
                "qwen_model": {
                    "description": "Default Qwen model to use",
                    "type": "string", 
                    "default": settings.qwen_model
                },
                "max_retries": {
                    "description": "Maximum number of retry attempts for LLM calls",
                    "type": "integer",
                    "default": 3,
                    "min": 0,
                    "max": 10
                },
                "retry_delay": {
                    "description": "Delay between retry attempts in seconds",
                    "type": "float",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 10.0
                },
                "default_provider": {
                    "description": "Default LLM provider to use",
                    "type": "string",
                    "default": settings.default_provider
                },
                "conversation_max_length": {
                    "description": "Maximum conversation history length",
                    "type": "integer",
                    "default": 20,
                    "min": 1,
                    "max": 100
                }
            }
            return True
        except Exception as e:
            logger.error(f"Error initializing Control & Configuration Service: {e}")
            return False
        
    async def shutdown(self) -> bool:
        """
        Shutdown the configuration service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Clear caches and pending approvals
        self._config_cache.clear()
        self._pending_approvals.clear()
        return True

    def set_runtime(self, runtime):
        """
        Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    async def load_configuration(self, config_name: str) -> Dict[str, Any]:
        """
        Load a specific configuration.
        
        Args:
            config_name: Name of the configuration to load
            
        Returns:
            Configuration dictionary
        """
        # Check if configuration is in cache
        if config_name in self._config_cache:
            logger.debug(f"Returning cached configuration: {config_name}")
            self.total_config_loads += 1
            return self._config_cache[config_name]
        
        # In a real implementation, this would load from a file or database
        # For now, we'll simulate loading predefined configurations
        config = self._load_predefined_config(config_name)
        
        if config:
            # Cache the configuration
            self._config_cache[config_name] = config
            self.total_config_loads += 1
            logger.info(f"Loaded configuration: {config_name}")
            return config
        else:
            logger.warning(f"Configuration not found: {config_name}")
            return {}

    def _load_predefined_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a predefined configuration.
        
        Args:
            config_name: Name of the configuration to load
            
        Returns:
            Configuration dictionary or None if not found
        """
        # Predefined configurations
        predefined_configs = {
            "default": {
                "llm_model": settings.llm_model,
                "qwen_model": settings.qwen_model,
                "max_retries": 3,
                "retry_delay": 1.0,
                "default_provider": settings.default_provider,
                "conversation_max_length": 20
            },
            "development": {
                "llm_model": settings.llm_model,
                "qwen_model": settings.qwen_model,
                "max_retries": 2,
                "retry_delay": 0.5,
                "default_provider": settings.default_provider,
                "conversation_max_length": 10
            },
            "production": {
                "llm_model": settings.llm_model,
                "qwen_model": settings.qwen_model,
                "max_retries": 5,
                "retry_delay": 2.0,
                "default_provider": settings.default_provider,
                "conversation_max_length": 50
            }
        }
        
        return predefined_configs.get(config_name)

    def list_configurations(self) -> List[str]:
        """
        List all available configurations.
        
        Returns:
            List of configuration names
        """
        # In a real implementation, this would scan the config directory
        # For now, return predefined configuration names
        return ["default", "development", "production"]

    def update_config_dir(self, config_dir: str) -> None:
        """
        Update the configuration directory.
        
        Args:
            config_dir: New configuration directory path
        """
        self.config_dir = config_dir
        # Clear cache since directory changed
        self._config_cache.clear()

    async def get_parameter(self, param_name: str) -> Optional[Any]:
        """
        Get a specific parameter value.
        
        Args:
            param_name: Name of the parameter to retrieve
            
        Returns:
            Parameter value or None if not found
        """
        config = await self.load_configuration("default")
        return config.get(param_name)

    async def set_parameter(self, param_name: str, value: Any, require_approval: bool = True) -> Dict[str, Any]:
        """
        Set a parameter with optional approval workflow.
        
        Args:
            param_name: Name of the parameter to set
            value: New value for the parameter
            require_approval: Whether to require approval for this change
            
        Returns:
            Dictionary with result of the operation
        """
        # Validate the parameter
        if param_name not in self._parameter_descriptions:
            return {
                "success": False,
                "error": f"Parameter '{param_name}' is not defined",
                "requires_approval": False
            }
        
        param_info = self._parameter_descriptions[param_name]
        
        # Validate value type and constraints
        validation_result = self._validate_parameter_value(param_name, value, param_info)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "requires_approval": False
            }
        
        # If approval is required, create a pending approval
        if require_approval and self._requires_approval(param_name, value):
            approval_id = f"approval_{asyncio.get_event_loop().time()}_{param_name}"
            self._pending_approvals[approval_id] = {
                "param_name": param_name,
                "current_value": await self.get_parameter(param_name),
                "new_value": value,
                "request_time": asyncio.get_event_loop().time(),
                "requested_by": "system"  # Would come from actual user in real implementation
            }
            
            return {
                "success": False,  # Not yet successful, awaiting approval
                "approval_id": approval_id,
                "requires_approval": True,
                "message": f"Parameter change for '{param_name}' requires approval"
            }
        else:
            # Apply the change directly
            return await self._apply_parameter_change(param_name, value)

    def _validate_parameter_value(self, param_name: str, value: Any, param_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a parameter value against its definition.
        
        Args:
            param_name: Name of the parameter
            value: Value to validate
            param_info: Parameter definition information
            
        Returns:
            Dictionary with validation result
        """
        # Check type
        expected_type = param_info.get("type")
        if expected_type == "string" and not isinstance(value, str):
            return {"valid": False, "error": f"Parameter '{param_name}' must be a string"}
        elif expected_type == "integer" and not isinstance(value, int):
            return {"valid": False, "error": f"Parameter '{param_name}' must be an integer"}
        elif expected_type == "float" and not isinstance(value, (int, float)):
            return {"valid": False, "error": f"Parameter '{param_name}' must be a number"}
        
        # Check min/max constraints
        if "min" in param_info and value < param_info["min"]:
            return {"valid": False, "error": f"Parameter '{param_name}' must be >= {param_info['min']}"}
        if "max" in param_info and value > param_info["max"]:
            return {"valid": False, "error": f"Parameter '{param_name}' must be <= {param_info['max']}"}
        
        return {"valid": True, "error": None}

    def _requires_approval(self, param_name: str, value: Any) -> bool:
        """
        Determine if a parameter change requires approval.
        
        Args:
            param_name: Name of the parameter
            value: New value
            
        Returns:
            True if approval is required, False otherwise
        """
        # In a real implementation, this would have more sophisticated logic
        # For now, we'll require approval for critical parameters
        critical_params = ["default_provider", "llm_model", "max_retries"]
        return param_name in critical_params

    async def _apply_parameter_change(self, param_name: str, value: Any) -> Dict[str, Any]:
        """
        Apply a parameter change to the active configuration.
        
        Args:
            param_name: Name of the parameter to change
            value: New value for the parameter
            
        Returns:
            Dictionary with result of the operation
        """
        try:
            # Load the default configuration
            config = await self.load_configuration("default")
            
            # Update the parameter
            config[param_name] = value
            
            # Update the cache
            self._config_cache["default"] = config
            
            logger.info(f"Parameter '{param_name}' updated to '{value}'")
            
            return {
                "success": True,
                "param_name": param_name,
                "new_value": value,
                "requires_approval": False
            }
        except Exception as e:
            logger.error(f"Error applying parameter change: {e}")
            return {
                "success": False,
                "error": str(e),
                "requires_approval": False
            }

    async def approve_parameter_change(self, approval_id: str, approved: bool = True) -> Dict[str, Any]:
        """
        Approve or deny a pending parameter change.
        
        Args:
            approval_id: ID of the approval request
            approved: Whether the change is approved
            
        Returns:
            Dictionary with result of the approval operation
        """
        if approval_id not in self._pending_approvals:
            return {
                "success": False,
                "error": f"Approval ID '{approval_id}' not found"
            }
        
        approval_request = self._pending_approvals[approval_id]
        
        if approved:
            # Apply the change
            result = await self._apply_parameter_change(
                approval_request["param_name"], 
                approval_request["new_value"]
            )
            if result["success"]:
                self.total_approvals += 1
                result["message"] = f"Parameter change approved and applied for '{approval_request['param_name']}'"
            else:
                result["message"] = f"Parameter change approval failed: {result.get('error', 'Unknown error')}"
        else:
            # Deny the change
            self.denied_approvals += 1
            result = {
                "success": True,
                "param_name": approval_request["param_name"],
                "new_value": approval_request["new_value"],
                "message": f"Parameter change denied for '{approval_request['param_name']}'",
                "requires_approval": False
            }
        
        # Remove the approval request
        del self._pending_approvals[approval_id]
        
        return result

    def get_parameter_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get descriptions of all parameters.
        
        Returns:
            Dictionary mapping parameter names to their descriptions
        """
        return self._parameter_descriptions

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the configuration service.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_config_loads": self.total_config_loads,
            "total_approvals": self.total_approvals,
            "denied_approvals": self.denied_approvals,
            "pending_approvals": len(self._pending_approvals),
            "cached_configs": len(self._config_cache),
            "defined_parameters": len(self._parameter_descriptions)
        }

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the control & config service.
        """
        if not hasattr(self, 'gcs_runtime') or not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register get parameter tool
        get_parameter_tool = {
            "name": "config_get_parameter",
            "description": "Get a specific configuration parameter value",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string", "description": "Name of the parameter to retrieve"}
                },
                "required": ["param_name"]
            },
            "type": "function"
        }

        # Register set parameter tool
        set_parameter_tool = {
            "name": "config_set_parameter",
            "description": "Set a specific configuration parameter value",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string", "description": "Name of the parameter to set"},
                    "value": {"type": "string", "description": "New value for the parameter"},
                    "require_approval": {"type": "boolean", "description": "Whether to require approval for this change", "default": True}
                },
                "required": ["param_name", "value"]
            },
            "type": "function"
        }

        # Register get parameter descriptions tool
        get_descriptions_tool = {
            "name": "config_get_parameter_descriptions",
            "description": "Get descriptions of all available parameters",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            get_parameter_tool,
            set_parameter_tool,
            get_descriptions_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            get_parameter_tool,
            set_parameter_tool,
            get_descriptions_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool