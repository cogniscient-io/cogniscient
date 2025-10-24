"""
Pydantic Settings for GCS Kernel.

This module provides application-wide configuration using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from typing import Literal


class LLMProviderSettings(BaseSettings):
    """LLM Provider configuration settings."""
    
    # Provider settings
    llm_provider_type: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4-turbo"
    llm_base_url: str = "https://api.openai.com/v1"
    
    # Request settings
    llm_timeout: int = 60
    llm_max_retries: int = 3
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class KernelSettings(BaseSettings):
    """GCS Kernel configuration settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Provider settings (these will be loaded from LLMProviderSettings)
    provider_type: Literal["openai", "anthropic", "ollama"] = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4-turbo"
    base_url: str = "https://api.openai.com/v1"
    
    # Request settings
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 1000
    
    # Application settings
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create a global settings instance
kernel_settings = KernelSettings()