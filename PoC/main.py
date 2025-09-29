"""Main entry point for the application.

This is the main entry point for the application. It can be used to start
the frontend server or to access different system components programmatically.
"""

import sys
import os


def main():
    """Main entry point for the application."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "frontend":
            # Start the frontend server
            from frontend.main import run_frontend
            run_frontend()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Available commands:")
            print("  frontend - Start the frontend server")
    else:
        print("Use 'python main.py frontend' to start the frontend server.")
        print("For programmatic access to the system, use GCSRuntime directly from cogniscient.engine.gcs_runtime")


if __name__ == "__main__":
    main()