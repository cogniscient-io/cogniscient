"""
Pydantic Settings for GCS Kernel LLM Provider Backend.

This module provides configuration using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from typing import Literal


class LLMProviderSettings(BaseSettings):
    """LLM Provider configuration settings."""
    
    # Provider settings
    provider_type: Literal["openai", "anthropic", "ollama"] = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4-turbo"
    base_url: str = "https://api.openai.com/v1"
    
    # Request settings
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 1000
    
    class Config:
        env_prefix = "LLM_"
        case_sensitive = False
        env_file = ".env"


# Create a global settings instance
llm_settings = LLMProviderSettings()