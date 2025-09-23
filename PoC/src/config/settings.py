"""
Configuration settings for the Adaptive Chatbot application.
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 9001
    debug: bool = False
    
    # LLM API settings
    llm_api_key: Optional[str] = "ollama"
    llm_model: str = "ollama_chat/qwen3:8b"
    llm_base_url: str = "http://192.168.0.230:11434"
    llm_request_timeout: float = 30.0
    llm_max_retries: int = 3
    
    # Conversation history settings
    max_context_size: int = 8000  # Maximum context window size in characters
    max_history_length: int = 20  # Maximum number of conversation turns to keep
    compression_threshold: int = 15  # Compress when history reaches this length
    
    # Application settings
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create a global settings instance
settings = Settings()