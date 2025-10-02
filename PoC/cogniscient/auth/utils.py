import base64
import hashlib
import os
import secrets
from typing import Tuple


def generate_code_verifier(length: int = 128) -> str:
    """
    Generate a PKCE code verifier.
    
    Args:
        length: Length of the code verifier (must be between 43 and 128 characters)
        
    Returns:
        A random string to be used as the code verifier
    """
    if length < 43 or length > 128:
        raise ValueError("Code verifier length must be between 43 and 128 characters")
    
    # Generate a random string of specified length using URL-safe characters
    verifier = secrets.token_urlsafe(length)[:length]
    return verifier


def generate_code_challenge(code_verifier: str) -> str:
    """
    Generate a PKCE code challenge from the code verifier using SHA256 method.
    
    Args:
        code_verifier: The code verifier string
        
    Returns:
        The code challenge string encoded with base64url
    """
    # Hash the code verifier using SHA-256
    hashed_verifier = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    
    # Encode the hash with base64url encoding
    challenge = base64.urlsafe_b64encode(hashed_verifier).decode('utf-8')
    
    # Remove padding characters for base64url encoding
    challenge = challenge.rstrip('=')
    
    return challenge


def generate_code_challenge_plain(code_verifier: str) -> str:
    """
    Generate a PKCE code challenge using the 'plain' method (not recommended for production).
    
    Args:
        code_verifier: The code verifier string
        
    Returns:
        The same code verifier string (plain method)
    """
    return code_verifier


def generate_pkce_pair(length: int = 128) -> Tuple[str, str]:
    """
    Generate both code verifier and code challenge pair.
    
    Args:
        length: Length of the code verifier
        
    Returns:
        A tuple containing (code_verifier, code_challenge)
    """
    code_verifier = generate_code_verifier(length)
    code_challenge = generate_code_challenge(code_verifier)
    return code_verifier, code_challenge