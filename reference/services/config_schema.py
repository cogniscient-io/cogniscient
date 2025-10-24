"""
Configuration Schemas for GCS Kernel LLM Provider Backend.

This module provides configuration schemas using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Literal
from typing import Dict, Any, List


class LLMProviderSettings(BaseSettings):
    """Configuration for LLM provider backend using Pydantic Settings."""
    
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


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate general configuration and return list of errors."""
    errors = []
    
    # With Pydantic Settings, most validation happens automatically
    # This is for additional custom validation if needed
    if config.get("provider_type") not in ["openai", "anthropic", "ollama"]:
        errors.append(f"Invalid provider type: {config.get('provider_type')}")
    
    return errors