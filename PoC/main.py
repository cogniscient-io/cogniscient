"""Main entry point for the application.

This is the main entry point for the application. It can be used to start
the frontend server, CLI, or to access different system components programmatically.
"""

import sys


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