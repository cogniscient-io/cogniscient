"""Test script for environment variable overrides."""

import asyncio
import os
from src.config.settings import settings


def test_env_overrides():
    """Test that environment variables override default settings."""
    print("=== Testing Environment Variable Overrides ===")
    
    # Show original settings
    print(f"Original MAX_CONTEXT_SIZE: {settings.max_context_size}")
    print(f"Original MAX_HISTORY_LENGTH: {settings.max_history_length}")
    print(f"Original COMPRESSION_THRESHOLD: {settings.compression_threshold}")
    
    # Set environment variables to override settings
    os.environ['MAX_CONTEXT_SIZE'] = '4000'
    os.environ['MAX_HISTORY_LENGTH'] = '10'
    os.environ['COMPRESSION_THRESHOLD'] = '8'
    
    # Create a new settings instance to see the overrides
    from src.config.settings import Settings
    new_settings = Settings()
    
    print(f"\nAfter environment variable overrides:")
    print(f"New MAX_CONTEXT_SIZE: {new_settings.max_context_size}")
    print(f"New MAX_HISTORY_LENGTH: {new_settings.max_history_length}")
    print(f"New COMPRESSION_THRESHOLD: {new_settings.compression_threshold}")
    
    # Clean up environment variables
    del os.environ['MAX_CONTEXT_SIZE']
    del os.environ['MAX_HISTORY_LENGTH']
    del os.environ['COMPRESSION_THRESHOLD']


if __name__ == "__main__":
    test_env_overrides()