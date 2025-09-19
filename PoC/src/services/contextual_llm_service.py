"""
High-level LLM service that adds domain context and agent registry information.
"""

import logging
from typing import Dict, Any, Optional, List
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ContextualLLMService:
    """High-level service for interacting with LLMs with contextual information."""
    
    def __init__(self, llm_service: LLMService):
        """Initialize the contextual LLM service.
        
        Args:
            llm_service (LLMService): The underlying LLM service for transport.
        """
        self.llm_service = llm_service

    async def generate_response(
        self, 
        prompt: str, 
        domain: Optional[str] = None, 
        agent_registry: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
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

            if agent_registry:
                system_content += "[AGENT_REGISTRY]\n"
                for name, agent in agent_registry.items():
                    desc = getattr(agent, "description", "")
                    system_content += f"- {name}: {desc}\n"
                system_content += "[/AGENT_REGISTRY]"
                
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