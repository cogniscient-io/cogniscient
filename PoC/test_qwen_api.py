#!/usr/bin/env python3
"""
Simple test script to verify Qwen API integration using existing OAuth tokens.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cogniscient.auth.token_manager import TokenManager
from cogniscient.llm.qwen_client import QwenClient
from cogniscient.engine.config.settings import settings
from cogniscient.llm.llm_service import LLMService


async def test_qwen_api():
    """Test the Qwen API with existing OAuth tokens."""
    print("Testing Qwen API with existing OAuth tokens...")
    
    # Check if Qwen client ID is configured
    if not settings.qwen_client_id:
        print("Error: QWEN_CLIENT_ID not configured in environment.")
        return False
    
    print(f"Using Qwen Client ID: {settings.qwen_client_id}")
    print(f"Using credentials file: {settings.qwen_credentials_file or '~/.qwen/oauth_creds.json'}")
    
    # Initialize token manager
    token_manager = TokenManager(
        credentials_file=settings.qwen_credentials_file,
        credentials_dir=settings.qwen_credentials_dir
    )
    
    # Check if we have valid credentials
    has_creds = await token_manager.has_valid_credentials()
    if not has_creds:
        print("Error: No valid Qwen OAuth credentials found.")
        # Try to show the credentials file status
        creds_file = token_manager.credentials_file
        if creds_file.exists():
            print(f"Credentials file exists: {creds_file}")
            import json
            try:
                with open(creds_file) as f:
                    creds = json.load(f)
                    print(f"Credentials keys: {list(creds.keys())}")
                    # Check if the access token has expired
                    import time
                    if 'expiry_date' in creds:
                        expiry_time = creds['expiry_date'] / 1000  # Convert milliseconds to seconds
                        current_time = time.time()
                        if expiry_time < current_time:
                            print(f"Credentials have expired: exp {expiry_time} vs now {current_time}")
                        else:
                            print(f"Credentials expiry: {expiry_time} (in {expiry_time - current_time} seconds)")
            except Exception as e:
                print(f"Error reading credentials file: {e}")
        else:
            print(f"Credentials file does not exist: {creds_file}")
        return False
    
    print("Valid Qwen credentials found!")
    
    # Initialize Qwen client
    # Note: We're not setting base_url here since the Python QwenClient 
    # will dynamically determine the correct URL from the credentials
    qwen_client = QwenClient(
        token_manager=token_manager
    )
    
    try:
        # Test the connection by sending a simple "hello" message
        print("\nSending 'hello' message to Qwen API...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        response = await qwen_client.generate_response(
            messages=messages,
            model="coder-model"  # Using the default Qwen model from the TypeScript code
        )
        
        if response:
            print(f"✅ Success! Response: {response}")
            return True
        else:
            print("❌ Failed to get response from Qwen API")
            return False
            
    except Exception as e:
        print(f"❌ Error calling Qwen API: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await qwen_client.close()


async def test_provider_switch():
    """Test switching to Qwen provider using the LLMService."""
    print("\n" + "="*50)
    print("Testing Provider Manager with Qwen...")
    
    # Initialize token manager
    token_manager = TokenManager(
        credentials_file=settings.qwen_credentials_file,
        credentials_dir=settings.qwen_credentials_dir
    )
    
    # Initialize LLM service with token manager
    llm_service = LLMService(token_manager=token_manager)
    
    print(f"Available providers: {await llm_service.get_available_providers()}")
    
    # Try to switch to Qwen provider
    success = llm_service.set_provider("qwen")
    if success:
        print("✅ Successfully switched to Qwen provider!")
        
        # Try to generate a response using the provider manager
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello from Cogniscient!"}
        ]
        
        response = await llm_service.generate_response(
            messages=messages,
            model="coder-model"  # Using the default Qwen model from the TypeScript code
        )
        
        if response:
            print(f"✅ Provider manager response: {response}")
            return True
        else:
            print("❌ Provider manager failed to get response")
            return False
    else:
        print("❌ Failed to switch to Qwen provider")
        return False


async def main():
    """Main test function."""
    print("Starting Qwen API integration test...")
    print(f"Default provider: {settings.default_provider}")
    
    # Test direct Qwen client
    qwen_success = await test_qwen_api()
    
    if qwen_success:
        # Test provider manager
        provider_success = await test_provider_switch()
        if provider_success:
            print("\n🎉 All tests passed! Qwen API integration is working correctly.")
            return True
    
    print("\n❌ Some tests failed.")
    return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)