"""
Test to verify the token manager can load existing credentials.
"""
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings
import asyncio


async def test_load_existing_credentials():
    """
    Test that verifies the token manager can load existing credentials.
    """
    print("Testing loading of existing credentials...")
    
    # Create a token manager with the default settings (None)
    token_manager = TokenManager(
        credentials_file=settings.qwen_credentials_file,
        credentials_dir=settings.qwen_credentials_dir
    )
    
    print(f"Looking for credentials at: {token_manager.credentials_file}")
    
    # Try to load credentials
    try:
        credentials = await token_manager.load_credentials()
        if credentials:
            print("✓ Successfully loaded credentials")
            print(f"  Access token starts with: {credentials.access_token[:20]}...")
            print(f"  Token type: {credentials.token_type}")
            print(f"  Refresh token starts with: {credentials.refresh_token[:20]}...")
            if credentials.expiry_date:
                print(f"  Expiry date: {credentials.expiry_date}")
                print(f"  Is expired: {credentials.is_expired()}")
                print(f"  Is expired (with 5-min buffer): {credentials.is_expired(buffer_seconds=300)}")
            else:
                print("  No expiry date set")
        else:
            print("✗ No credentials found or failed to load")
            return False
    except Exception as e:
        print(f"✗ Error loading credentials: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test getting a valid access token
    try:
        access_token = await token_manager.get_valid_access_token()
        if access_token:
            print(f"✓ Successfully retrieved valid access token")
            print(f"  Token starts with: {access_token[:20]}...")
        else:
            print("✗ No valid access token available (possibly expired)")
            return False
    except Exception as e:
        print(f"✗ Error getting access token: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test the has_valid_credentials method
    try:
        has_valid = await token_manager.has_valid_credentials()
        print(f"✓ has_valid_credentials() returned: {has_valid}")
        if not has_valid:
            print("  (This is expected if the token has expired)")
    except Exception as e:
        print(f"✗ Error checking valid credentials: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\nCredentials loading test completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_load_existing_credentials())
    if not success:
        exit(1)