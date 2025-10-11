"""
Simplified LLM Service that focuses only on interfacing with LLM providers,
without complex control logic that belongs in the system services.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Simplified LLM service that focuses on basic provider interface without complex control logic."""
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the simplified LLM service.
        
        Args:
            token_manager: Token manager that may be used for authenticated providers (optional)
        """
        self.current_provider = "litellm"  # Default provider
        self.providers = {}
        self.token_manager = token_manager
        
        # Initialize the actual provider implementation
        # In a real implementation this would load different providers dynamically
        try:
            from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter
            self.litellm_adapter = LiteLLMAdapter(token_manager=token_manager)
            self.providers["litellm"] = self.litellm_adapter
        except ImportError:
            logger.error("LiteLLM adapter not available")
            self.litellm_adapter = None
    
    def set_provider(self, provider_name: str) -> bool:
        """
        Set the active provider.
        
        Args:
            provider_name: Name of the provider to activate
            
        Returns:
            True if provider exists and was set, False otherwise
        """
        if provider_name in self.providers:
            self.current_provider = provider_name
            logger.info(f"Provider set to: {provider_name}")
            return True
        elif provider_name == "qwen" and self.token_manager:
            # Qwen uses the same LiteLLM adapter with different auth
            self.current_provider = provider_name
            logger.info(f"Provider set to: {provider_name}")
            return True
        else:
            logger.error(f"Provider '{provider_name}' not available")
            return False

    def get_provider(self):
        """Get the currently active provider."""
        if self.current_provider == "qwen":
            return self.providers.get("litellm")  # Use litellm adapter for Qwen
        else:
            return self.providers.get(self.current_provider)

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Optional[str] | AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a response from the current provider with minimal error handling.
        
        Args:
            messages: List of messages in the format {"role": "...", "content": "..."}
            model: Model to use for generation
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the provider
            
        Returns:
            Generated response text, or None if the request failed
        """
        provider = self.get_provider()
        if not provider:
            logger.error(f"Provider '{self.current_provider}' not found")
            return None

        try:
            # Set model if not provided
            if model is None:
                model = settings.llm_model if self.current_provider != "qwen" else settings.qwen_model

            # Determine if this is Qwen provider
            is_qwen = self.current_provider == "qwen"
            
            # Call provider's generate_response method
            result = await provider.generate_response(
                messages=messages,
                model=model,
                stream=stream,
                provider="qwen" if is_qwen else "litellm",
                **kwargs
            )
            
            return result
        except Exception as e:
            logger.error(f"Error calling LLM provider '{self.current_provider}': {e}")
            return None

    async def check_provider_credentials(self, provider_name: str) -> bool:
        """
        Check if the specified provider has valid credentials.
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if provider_name == "qwen" and self.token_manager:
            try:
                token = await self.token_manager.get_valid_access_token()
                return token is not None
            except Exception:
                return False
        elif provider_name == "litellm":
            # For local models, credentials aren't typically required
            return True
        else:
            return False

    def add_provider(self, provider_name: str, provider_instance):
        """
        Add a new provider to the service.

        Args:
            provider_name: Name of the provider
            provider_instance: Instance of the provider
        """
        self.providers[provider_name] = provider_instance

    async def get_available_providers(self) -> List[str]:
        """
        Get a list of available providers.
        
        Returns:
            List of provider names
        """
        providers = list(self.providers.keys())
        if self.token_manager:
            providers.append("qwen")
        return providers

    async def close(self):
        """Close any resources held by providers."""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()