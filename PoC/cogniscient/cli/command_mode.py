"""
Command-line mode implementation for Cogniscient.

This module preserves the existing command-line functionality while
allowing integration with the new interactive features.
"""
import argparse
import sys
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings

def run_command_mode():
    """Execute the original command-line interface."""
    parser = argparse.ArgumentParser(description="Cogniscient - Generic Control System")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["run", "list-configs", "load-config"],
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Use settings from .env if no command-line values provided
    config_dir = args.config_dir if args.config_dir is not None else settings.config_dir
    agents_dir = args.agents_dir if args.agents_dir is not None else settings.agents_dir

    # Initialize the GCS runtime
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