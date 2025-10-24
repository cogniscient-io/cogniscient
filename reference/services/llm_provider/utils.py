"""
Utilities for GCS Kernel LLM Provider Backend.

This module contains utility functions for the LLM provider backend.
"""

import os
from typing import Dict, Any


def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Returns:
        Configuration dictionary with values from environment variables
    """
    config = {}
    
    # Load common LLM provider settings from environment
    api_key = os.getenv("LLM_PROVIDER_API_KEY")
    if api_key:
        config["api_key"] = api_key
    
    model = os.getenv("LLM_PROVIDER_MODEL")
    if model:
        config["model"] = model
    
    base_url = os.getenv("LLM_PROVIDER_BASE_URL")
    if base_url:
        config["base_url"] = base_url
    
    provider_type = os.getenv("LLM_PROVIDER_TYPE", "openai")
    config["provider_type"] = provider_type
    
    timeout = os.getenv("LLM_PROVIDER_TIMEOUT")
    if timeout and timeout.isdigit():
        config["timeout"] = int(timeout)
    
    max_retries = os.getenv("LLM_PROVIDER_MAX_RETRIES")
    if max_retries and max_retries.isdigit():
        config["max_retries"] = int(max_retries)
    
    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate the LLM provider configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    required_fields = ["api_key", "provider_type"]
    
    for field in required_fields:
        if field not in config or not config[field]:
            return False
    
    # Validate provider type
    valid_providers = ["openai"]  # Add more providers as they're implemented
    if config["provider_type"] not in valid_providers:
        return False
    
    return True