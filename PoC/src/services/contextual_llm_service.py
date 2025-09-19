"""
High-level LLM service that adds domain context and agent registry information.
"""

import logging
from typing import Dict, Any, Optional, List
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContextualLLMService:
    """High-level service for interacting with LLMs with contextual information."""
    
    def __init__(self, llm_service: LLMService, agent_registry: Optional[Dict[str, Any]] = None):
        """Initialize the contextual LLM service.
        
        Args:
            llm_service (LLMService): The underlying LLM service for transport.
            agent_registry (Dict[str, Any], optional): Agent registry information.
        """
        self.llm_service = llm_service
        self.agent_registry = agent_registry

    async def generate_response(
        self, 
        prompt: str, 
        domain: Optional[str] = None, 
        agent_registry: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        include_agent_capabilities: bool = True,
        **kwargs
    ) -> str:
        """Generate a response from the LLM API with contextual information.
        
        Args:
            prompt (str): The user's prompt.
            domain (str, optional): Domain context to add to the system message.
            agent_registry (Dict[str, Any], optional): Agent registry information.
            model (str, optional): The model to use.
            temperature (float): Temperature for generation (0.0 to 1.0).
            max_tokens (int, optional): Maximum number of tokens to generate.
            include_agent_capabilities (bool): Whether to include agent capabilities in the prompt.
            **kwargs: Additional arguments to pass to the LLM API.
            
        Returns:
            str: The generated response content.
        """
        if not self.llm_service:
            # Return a mock response if no LLM service is configured
            domain_context = f" [Domain: {domain}]" if domain else ""
            return f"Mock response to: {prompt}{domain_context}"
        
        try:
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
                
            if system_content:
                messages.append({"role": "system", "content": system_content})
                
            messages.append({"role": "user", "content": prompt})
            
            # Delegate to the underlying LLM service
            return await self.llm_service.generate_response(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
                    
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            return f"Error: Unable to generate response ({str(e)})"

    def _format_agent_capabilities(self, agent_registry: Dict[str, Any]) -> str:
        """Format agent capabilities for inclusion in system prompt.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
            
        Returns:
            str: Formatted agent capabilities string.
        """
        if not agent_registry:
            return ""
            
        capabilities_str = "\n[AGENT_REGISTRY]\n"
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

    def set_agent_registry(self, agent_registry: Dict[str, Any]) -> None:
        """Set the agent registry for this service.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
        """
        self.agent_registry = agent_registry