"""
Tests for the auth module utilities.
"""
import pytest
from cogniscient.auth.utils import generate_code_verifier, generate_code_challenge, generate_pkce_pair


def test_generate_code_verifier():
    """Test generating a code verifier."""
    verifier = generate_code_verifier()
    
    # Check length (default is 128)
    assert len(verifier) == 128
    
    # Check that it only contains URL-safe characters
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.' + '~')
    assert all(c in valid_chars for c in verifier)


def test_generate_code_verifier_custom_length():
    """Test generating a code verifier with custom length."""
    verifier = generate_code_verifier(length=43)
    assert len(verifier) == 43


def test_generate_code_verifier_invalid_length():
    """Test generating a code verifier with invalid length."""
    with pytest.raises(ValueError):
        generate_code_verifier(length=42)  # Too short
    
    with pytest.raises(ValueError):
        generate_code_verifier(length=129)  # Too long


def test_generate_code_challenge():
    """Test generating a code challenge from a verifier."""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    
    # Check that the challenge is a string
    assert isinstance(challenge, str)
    
    # Check that it contains only URL-safe characters
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.')
    assert all(c in valid_chars for c in challenge)


def test_generate_pkce_pair():
    """Test generating a PKCE pair."""
    verifier, challenge = generate_pkce_pair()
    
    # Check that both are strings
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    
    # Verify the relationship between verifier and challenge
    expected_challenge = generate_code_challenge(verifier)
    assert challenge == expected_challenge