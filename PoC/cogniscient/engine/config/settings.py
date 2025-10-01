"""
Configuration settings for the Adaptive Chatbot application.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
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
    llm_base_url: str = "http://localhost:11434"
    llm_request_timeout: float = 30.0
    llm_max_retries: int = 3
    
    # Conversation history settings
    max_context_size: int = 8000  # Maximum context window size in characters
    max_history_length: int = 20  # Maximum number of conversation turns to keep
    compression_threshold: int = 15  # Compress when history reaches this length
    
    # Application settings
    log_level: str = "INFO"
    
    # Add config directory setting
    config_dir: str = "."
    
    # Add agents directory setting
    agents_dir: str = "cogniscient/agentSDK"
    
    # Runtime data directory for system generated files
    runtime_data_dir: str = "runtime_data"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    def model_post_init(self, __context):
        """Post initialization validation to ensure directories exist if specified."""
        # Validate config_dir after loading from env
        if self.config_dir and self.config_dir != "." and not os.path.exists(self.config_dir):
            print(f"Warning: Config directory '{self.config_dir}' from .env does not exist. Using default: '.'")
            self.config_dir = "."
        
        # Validate agents_dir after loading from env
        if self.agents_dir and self.agents_dir != "cogniscient/agentSDK" and not os.path.exists(self.agents_dir):
            print(f"Warning: Agents directory '{self.agents_dir}' from .env does not exist. Using default: 'cogniscient/agentSDK'")
            self.agents_dir = "cogniscient/agentSDK"

# Create a global settings instance
settings = Settings()