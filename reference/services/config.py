"""
Configuration settings for the GCS Kernel application.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LLM API settings
    llm_provider_type: str = "openai"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4-turbo"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: int = 60
    llm_max_retries: int = 3
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000

    # Application settings
    log_level: str = "INFO"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Create a global settings instance
settings = Settings()