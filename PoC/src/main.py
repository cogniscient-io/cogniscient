"""Main entry point for the application.

This module serves as the entry point for launching either the frontend server
or for development purposes.
"""

import uvicorn
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import settings


def run_frontend():
    """Run the frontend server."""
    # Add static file serving
    from fastapi.staticfiles import StaticFiles
    from frontend.api import app
    import os
    
    # Serve static files
    static_dir = os.path.join(os.path.dirname(__file__), "frontend", "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    
    # Add root endpoint to serve index.html
    @app.get("/")
    async def read_root():
        return {"message": "LLM Orchestration Frontend Server"}
    
    # Use host and port from settings
    uvicorn.run("src.frontend.api:app", 
                host=settings.host, 
                port=settings.port, 
                reload=settings.debug)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "frontend":
        run_frontend()
    else:
        print("Use 'python src/main.py frontend' to start the frontend server.")
        print("For programmatic access to the system, use UCSRuntime directly from src.ucs_runtime")