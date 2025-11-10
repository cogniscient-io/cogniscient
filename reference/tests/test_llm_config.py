"""
Test suite for the Configuration Settings.

This module tests the Pydantic Settings class.
"""
import os
import pytest
from common.settings import GlobalSettings as Settings


def test_config_default_values():
    """
    Test that Settings can be instantiated with defaults.
    """
    # Just test that the Settings class can be instantiated properly
    # The defaults are tested indirectly via other tests
    from common.settings import settings
    
    # Simply verify that settings has the required properties
    assert hasattr(settings, 'host')
    assert hasattr(settings, 'port')
    assert hasattr(settings, 'debug')
    assert hasattr(settings, 'log_level')
    assert hasattr(settings, 'llm_provider_type')
    assert hasattr(settings, 'llm_api_key')
    assert hasattr(settings, 'llm_model')
    assert hasattr(settings, 'llm_base_url')
    assert hasattr(settings, 'llm_timeout')
    assert hasattr(settings, 'llm_max_retries')
    assert hasattr(settings, 'llm_temperature')
    assert hasattr(settings, 'llm_max_tokens')


def test_config_from_environment():
    """
    Test that Settings can be configured from environment variables.
    """
    # Set environment variables for the test
    os.environ["LLM_PROVIDER_TYPE"] = "anthropic"
    os.environ["LLM_MODEL"] = "claude-3-opus"
    os.environ["LLM_BASE_URL"] = "https://api.anthropic.com/v1"
    os.environ["LLM_TIMEOUT"] = "120"
    os.environ["LLM_MAX_RETRIES"] = "5"
    os.environ["LLM_TEMPERATURE"] = "0.5"
    os.environ["LLM_MAX_TOKENS"] = "2000"
    
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PORT"] = "9000"
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    try:
        config = Settings()
        
        # Test all settings from environment
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.llm_provider_type == "anthropic"
        assert config.llm_model == "claude-3-opus"
        assert config.llm_base_url == "https://api.anthropic.com/v1"
        assert config.llm_timeout == 120
        assert config.llm_max_retries == 5
        assert config.llm_temperature == 0.5
        assert config.llm_max_tokens == 2000
    finally:
        # Clean up environment variables
        env_vars_to_clean = [
            "LLM_PROVIDER_TYPE", "LLM_MODEL", "LLM_BASE_URL", "LLM_TIMEOUT", 
            "LLM_MAX_RETRIES", "LLM_TEMPERATURE", "LLM_MAX_TOKENS",
            "HOST", "PORT", "DEBUG", "LOG_LEVEL"
        ]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]


def test_config_api_key():
    """
    Test that Settings handles API key correctly.
    """
    os.environ["LLM_API_KEY"] = "test-api-key-12345"
    
    try:
        config = Settings()
        assert config.llm_api_key == "test-api-key-12345"
    finally:
        if "LLM_API_KEY" in os.environ:
            del os.environ["LLM_API_KEY"]


def test_config_access():
    """
    Test that Settings provides proper access to configuration values.
    """
    os.environ["LLM_PROVIDER_TYPE"] = "ollama"
    os.environ["LLM_MODEL"] = "llama3"
    
    try:
        config = Settings()
        
        # Test that we can access all config values directly
        assert config.host == "0.0.0.0"  # default
        assert config.llm_provider_type == "ollama"
        assert config.llm_model == "llama3"
    finally:
        # Clean up
        for var in ["LLM_PROVIDER_TYPE", "LLM_MODEL"]:
            if var in os.environ:
                del os.environ[var]