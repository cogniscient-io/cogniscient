"""Main entry point for the application.

This is the main entry point for the application. It can be used to start
the frontend server, CLI, or to access different system components programmatically.
"""

import sys
import warnings
from cogniscient.utils.shutdown_handler import graceful_shutdown


def _suppress_aiohttp_warnings():
    """
    Suppress specific aiohttp warnings that occur during shutdown.
    This addresses the common issue where aiohttp ClientSession objects
    throw warnings during garbage collection after the event loop is closed.
    """
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
    """Main entry point for the application."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "frontend":
            # Start the frontend server
            from cogniscient.ui.webui.main import run_frontend
            run_frontend()
        elif sys.argv[1] == "cli":
            # Start the CLI
            from cogniscient.ui.cli.main import main as cli_main
            cli_main()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Available commands:")
            print("  frontend - Start the frontend server")
            print("  cli      - Start the command line interface")
    else:
        print("Use 'python main.py frontend' to start the frontend server.")
        print("Use 'python main.py cli' to start the command line interface.")
        print("For programmatic access to the system, use GCSRuntime directly from cogniscient.engine.gcs_runtime")


if __name__ == "__main__":
    main()