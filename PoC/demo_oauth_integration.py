"""
Demonstration script for the OAuth and Qwen LLM integration.
"""
import asyncio
from cogniscient.auth.oauth_manager import OAuthManager
from cogniscient.auth.token_manager import TokenManager
from cogniscient.llm.llm_service import LLMService
from cogniscient.engine.config.settings import settings


async def demo():
    print("Cogniscient OAuth and Qwen LLM Integration Demo")
    print("=" * 50)
    
    print("\n1. Checking configuration...")
    print(f"   Default Provider: {settings.default_provider}")
    print(f"   Qwen Client ID: {'SET' if settings.qwen_client_id else 'NOT SET'}")
    print(f"   Authorization Server: {settings.qwen_authorization_server}")
    
    print("\n2. Creating token manager...")
    token_manager = TokenManager(
        credentials_file=settings.qwen_credentials_file,
        credentials_dir=settings.qwen_credentials_dir
    )
    print("   Token manager created successfully")
    
    print("\n3. Checking authentication status...")
    # Use a temporary credentials file to avoid issues with existing files
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp()
    temp_credentials_file = os.path.join(temp_dir, "temp_oauth_creds.json")
    temp_token_manager = TokenManager(credentials_file=temp_credentials_file)
    
    has_creds = await temp_token_manager.has_valid_credentials()
    print(f"   Has valid credentials: {has_creds}")
    
    print("\n4. Creating LLM service with token manager...")
    llm_service = LLMService(token_manager=temp_token_manager)
    print("   LLM service created successfully")
    
    print("\n5. Getting available providers...")
    providers = await llm_service.get_available_providers()
    print(f"   Available providers: {providers}")
    
    print("\n6. Current provider:")
    print(f"   Active provider: {llm_service.current_provider}")
    
    print("\n7. Switching provider to litellm...")
    result = llm_service.set_provider("litellm")
    print(f"   Switch successful: {result}")
    print(f"   Active provider: {llm_service.current_provider}")
    
    print("\n8. Attempting to switch to Qwen provider...")
    result = llm_service.set_provider("qwen")
    print(f"   Switch to qwen successful: {result}")
    print(f"   Active provider: {llm_service.current_provider if result else 'Remained as litellm'}")
    
    # Clean up temp directory
    import shutil
    shutil.rmtree(temp_dir)
    
    # Note: To actually test the Qwen provider, you would need valid credentials
    # which requires a valid client ID and completing the OAuth flow
    
    print("\nDemo completed successfully!")
    print("\nTo use Qwen provider in practice, you need to:")
    print("1. Set QWEN_CLIENT_ID environment variable")
    print("2. Run 'cogniscient auth' to complete OAuth flow")
    print("3. Run 'cogniscient switch-provider --provider qwen' to switch to Qwen")
    

if __name__ == "__main__":
    asyncio.run(demo())