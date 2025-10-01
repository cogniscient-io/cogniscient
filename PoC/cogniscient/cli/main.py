"""
Main entry point for the Cogniscient CLI with both interactive and command modes.
"""
import argparse
import sys
from .command_mode import run_command_mode
from .interactive_mode import InteractiveCLI
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings

def main():
    """
    Main entry point for the Cogniscient CLI supporting both command and interactive modes.
    """
    _ = argparse.ArgumentParser(
        description="Cogniscient - Generic Control System with Interactive CLI",
        add_help=False
    )
    
    # Create a separate parser for just the mode selection
    mode_parser = argparse.ArgumentParser(add_help=False)
    mode_parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute ('chat' for interactive mode, or traditional commands: run, list-configs, load-config)"
    )
    
    # Parse the first argument to determine mode
    args, remaining = mode_parser.parse_known_args()
    
    if args.command == "chat" or not args.command:  # Start interactive if no command or 'chat' command
        # Launch interactive mode
        # Parse additional args for interactive session configuration
        chat_parser = argparse.ArgumentParser(parents=[mode_parser])
        chat_parser.add_argument(
            "--session",
            type=str,
            help="Named session to continue previous work"
        )
        chat_args = chat_parser.parse_args()
        
        print(f"Starting interactive Cogniscient session{' with ' + chat_args.session if chat_args.session else ''}...")
        
        # Initialize the GCS runtime with settings from .env
        gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
        
        # Create and start interactive CLI
        interactive_cli = InteractiveCLI(gcs)
        interactive_cli.start_session()
        
        # Shutdown the system when exiting
        gcs.shutdown()
    else:
        # Process as traditional command mode
        # Reconstruct sys.argv to pass to command mode
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]] + remaining
        
        # If no command is specified but it's not 'chat', show help
        if not args.command:
            print("Cogniscient - Generic Control System")
            print("Usage: cogniscient [command] [options]")
            print("Commands:")
            print("  chat              Start interactive session")
            print("  run               Initialize and run the system with agents")
            print("  list-configs      List all available configurations")
            print("  load-config       Load a specific configuration")
            print("  -h, --help       Show this help message")
            sys.exit(0)
        else:
            # Restore sys.argv and run command mode
            sys.argv = original_argv
            run_command_mode()