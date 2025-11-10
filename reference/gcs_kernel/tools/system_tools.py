"""
System tools for the GCS Kernel.

This module implements system-level tools that provide access to kernel functionality
through the same interface as other tools.
"""

import logging
from typing import Dict, Any
from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class SetLogLevelTool:
    """
    System tool to change the current logging level.
    """
    name = "set_log_level"
    display_name = "Set Log Level"
    description = "Change the current application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "description": "The logging level to set"
            }
        },
        "required": ["level"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the set log level tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        level = parameters.get("level", "").upper()
        
        if not level:
            error_msg = "Missing required parameter: level"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        # Validate the log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level not in valid_levels:
            error_msg = f"Invalid log level: {level}. Valid levels are: {', '.join(valid_levels)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            # Convert the log level string to the corresponding logging constant
            numeric_level = getattr(logging, level, None)
            if not isinstance(numeric_level, int):
                error_msg = f"Invalid log level: {level}"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Update the log level of the root logger
            logging.getLogger().setLevel(numeric_level)
            
            # Update the log level in our config module
            from common.settings import settings, configure_logging
            settings.log_level = level
            configure_logging()  # Reconfigure logging with the new level
            
            result = f"Log level successfully changed to {level}"
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error setting log level to {level}: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class ListToolsTool:
    """
    System tool to list all available tools in the kernel.
    """
    name = "list_tools"
    display_name = "List Tools"
    description = "List all available tools in the kernel"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the list tools tool.
        
        Args:
            parameters: The parameters for tool execution (none required)
            
        Returns:
            A ToolResult containing the execution result
        """
        try:
            if not self.kernel or not self.kernel.registry:
                result = "No tools available - kernel registry not initialized"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    llm_content=result,
                    return_display=result
                )
            
            tools = self.kernel.registry.get_all_tools()
            if not tools:
                result = "No tools are currently registered in the system"
            else:
                tool_list = []
                for name, tool in tools.items():
                    description = getattr(tool, 'description', 'No description')
                    tool_list.append(f"  - {name}: {description}")
                
                result = "Available tools:\n" + "\n".join(tool_list)
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error listing tools: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class GetToolInfoTool:
    """
    System tool to get information about a specific tool.
    """
    name = "get_tool_info"
    display_name = "Get Tool Info"
    description = "Get detailed information about a specific tool"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "The name of the tool to get information for"
            }
        },
        "required": ["tool_name"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.
        
        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the get tool info tool.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        tool_name = parameters.get("tool_name")
        
        if not tool_name:
            error_msg = "Missing required parameter: tool_name"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )
        
        try:
            if not self.kernel or not self.kernel.registry:
                error_msg = "Kernel registry not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            tool = await self.kernel.registry.get_tool(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            # Get tool information
            name = getattr(tool, 'name', tool_name)
            description = getattr(tool, 'description', 'No description')
            display_name = getattr(tool, 'display_name', name)
            schema = getattr(tool, 'parameters', {})
            
            result = f"Tool Information for '{tool_name}':\n"
            result += f"  Name: {name}\n"
            result += f"  Display Name: {display_name}\n"
            result += f"  Description: {description}\n"
            result += f"  Parameters Schema: {schema}"
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error getting tool info for '{tool_name}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class SetConfigTool:
    """
    System tool to change any configuration parameter at runtime.
    """
    name = "set_config"
    display_name = "Set Configuration"
    description = "Change any configuration parameter at runtime (e.g., log_level, max_tokens, max_context_length)"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "The name of the configuration parameter to change"
            },
            "param_value": {
                "type": ["string", "integer", "number"],  # Support different value types
                "description": "The new value for the configuration parameter"
            }
        },
        "required": ["param_name", "param_value"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the set config tool.

        Args:
            parameters: The parameters for tool execution

        Returns:
            A ToolResult containing the execution result
        """
        from common.settings import settings
        import logging
        
        try:
            param_name = parameters.get("param_name")
            param_value = parameters.get("param_value")

            if not param_name:
                error_msg = "Missing required parameter: param_name"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            if param_value is None:
                error_msg = "Missing required parameter: param_value"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Handle specific parameters that need special processing or validation
            if param_name == "log_level":
                # Validate log level
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                level_upper = str(param_value).upper()
                if level_upper not in valid_levels:
                    error_msg = f"Invalid log level: {level_upper}. Valid levels are: {', '.join(valid_levels)}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
                
                # Set the new log level
                numeric_level = getattr(logging, level_upper, None)
                if not isinstance(numeric_level, int):
                    error_msg = f"Invalid log level: {level_upper}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
                
                # Update the log level of the root logger
                logging.getLogger().setLevel(numeric_level)
                
                # Update the log level in our config module
                settings.log_level = level_upper
                from common.settings import configure_logging
                configure_logging()  # Reconfigure logging with the new level
                
                result = f"Log level successfully changed to {level_upper}"
            
            elif param_name == "max_tokens":
                # Validate max_tokens
                try:
                    new_max_tokens = int(param_value)
                    if not (1 <= new_max_tokens <= 4096):
                        error_msg = f"max_tokens must be between 1 and 4096, got {new_max_tokens}"
                        return ToolResult(
                            tool_name=self.name,
                            success=False,
                            error=error_msg,
                            llm_content=error_msg,
                            return_display=error_msg
                        )
                    
                    # Update the settings value (this is now the single source of truth)
                    old_max_tokens = settings.llm_max_tokens
                    settings.llm_max_tokens = new_max_tokens
                    
                    result = f"max_tokens changed from {old_max_tokens} to {new_max_tokens}"
                except (ValueError, TypeError):
                    error_msg = f"max_tokens must be an integer, got {param_value}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
                    
            elif param_name == "max_context_length":
                # Validate max_context_length
                try:
                    new_max_context_length = int(param_value)
                    if not (1024 <= new_max_context_length <= 128000):
                        error_msg = f"max_context_length must be between 1024 and 128000, got {new_max_context_length}"
                        return ToolResult(
                            tool_name=self.name,
                            success=False,
                            error=error_msg,
                            llm_content=error_msg,
                            return_display=error_msg
                        )
                    
                    # Update the settings value (this is now the single source of truth)
                    old_max_context_length = settings.llm_max_context_length
                    settings.llm_max_context_length = new_max_context_length
                    
                    result = f"max_context_length changed from {old_max_context_length} to {new_max_context_length}"
                except (ValueError, TypeError):
                    error_msg = f"max_context_length must be an integer, got {param_value}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
            
            elif hasattr(settings, param_name):
                # For other parameters that exist in the settings, update them directly
                # Get the type of the current value to validate the new value is compatible
                current_value = getattr(settings, param_name)
                current_type = type(current_value)
                
                # Convert the param_value to the appropriate type
                try:
                    if current_type == int:
                        converted_value = int(param_value)
                    elif current_type == float:
                        converted_value = float(param_value)
                    elif current_type == bool:
                        # Handle boolean values properly
                        if isinstance(param_value, str):
                            converted_value = param_value.lower() in ['true', '1', 'yes', 'on']
                        else:
                            converted_value = bool(param_value)
                    elif current_type == str:
                        converted_value = str(param_value)
                    else:
                        converted_value = param_value  # Use as-is for other types
                        
                    # Update the settings value
                    setattr(settings, param_name, converted_value)
                    
                    result = f"Configuration parameter '{param_name}' changed from {current_value} to {converted_value}"
                except (ValueError, TypeError) as e:
                    error_msg = f"Cannot convert value '{param_value}' to the required type {current_type.__name__}: {str(e)}"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
            else:
                # For parameters that don't exist in settings, we could potentially add them
                # However, for safety reasons we'll only allow parameters that exist in settings
                # This prevents arbitrary attribute creation on the settings object
                error_msg = f"Configuration parameter '{param_name}' does not exist in the system settings"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error setting configuration: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class GetConfigTool:
    """
    System tool to get current configuration parameters.
    """
    name = "get_config"
    display_name = "Get Configuration"
    description = "Get current values of configuration parameters (e.g., log_level, max_tokens, max_context_length)"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "The name of the configuration parameter to retrieve (optional, returns all if not specified)"
            }
        },
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the get config tool.

        Args:
            parameters: The parameters for tool execution

        Returns:
            A ToolResult containing the execution result
        """
        from common.settings import settings
        
        try:
            param_name = parameters.get("param_name")
            
            if param_name:
                if hasattr(settings, param_name):
                    # For all settings, return their value
                    param_value = getattr(settings, param_name)
                    result = f"{param_name} = {param_value}"
                else:
                    error_msg = f"Configuration parameter '{param_name}' does not exist"
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        error=error_msg,
                        llm_content=error_msg,
                        return_display=error_msg
                    )
            else:
                # Return all parameters from the settings object
                result_lines = ["Current configuration:"]
                
                # Get only the actual model fields to avoid accessing computed fields directly
                # Add all settings parameters using model_fields for Pydantic compatibility
                if hasattr(settings.__class__, 'model_fields'):
                    # Pydantic v2 approach
                    for field_name in settings.__class__.model_fields:
                        field_value = getattr(settings, field_name)
                        result_lines.append(f"  {field_name} = {field_value}")
                else:
                    # Fallback for other cases
                    for attr_name in dir(settings):
                        # Skip private/magic attributes and functions
                        if not attr_name.startswith('_') and not callable(getattr(settings, attr_name)):
                            # Skip special Pydantic attributes
                            if not attr_name.startswith('model_'):
                                attr_value = getattr(settings, attr_name)
                                result_lines.append(f"  {attr_name} = {attr_value}")
                
                result = "\n".join(result_lines)
            
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error getting configuration: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


async def register_system_tools(kernel) -> bool:
    """
    Register all system tools with the kernel registry.
    This should be called after the kernel and registry are initialized.
    
    Args:
        kernel: The GCSKernel instance
        
    Returns:
        True if registration was successful, False otherwise
    """
    import time
    start_time = time.time()
    
    from gcs_kernel.registry import ToolRegistry
    
    # Check if the kernel and registry are available
    if not kernel or not hasattr(kernel, 'registry'):
        if hasattr(kernel, 'logger') and kernel.logger:
            kernel.logger.error("Kernel registry not available for system tool registration")
        return False

    registry = kernel.registry
    
    if hasattr(kernel, 'logger') and kernel.logger:
        kernel.logger.debug("Starting system tools registration...")
    
    # List of system tools to register
    system_tools = [
        ListToolsTool(kernel),
        GetToolInfoTool(kernel),
        SetConfigTool(kernel),
        GetConfigTool(kernel)
    ]
    
    # Register each system tool
    for tool in system_tools:
        if hasattr(kernel, 'logger') and kernel.logger:
            kernel.logger.debug(f"Registering system tool: {tool.name}")
        
        success = await registry.register_tool(tool)
        if not success:
            if hasattr(kernel, 'logger') and kernel.logger:
                kernel.logger.error(f"Failed to register system tool: {tool.name}")
            return False
    
    elapsed = time.time() - start_time
    if hasattr(kernel, 'logger') and kernel.logger:
        kernel.logger.info(f"Successfully registered {len(system_tools)} system tools (elapsed: {elapsed:.2f}s)")
    
    return True