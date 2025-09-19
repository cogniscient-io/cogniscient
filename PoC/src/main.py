"""Main entry point for the dynamic control system."""

import uvicorn
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from control_system.manager import ControlSystemManager
from agents.sample_agent_a import SampleAgentA
from agents.sample_agent_b import SampleAgentB
from config.settings import settings

def main():
    """Main function to run the control system."""
    # Initialize the control system manager
    manager = ControlSystemManager()
    
    # Create and add sample agents
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    
    # Generate configuration files for all agents
    manager.generate_all_configs()
    
    print("Configuration files generated successfully.")

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
        main()