"""
High-level LLM service that adds domain context and agent registry information.
"""

import logging
from typing import Dict, Any, Optional
from cogniscient.llm.llm_service import LLMService  # This is the new main LLM service (formerly ProviderManager)

logger = logging.getLogger(__name__)


class ContextualLLMService:
    def __init__(self, provider_manager: 'LLMService' = None, agent_registry: Optional[Dict[str, Any]] = None, system_services: Optional[Dict[str, Any]] = None):
        """Initialize the contextual LLM service.
        
        Args:
            provider_manager (LLMService, optional): The LLM service for handling LLM calls (formerly ProviderManager).
            agent_registry (Dict[str, Any], optional): Agent registry information.
            system_services (Dict[str, Any], optional): System services information.
        """
        self.provider_manager = provider_manager
        self.agent_registry = agent_registry
        self.system_services = system_services or {}

    async def generate_response(
        self, 
        prompt: str, 
        domain: Optional[str] = None, 
        agent_registry: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        include_agent_capabilities: bool = True,
        return_token_counts: bool = False,  # New parameter to return token counts
        **kwargs
    ) -> str | Dict[str, Any]:
        """Generate a response from the LLM API with contextual information.
        
        Args:
            prompt (str): The user's prompt.
            domain (str, optional): Domain context to add to the system message.
            agent_registry (Dict[str, Any], optional): Agent registry information.
            model (str, optional): The model to use.
            temperature (float): Temperature for generation (0.0 to 1.0).
            max_tokens (int, optional): Maximum number of tokens to generate.
            include_agent_capabilities (bool): Whether to include agent capabilities in the prompt.
            return_token_counts (bool): Whether to return token count information.
            **kwargs: Additional arguments to pass to the LLM API.
            
        Returns:
            Union[str, Dict[str, Any]]: The generated response content or a dict with response and token counts.
        """
        if not self.provider_manager:
            # Return a mock response if no provider manager is configured
            domain_context = f" [Domain: {domain}]" if domain else ""
            response = f"Mock response to: {prompt}{domain_context}"
            
            # Return mock response with token counts if requested
            if return_token_counts:
                # For mock response, we'll count tokens using LiteLLM
                import litellm
                mock_tokens = litellm.token_counter(model=model or "gpt-3.5-turbo", text=response)
                return {
                    "response": response,
                    "token_counts": {
                        "input_tokens": 0,  # No input tokens for a mock response
                        "output_tokens": mock_tokens,
                        "total_tokens": mock_tokens
                    }
                }
            
            return response
        
        try:
            # The provider manager should always be available - this is now a requirement
            if not self.provider_manager:
                raise ValueError("ProviderManager not available - this is required for LLM operations")
            
            # Create messages with domain context if available
            messages = []
            system_content = ""
            
            if domain:
                system_content += (f"You are an expert in the {domain} domain. Please explain the error "
                                   f"with information specific to this domain and provide options to resolve it.")

            # Use provided agent_registry or fall back to instance agent_registry
            registry_to_use = agent_registry or self.agent_registry
            
            # Include agent capabilities if requested and available
            if include_agent_capabilities and registry_to_use:
                agent_capabilities = self._format_agent_capabilities(registry_to_use)
                if agent_capabilities:
                    system_content += agent_capabilities
                    
            # Include system service capabilities (always available)
            system_service_capabilities = self._format_system_service_capabilities()
            if system_service_capabilities:
                system_content += system_service_capabilities
                
            if system_content:
                messages.append({"role": "system", "content": system_content})
                
            messages.append({"role": "user", "content": prompt})
            
            # Use the provider manager to generate response
            result = await self.provider_manager.generate_response(
                messages=messages,
                model=model,  # Pass the provided model directly (will use provider defaults if None)
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Handle the result based on whether it contains token counts
            if isinstance(result, dict) and "token_counts" in result and "response" in result:
                # The provider already returned token counts, so use them
                if return_token_counts:
                    return result  # Return as-is with token counts
                else:
                    # Caller doesn't want return_token_counts format, just return response
                    return result["response"]
            else:
                # The provider returned a string or a non-token-count-aware result
                if return_token_counts:
                    # Return in token count format with zeros for token counts
                    return {
                        "response": result,
                        "token_counts": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0
                        }
                    }
                else:
                    # Return as-is
                    return result
                    
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            error_response = f"Error: Unable to generate response ({str(e)})"
            
            # Return error response with token counts if requested
            if return_token_counts:
                import litellm
                # Use a default model for token counting in case of error
                default_model = model or "gpt-3.5-turbo"
                error_tokens = litellm.token_counter(model=default_model, text=error_response)
                return {
                    "response": error_response,
                    "token_counts": {
                        "input_tokens": 0,  # No input tokens for an error response
                        "output_tokens": error_tokens,
                        "total_tokens": error_tokens
                    }
                }
            
            return error_response

    def _format_agent_capabilities(self, agent_registry: Dict[str, Any]) -> str:
        """Format agent capabilities for inclusion in system prompt.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
            
        Returns:
            str: Formatted agent capabilities string.
        """
        if not agent_registry:
            return ""
            
        capabilities_str = "\\n[AGENT_REGISTRY]\n"
        for name, agent in agent_registry.items():
            # Try to get agent description
            desc = getattr(agent, "description", f"Agent {name}")
            
            # Try to get agent capabilities/methods if available
            capabilities_str += f"- {name}: {desc}\n"
            
            # If agent has a self_describe method, use it for more detailed info
            if hasattr(agent, "self_describe"):
                try:
                    agent_info = agent.self_describe()
                    methods = agent_info.get("methods", {})
                    if methods:
                        capabilities_str += "  Available methods:\n"
                        for method_name, method_info in methods.items():
                            method_desc = method_info.get("description", "")
                            capabilities_str += f"  - {method_name}: {method_desc}\n"
                            parameters = method_info.get("parameters", {})
                            if parameters:
                                capabilities_str += "    Parameters:\n"
                                for param_name, param_info in parameters.items():
                                    param_type = param_info.get("type", "any")
                                    param_desc = param_info.get("description", "")
                                    required = " (required)" if param_info.get("required", False) else ""
                                    capabilities_str += f"    - {param_name}: {param_type} - {param_desc}{required}\n"
                except Exception:
                    # If self_describe fails, continue with basic info
                    pass
                    
        capabilities_str += "[/AGENT_REGISTRY]\n"
        return capabilities_str

    def set_agent_registry(self, agent_registry: Dict[str, Any], system_services: Optional[Dict[str, Any]] = None) -> None:
        """Set the agent registry for this service, with optional system services.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
            system_services (Dict[str, Any], optional): System services information.
        """
        self.agent_registry = agent_registry
        if system_services:
            self.system_services = system_services
        else:
            # Initialize with default system services if not provided
            self.system_services = {}

    def _format_system_service_capabilities(self) -> str:
        """Format system service capabilities for inclusion in system prompt.
        
        Returns:
            str: Formatted system service capabilities string.
        """
        # Define system service capabilities as a static structure for now
        default_system_services = {
            "ConfigManager": {
                "name": "ConfigService",
                "version": "1.0.0",
                "methods": {
                    "list_configurations": {
                        "description": "List all available system configurations",
                        "parameters": {}
                    },
                    "load_configuration": {
                        "description": "Load a specific system configuration by name",
                        "parameters": {
                            "config_name": {
                                "type": "string", 
                                "description": "Name of the configuration to load", 
                                "required": True
                            }
                        }
                    },
                    "get_configuration": {
                        "description": "Get a specific system configuration from cache or file",
                        "parameters": {
                            "config_name": {
                                "type": "string", 
                                "description": "Name of the configuration to get", 
                                "required": True
                            }
                        }
                    },
                    "get_all_cached_configs": {
                        "description": "Get all currently cached configurations",
                        "parameters": {}
                    },
                    "clear_config_cache": {
                        "description": "Clear the configuration cache",
                        "parameters": {}
                    }
                },
                "description": "Service for managing system configurations"
            },
            "SystemParametersManager": {
                "name": "SystemParametersService", 
                "version": "1.0.0",
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
                },
                "description": "Service for managing system parameters dynamically"
            }
        }
        
        # Include any additional system services passed during initialization
        all_system_services = {**default_system_services, **self.system_services}
        capabilities_str = "\\n[SYSTEM_SERVICES]\\n"
        for name, service_info in all_system_services.items():
            capabilities_str += f"- {name}: {service_info.get('description', f'System service {name}')}\\n"
            
            methods = service_info.get("methods", {})
            if methods:
                capabilities_str += "  Available methods:\\n"
                for method_name, method_info in methods.items():
                    method_desc = method_info.get("description", "")
                    capabilities_str += f"  - {method_name}: {method_desc}\\n"
                    parameters = method_info.get("parameters", {})
                    if parameters:
                        capabilities_str += "    Parameters:\\n"
                        for param_name, param_info in parameters.items():
                            param_type = param_info.get("type", "any")
                            param_desc = param_info.get("description", "")
                            required = " (required)" if param_info.get("required", False) else ""
                            capabilities_str += f"    - {param_name}: {param_type} - {param_desc}{required}\\n"
                    
        capabilities_str += "[/SYSTEM_SERVICES]\\n"
        return capabilities_str