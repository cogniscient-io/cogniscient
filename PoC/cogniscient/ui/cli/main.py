"""
Main entry point for the Cogniscient CLI with both interactive and command modes.
"""
import argparse
import sys
import asyncio
import warnings
from .command_mode import run_command_mode
from .interactive_mode import InteractiveCLI
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings
from cogniscient.utils.shutdown_handler import graceful_shutdown


def _suppress_aiohttp_warnings():
    """
    Suppress specific aiohttp warnings that occur during shutdown.
    This addresses the common issue where aiohttp ClientSession objects
    throw warnings during garbage collection after the event loop is closed.
    """
    import warnings
    import sys
    
    # Filter specific warnings related to aiohttp ClientSession cleanup
    warnings.filterwarnings("ignore", 
                           message=".*aiohttp.*", 
                           category=ResourceWarning,
                           module=".*aiohttp.*")
    
    # Also temporarily patch warnings.showwarning to suppress specific messages
    original_showwarning = warnings.showwarning
    
    def custom_showwarning(message, category, filename, lineno, file=None, line=None):
        # Check if this is the specific aiohttp warning we want to suppress
        msg_str = str(message)
        if ("ResourceWarning" in msg_str or 
            "ClientSession.__del__" in msg_str or 
            "BaseConnector.__del__" in msg_str or
            ("aiohttp" in msg_str and "AttributeError" in msg_str and "from_exception" in msg_str)):
            return  # Suppress this warning
        # Call the original function for other warnings
        original_showwarning(message, category, filename, lineno, file, line)
    
    warnings.showwarning = custom_showwarning

# Apply the warning suppression early
_suppress_aiohttp_warnings()


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
        
        # Register the shutdown function with the graceful shutdown handler
        async def async_shutdown():
            if not hasattr(gcs, 'shutdown_initiated') or not gcs.shutdown_initiated:
                try:
                    await gcs.shutdown()
                except Exception as e:
                    print(f"Warning: Error during system shutdown: {e}")
        
        graceful_shutdown.register_shutdown_handler(async_shutdown)
        
        # Perform shutdown immediately if not already initiated
        if not hasattr(gcs, 'shutdown_initiated') or not gcs.shutdown_initiated:
            try:
                # Try to get the current running loop
                loop = asyncio.get_running_loop()
                # If we're in a running loop, schedule the shutdown as a task
                task = loop.create_task(gcs.shutdown())
                # Give a brief moment for the shutdown to start
                loop.run_until_complete(asyncio.sleep(0.05))
            except RuntimeError:
                # No event loop running, we can create a new one
                asyncio.run(gcs.shutdown())
            except Exception as e:
                print(f"Warning: Error during system shutdown: {e}")
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


# This allows the module to be run directly with `python -m cogniscient.cli.main`
# while still supporting the entry point configuration in pyproject.toml
if __name__ == "__main__":
    main()