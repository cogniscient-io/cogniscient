"""Main entry point for the application.

This module serves as the entry point for launching either the frontend server
or for development purposes.
"""

import uvicorn
import sys
import os

# Add the home directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from cogniscient.engine.config.settings import settings


def run_frontend():
    """Run the frontend server."""
    # Add static file serving
    from fastapi.staticfiles import StaticFiles
    from frontend.api import app
    import os
    
    # Serve static files at /static route to ensure CSS is accessible at /static/css/style.css
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Use host and port from settings
    uvicorn.run("frontend.api:app", 
                host=settings.host, 
                port=settings.port, 
                reload=settings.debug)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "frontend":
        run_frontend()
    else:
        print("Use 'python -m frontend.main frontend' or 'cd frontend && python main.py frontend' to start the frontend server.")
        print("For programmatic access to the system, use UCSRuntime directly from cogniscient.engine.ucs_runtime")