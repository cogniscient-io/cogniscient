"""
Contextual LLM Service that focuses on contextual LLM operations
with prompt construction handled by the PromptConstructionService.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from cogniscient.llm.llm_provider_service import LLMService

logger = logging.getLogger(__name__)


class ContextualLLMService:
    """
    Contextual LLM service that focuses on high-level operations
    while delegating the prompt construction to the PromptConstructionService.
    """
    
    def __init__(self, 
                 provider_manager: LLMService,
                 prompt_construction_service=None,
                 mcp_client_service=None,
                 system_services=None):
        """
        Initialize the contextual LLM service.
        
        Args:
            provider_manager: The LLM provider manager (LLMService)
            prompt_construction_service: Service for prompt construction (optional)
            mcp_client_service: MCP client service for external agent connections (optional)
            system_services: Dictionary of system services to integrate (optional)
        """
        self.provider_manager = provider_manager
        self.prompt_construction_service = prompt_construction_service
        self.mcp_client_service = mcp_client_service
        
        # Initialize with common system services, then update with passed services
        default_system_services = {}
        if system_services:
            default_system_services.update(system_services)
        
        # Add default configuration service if not already present
        if "ConfigService" not in default_system_services:
            default_system_services["ConfigService"] = {
                "name": "ConfigService", 
                "description": "Configuration management service",
                "methods": {
                    "config.list_configurations": {
                        "description": "List all available configurations",
                        "parameters": {}
                    },
                    "config.load_configuration": {
                        "description": "Load a specific configuration",
                        "parameters": {
                            "config_name": {
                                "type": "string",
                                "description": "Name of the configuration to load",
                                "required": True
                            }
                        }
                    },
                    "config.save_configuration": {
                        "description": "Save a specific configuration",
                        "parameters": {
                            "config_name": {
                                "type": "string", 
                                "description": "Name of the configuration to save",
                                "required": True
                            },
                            "config_data": {
                                "type": "object",
                                "description": "Configuration data to save",
                                "required": True
                            }
                        }
                    },
                    "config.update_configuration": {
                        "description": "Update a specific configuration",
                        "parameters": {
                            "config_name": {
                                "type": "string",
                                "description": "Name of the configuration to update", 
                                "required": True
                            },
                            "config_data": {
                                "type": "object", 
                                "description": "Configuration data to update with",
                                "required": True
                            }
                        }
                    }
                }
            }
        
        self.system_services = default_system_services

    async def generate_response(
        self,
        prompt: str,  # Changed parameter name to match original interface
        domain: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str | Dict[str, Any]:
        """
        Generate a response with contextual information handled by the prompt construction service.
        This method maintains compatibility with the original ContextualLLMService interface.
        
        Args:
            prompt: The user's prompt/input
            domain: Domain context to add
            model: Model to use for generation
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Generated response content or formatted result with token counts
        """
        if not self.provider_manager:
            # Return a mock response if no provider manager is configured
            return f"Mock response to: {prompt} [Domain: {domain}]" if domain else f"Mock response to: {prompt}"
        
        # If we have a prompt construction service, use it to build the messages
        if self.prompt_construction_service:
            # For general prompts (not specifically user input), we should still use prompt construction
            # but we need to treat the prompt as the user input for message formatting
            messages = self.prompt_construction_service.construct_contextual_messages(
                user_input=prompt,  # Use prompt as user input
                domain=domain,
                include_agent_capabilities=True,
                include_system_services=True
            )
            
            # Use the provider manager to generate response with the constructed messages
            result = await self.provider_manager.generate_response(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return result
        else:
            # Fallback: just send the prompt directly as user message
            result = await self.provider_manager.generate_response(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return result

    async def generate_contextual_response(
        self,
        user_input: str,
        domain: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str | Dict[str, Any]:
        """
        Alias for generate_response method for compatibility.
        Generate a response with contextual information handled by the prompt construction service.
        
        Args:
            user_input: The user's input
            domain: Domain context to add
            model: Model to use for generation
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Generated response content or formatted result with token counts
        """
        # Call the main method with the same parameters
        return await self.generate_response(
            prompt=user_input,
            domain=domain,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    def set_agent_registry(self, agent_registry, system_services=None):
        """
        Set the agent registry and optionally system services.
        
        Args:
            agent_registry: Dictionary of agents
            system_services: Dictionary of system services
        """
        self.agent_registry = agent_registry
        if system_services is not None:
            self.system_services = system_services

    def _format_system_service_capabilities(self) -> str:
        """
        Format system service capabilities for inclusion in prompts.
        
        Returns:
            String representation of system service capabilities
        """
        if not self.system_services:
            return "No system services available."
        
        capabilities_str = "Available system services:\n"
        for service_name, service_info in self.system_services.items():
            capabilities_str += f"- {service_name}: "
            if isinstance(service_info, dict) and "methods" in service_info:
                # Add special handling for MCP service to include "Model Context Protocol" in output
                if "connect_to_external_agent" in service_info["methods"]:
                    capabilities_str += "Model Context Protocol service. "
                capabilities_str += f"Methods: {', '.join(service_info['methods'])}\n"
            else:
                capabilities_str += f"{service_info}\n"
        
        return capabilities_str

    async def close(self):
        """Close any resources held by the simplified contextual LLM service."""
        # If the provider manager has a close method, call it
        if self.provider_manager and hasattr(self.provider_manager, 'close'):
            await self.provider_manager.close()
        # Close the prompt construction service if it has a close method
        if self.prompt_construction_service and hasattr(self.prompt_construction_service, 'close'):
            self.prompt_construction_service.close()