"""
Main LLM Service for switching between different LLM providers.
"""
import asyncio
from typing import List, Dict, Any, Optional
from cogniscient.llm.providers.litellm_adapter import LiteLLMAdapter
from .qwen_client import QwenClient
from cogniscient.auth.token_manager import TokenManager


class LLMService:
    """Main service for switching between different LLM providers."""
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the LLM Service.
        
        Args:
            token_manager: Token manager for Qwen provider (optional)
        """
        self.current_provider = "litellm"  # Default provider
        self.providers = {
            "litellm": LiteLLMAdapter(),  # Current implementation
        }
        
        # Set up Qwen provider if token_manager is provided
        if token_manager:
            self.qwen_client = QwenClient(token_manager)
            self.providers["qwen"] = self.qwen_client
        else:
            self.qwen_client = None

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
        if provider_name not in self.providers:
            print(f"Provider '{provider_name}' not available. Available providers: {list(self.providers.keys())}")
            return False

        # Check if provider requires authentication
        if provider_name == "qwen":
            if self.qwen_client:
                # Verify credentials are valid before switching
                # In a real implementation, we'd check this properly
                pass
            else:
                print("Qwen provider not initialized - token manager required")
                return False

        self.current_provider = provider_name
        print(f"Provider set to: {provider_name}")
        return True

    def get_provider(self):
        """Get the currently active provider."""
        return self.providers.get(self.current_provider)

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = None,  # Changed to None so we can set provider-specific defaults
        **kwargs
    ) -> Optional[str]:
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
            if self.current_provider == "qwen":
                model = settings.qwen_model  # Default model for Qwen API from settings
            else:
                model = settings.llm_model  # Default model for litellm/Ollama from settings
        
        provider = self.get_provider()
        if not provider:
            print(f"Provider '{self.current_provider}' not found")
            return None

        # Generate response using the current provider
        # The interface might be different for different providers
        if self.current_provider == "litellm":
            # For LiteLLM service, use its generate_response method
            try:
                return await provider.generate_response(messages, model, **kwargs)
            except Exception as e:
                print(f"Error with LiteLLM provider: {e}")
                return None
        elif self.current_provider == "qwen":
            # For Qwen client, use its generate_response method
            try:
                # Adjust model name for Qwen API if needed
                qwen_model = model.replace("ollama_chat/", "") if "ollama_chat/" in model else model
                return await self.qwen_client.generate_response(messages, qwen_model, **kwargs)
            except Exception as e:
                print(f"Error with Qwen provider: {e}")
                return None
        else:
            # Handle other providers if added in the future
            print(f"Unknown provider: {self.current_provider}")
            return None

    async def check_provider_credentials(self, provider_name: str) -> bool:
        """
        Check if the specified provider has valid credentials.
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if provider_name == "qwen" and self.qwen_client:
            return await self.qwen_client.check_credentials()
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
        if self.qwen_client:
            await self.qwen_client.close()
        
        # Close LiteLLM adapter to properly clean up async clients
        litellm_adapter = self.providers.get("litellm")
        if litellm_adapter and hasattr(litellm_adapter, 'close'):
            await litellm_adapter.close()