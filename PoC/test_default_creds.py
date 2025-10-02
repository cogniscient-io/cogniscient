"""
Test to verify the default credentials location configuration.
"""
import os
from pathlib import Path
from cogniscient.engine.config.settings import settings
from cogniscient.auth.token_manager import TokenManager


def test_default_credentials_location():
    """
    Test that verifies the default credentials location configuration.
    """
    print("Testing default credentials location configuration...")
    print(f"Settings qwen_credentials_file: {settings.qwen_credentials_file}")
    print(f"Settings qwen_credentials_dir: {settings.qwen_credentials_dir}")
    
    # Create a token manager with the settings (which are None by default)
    token_manager = TokenManager(
        credentials_file=settings.qwen_credentials_file,
        credentials_dir=settings.qwen_credentials_dir
    )
    
    print(f"Token manager credentials file path: {token_manager.credentials_file}")
    
    # Check if this matches the expected default
    expected_default = Path.home() / ".qwen" / "oauth_creds.json"
    print(f"Expected default path: {expected_default}")
    
    if str(token_manager.credentials_file) == str(expected_default):
        print("✓ Default credentials path is correctly configured")
    else:
        print("✗ Default credentials path does not match expected value")
        return False
    
    # Check if the directory exists (it should be created)
    creds_dir = token_manager.credentials_file.parent
    if creds_dir.exists():
        print(f"✓ Credentials directory exists: {creds_dir}")
    else:
        print(f"✗ Credentials directory does not exist: {creds_dir}")
        # Try to create it to see if there are permission issues
        try:
            creds_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ Successfully created credentials directory: {creds_dir}")
        except Exception as e:
            print(f"✗ Failed to create credentials directory: {e}")
            return False
    
    # Check if the file exists (it might not if no auth has been performed yet)
    if token_manager.credentials_file.exists():
        print(f"✓ Credentials file exists: {token_manager.credentials_file}")
        print("  Note: This means you have previously authenticated with Qwen")
    else:
        print(f"✗ Credentials file does not exist: {token_manager.credentials_file}")
        print("  Note: This is expected if you haven't authenticated with Qwen yet")
    
    # Test that the token manager can access the location without errors
    try:
        has_creds = token_manager._cached_credentials is None
        print("✓ Token manager can access the credentials location")
    except Exception as e:
        print(f"✗ Token manager failed to access credentials location: {e}")
        return False

    print("\nConfiguration test completed successfully!")
    print(f"Default credentials will be stored at: {expected_default}")
    print("This location will be used when you run 'cogniscient auth' for the first time.")
    
    return True


if __name__ == "__main__":
    success = test_default_credentials_location()
    if not success:
        exit(1)