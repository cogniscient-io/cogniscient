"""
Command-line mode implementation for Cogniscient.

This module preserves the existing command-line functionality while
allowing integration with the new interactive features.
"""
import argparse
import asyncio
import sys
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings
from cogniscient.auth.oauth_manager import OAuthManager
from cogniscient.auth.token_manager import TokenManager

def run_command_mode():
    """Execute the original command-line interface."""
    parser = argparse.ArgumentParser(description="Cogniscient - Generic Control System")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["run", "list-configs", "load-config", "auth", "auth-status", "switch-provider"],
        help="Command to execute"
    )
    parser.add_argument(
        "--config-dir",
        default=None,  # Using None to check if user provided value
        help="Directory to load agent configurations from (default: from .env settings)"
    )
    parser.add_argument(
        "--agents-dir",
        default=None,  # Using None to check if user provided value
        help="Directory where agent modules are located (default: from .env settings)"
    )
    parser.add_argument(
        "--config-name",
        help="Configuration name to load (for load-config command)"
    )
    parser.add_argument(
        "--provider",
        help="Provider name to switch to (for switch-provider command)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command in ["run", "list-configs", "load-config"]:
        # Use settings from .env if no command-line values provided
        config_dir = args.config_dir if args.config_dir is not None else settings.config_dir
        agents_dir = args.agents_dir if args.agents_dir is not None else settings.agents_dir

        # Initialize the GCS runtime for config-related commands
        gcs = GCSRuntime(config_dir=config_dir, agents_dir=agents_dir)

        if args.command == "run":
            # Load all agents and run a simple test
            gcs.load_all_agents()
            print("Cogniscient system initialized with agents:", list(gcs.agents.keys()))

        elif args.command == "list-configs":
            # List all available configurations
            configs = gcs.list_available_configurations()
            print("Available configurations:")
            for config in configs:
                print(f"  - {config}")

        elif args.command == "load-config":
            if not args.config_name:
                print("Error: --config-name is required for load-config command")
                sys.exit(1)
            
            try:
                gcs.load_configuration(args.config_name)
                print(f"Configuration '{args.config_name}' loaded successfully")
                print("Active agents:", list(gcs.agents.keys()))
            except ValueError as e:
                print(f"Error loading configuration: {e}")
                sys.exit(1)

        # Shutdown the system
        gcs.shutdown()
    
    elif args.command == "auth":
        # Initialize OAuth manager for authentication
        if not settings.qwen_client_id:
            print("Error: Qwen client ID not configured. Please set QWEN_CLIENT_ID in your environment.")
            sys.exit(1)
        
        oauth_manager = OAuthManager(
            client_id=settings.qwen_client_id,
            authorization_server=settings.qwen_authorization_server,
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        async def authenticate():
            print("Starting OAuth device flow...")
            success = await oauth_manager.authenticate_with_device_flow()
            if success:
                print("Authentication successful!")
            else:
                print("Authentication failed!")
                sys.exit(1)
        
        asyncio.run(authenticate())
        
    elif args.command == "auth-status":
        # Check authentication status
        token_manager = TokenManager(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        async def check_auth_status():
            has_creds = await token_manager.has_valid_credentials()
            if has_creds:
                print("Authentication status: Valid credentials found")
                token = await token_manager.get_valid_access_token()
                if token:
                    print("Access token is valid")
            else:
                print("Authentication status: No valid credentials found")
        
        asyncio.run(check_auth_status())
        
    elif args.command == "switch-provider":
        if not args.provider:
            print("Error: --provider is required for switch-provider command")
            print("Available providers: litellm, qwen")
            sys.exit(1)
        
        # Initialize GCS runtime to access provider manager
        gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
        
        async def switch_provider():
            success = gcs.llm_service.provider_manager.set_provider(args.provider)
            if success:
                print(f"Provider switched to: {args.provider}")
            else:
                print(f"Failed to switch to provider: {args.provider}")
                available = await gcs.llm_service.provider_manager.get_available_providers()
                print(f"Available providers: {available}")
                sys.exit(1)
        
        asyncio.run(switch_provider())
        gcs.shutdown()