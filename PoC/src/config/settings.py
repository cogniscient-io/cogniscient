"""
Configuration settings for the Adaptive Chatbot application.
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Server settings
    host: str = "192.168.0.176"
    port: int = 8002
    debug: bool = False
    
    # LLM API settings
    llm_api_key: Optional[str] = "ollama"
    llm_model: str = "ollama_chat/qwen3:8b"
    llm_base_url: str = "http://192.168.0.230:11434"
    llm_request_timeout: float = 30.0
    llm_max_retries: int = 3
    
    # Application settings
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create a global settings instance
settings = Settings()