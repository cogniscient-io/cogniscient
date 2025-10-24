"""
Configuration Management for GCS Kernel using Pydantic Settings.

This module provides application-wide configuration using Pydantic Settings
for type safety and validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Literal


class KernelSettings(BaseSettings):
    """GCS Kernel configuration settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # LLM Provider settings
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