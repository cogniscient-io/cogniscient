"""
Main LLM Service for switching between different LLM providers.
"""
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter
from cogniscient.auth.token_manager import TokenManager


class LLMService:
    """Main service for switching between different LLM providers."""
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the LLM Service.
        
        Args:
            token_manager: Token manager that may be used for authenticated providers (optional)
        """
        self.current_provider = "litellm"  # Default provider
        # Initialize LiteLLM adapter with token manager for potential authenticated requests
        self.litellm_adapter = LiteLLMAdapter(token_manager=token_manager)
        self.providers = {
            "litellm": self.litellm_adapter,  # Current implementation
        }
        
        # Store token manager for potential use in authenticated requests
        self.token_manager = token_manager

    def add_provider(self, name: str, provider: Any):
        """
        Add a new provider to the service.
        
        Args:
            name: Name of the provider
            provider: Provider instance
        """
        self.providers[name] = provider

    def set_provider(self, provider_name: str) -> bool:
        """
        Set the active provider.
        
        Args:
            provider_name: Name of the provider to activate
            
        Returns:
            True if provider exists and was set, False otherwise
        """
        if provider_name not in self.providers and provider_name != "qwen":
            print(f"Provider '{provider_name}' not available. Available providers: {list(self.providers.keys())}")
            # Add "qwen" to the list if token manager is available
            available_providers = list(self.providers.keys())
            if self.token_manager:
                available_providers.append("qwen")
            print(f"Available providers: {available_providers}")
            return False

        # Check if provider requires authentication
        if provider_name == "qwen":
            if not self.token_manager:
                print("Qwen provider not available - token manager required")
                return False
            # Verify credentials are valid before switching
            # In a real implementation, we'd check this properly

        self.current_provider = provider_name
        print(f"Provider set to: {provider_name}")
        return True

    def get_provider(self):
        """Get the currently active provider."""
        # For Qwen, use the same LiteLLM adapter but with authentication
        if self.current_provider == "qwen":
            return self.providers.get("litellm")
        else:
            return self.providers.get(self.current_provider)

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,  # Changed to None so we can set provider-specific defaults
        stream: bool = False,  # Add stream parameter
        **kwargs
    ) -> Optional[str] | AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a response using the current provider.
        
        Args:
            messages: List of messages in the format {"role": "...", "content": "..."}
            model: Model to use for generation (uses provider-specific defaults if None)
            **kwargs: Additional parameters to pass to the provider
            
        Returns:
            Generated response text, or None if the request failed
        """
        # Set provider-specific default model if none provided
        if model is None:
            from cogniscient.engine.config.settings import settings
            # Use settings model based on current provider
            if self.current_provider == "qwen":
                model = settings.qwen_model  # Default model for Qwen/DashScope API from settings
            else:
                model = settings.llm_model  # Default model for other providers from settings
        
        provider = self.get_provider()
        if not provider:
            print(f"Provider '{self.current_provider}' not found")
            return None

        # Use the LiteLLM adapter with provider-specific logic
        try:
            return await provider.generate_response(messages, model, stream=stream, provider=self.current_provider, **kwargs)
        except Exception as e:
            print(f"Error with {self.current_provider} provider: {e}")
            return None

    async def check_provider_credentials(self, provider_name: str) -> bool:
        """
        Check if the specified provider has valid credentials.
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if provider_name == "qwen":
            if self.token_manager:
                # Check if we can get a valid access token
                token = await self.token_manager.get_valid_access_token()
                return token is not None
            return False
        elif provider_name == "litellm":
            # LiteLLM typically doesn't require special credentials for local models
            return True
        else:
            return False

    async def get_available_providers(self) -> List[str]:
        """
        Get a list of available providers.
        
        Returns:
            List of provider names
        """
        return list(self.providers.keys())

    async def close(self):
        """Close any resources held by providers."""
        # Close LiteLLM adapter to properly clean up async clients
        litellm_adapter = self.providers.get("litellm")
        if litellm_adapter and hasattr(litellm_adapter, 'close'):
            await litellm_adapter.close()