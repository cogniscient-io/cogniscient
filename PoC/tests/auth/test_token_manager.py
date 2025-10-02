"""
Tests for the token manager.
"""
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
import pytest
from cogniscient.auth.token_manager import TokenManager, QwenCredentials


@pytest.fixture
def token_manager():
    """Create a temporary token manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        credentials_file = os.path.join(temp_dir, "test_creds.json")
        token_manager = TokenManager(credentials_file=credentials_file)
        yield token_manager


@pytest.mark.asyncio
async def test_save_and_load_credentials(token_manager):
    """Test saving and loading credentials."""
    expiry_date = datetime.now() + timedelta(hours=1)
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    # Save credentials
    success = await token_manager.save_credentials(credentials)
    assert success is True
    
    # Load credentials
    loaded_credentials = await token_manager.load_credentials()
    assert loaded_credentials is not None
    assert loaded_credentials.access_token == "test_access_token"
    assert loaded_credentials.refresh_token == "test_refresh_token"
    assert loaded_credentials.token_type == "Bearer"


@pytest.mark.asyncio
async def test_has_valid_credentials(token_manager):
    """Test checking for valid credentials."""
    # Initially, should not have valid credentials
    has_valid = await token_manager.has_valid_credentials()
    assert has_valid is False
    
    # Add valid credentials
    expiry_date = datetime.now() + timedelta(hours=1)
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    await token_manager.save_credentials(credentials)
    
    # Now should have valid credentials
    has_valid = await token_manager.has_valid_credentials()
    assert has_valid is True


@pytest.mark.asyncio
async def test_credentials_expired(token_manager):
    """Test checking for expired credentials."""
    # Add expired credentials
    expiry_date = datetime.now() - timedelta(hours=1)  # Expired 1 hour ago
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    await token_manager.save_credentials(credentials)
    
    # Should not have valid credentials as they are expired
    has_valid = await token_manager.has_valid_credentials()
    assert has_valid is False


@pytest.mark.asyncio
async def test_get_valid_access_token(token_manager):
    """Test getting a valid access token."""
    expiry_date = datetime.now() + timedelta(hours=1)
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    await token_manager.save_credentials(credentials)
    
    # Get valid access token
    token = await token_manager.get_valid_access_token()
    assert token == "test_access_token"


@pytest.mark.asyncio
async def test_clear_credentials(token_manager):
    """Test clearing credentials."""
    expiry_date = datetime.now() + timedelta(hours=1)
    credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    await token_manager.save_credentials(credentials)
    
    # Verify credentials exist
    has_valid = await token_manager.has_valid_credentials()
    assert has_valid is True
    
    # Clear credentials
    success = await token_manager.clear_credentials()
    assert success is True
    
    # Verify credentials are cleared
    has_valid = await token_manager.has_valid_credentials()
    assert has_valid is False


def test_qwen_credentials_to_from_dict():
    """Test converting QwenCredentials to and from dictionary."""
    expiry_date = datetime.now() + timedelta(hours=1)
    original_credentials = QwenCredentials(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="Bearer",
        expiry_date=expiry_date
    )
    
    # Convert to dict
    creds_dict = original_credentials.to_dict()
    
    # Convert back from dict
    new_credentials = QwenCredentials.from_dict(creds_dict)
    
    assert new_credentials.access_token == original_credentials.access_token
    assert new_credentials.refresh_token == original_credentials.refresh_token
    assert new_credentials.token_type == original_credentials.token_type
    # Note: The datetime precision might differ slightly, so we'll check that they're close
    assert abs((new_credentials.expiry_date - original_credentials.expiry_date).total_seconds()) < 1