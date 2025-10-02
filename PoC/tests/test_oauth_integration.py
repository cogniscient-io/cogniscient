"""
Integration tests for the OAuth and Qwen LLM integration.
"""
import pytest
import asyncio
from cogniscient.auth.utils import generate_pkce_pair
from cogniscient.auth.token_manager import QwenCredentials
from cogniscient.engine.config.settings import settings


def test_pkce_generation():
    """Test that PKCE generation works correctly."""
    verifier, challenge = generate_pkce_pair()
    
    # Verify they are properly formed
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) == 128  # Default length


def test_settings_access():
    """Test that settings are accessible."""
    # Check that the new settings fields are available
    assert hasattr(settings, 'default_provider')
    assert hasattr(settings, 'qwen_client_id')
    assert hasattr(settings, 'qwen_authorization_server')
    
    # Check default values
    assert settings.default_provider in ["litellm", "qwen"]


@pytest.mark.asyncio
async def test_qwen_credentials():
    """Test Qwen credentials creation."""
    from datetime import datetime, timedelta
    
    expiry_date = datetime.now() + timedelta(hours=1)
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    # Test that credentials are created properly
    assert credentials.access_token == "test_access_token"
    assert credentials.refresh_token == "test_refresh_token"
    assert credentials.token_type == "Bearer"
    assert credentials.expiry_date == expiry_date
    
    # Test expiration functionality
    assert not credentials.is_expired()  # Should not be expired yet
    
    # Test with expired date
    past_expiry = datetime.now() - timedelta(hours=1)
    expired_credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=past_expiry
    )
    assert expired_credentials.is_expired()  # Should be expired
    
    # Test with buffer - the buffer means it's considered expired early
    # If expiry is in 2 minutes and default buffer is 5 minutes, should be expired (2 < 5)
    future_expiry = datetime.now() + timedelta(seconds=120)  # 2 minutes in future
    future_credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=future_expiry
    )
    # Should be expired because expiry is less than 5 minutes away
    assert future_credentials.is_expired()
    
    # To not be expired, the expiry needs to be MORE than buffer seconds in the future
    safe_future_expiry = datetime.now() + timedelta(seconds=400)  # 6+ minutes in future (more than 5-min default buffer)
    safe_future_credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=safe_future_expiry
    )
    # Should not be expired because expiry is more than 5 minutes away
    assert not safe_future_credentials.is_expired()
    
    # But using a larger buffer (e.g. 7 minutes) when expiry is only 6+ minutes away would make it expired
    assert safe_future_credentials.is_expired(buffer_seconds=420)  # 7 minute buffer