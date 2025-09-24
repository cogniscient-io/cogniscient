"""
Base external agent implementation that can be used to create custom external agents.

This module provides a BaseExternalAgent class that can be inherited to create
custom external agents that can be registered with the UCS system via the
REST API.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
import uvicorn


class BaseExternalAgent:
    """
    Base class for creating external agents that can be registered with UCS.
    
    This class provides the basic structure and utilities needed to create
    external agents that can be dynamically registered with the UCS system.
    """
    
    def __init__(self, 
                 name: str, 
                 version: str = "1.0.0", 
                 description: str = "",
                 host: str = "0.0.0.0", 
                 port: int = 8001,
                 methods: Optional[Dict[str, Any]] = None):
        """
        Initialize the base external agent.
        
        Args:
            name: Name of the agent
            version: Version of the agent
            description: Description of the agent's functionality
            host: Host address for the agent's API server
            port: Port for the agent's API server
            methods: Dictionary of available methods with their metadata
        """
        self.name = name
        self.version = version
        self.description = description
        self.host = host
        self.port = port
        self.methods = methods or {}
        
        # Create the FastAPI app
        self.app = FastAPI(title=f"{name} External Agent", version=version)
        
        # Set up logging
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        
        # Add handlers to avoid "no handler" warnings
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Register the standard methods
        self._register_standard_routes()
    
    def _register_standard_routes(self):
        """Register standard routes for the external agent."""
        # Root endpoint to return agent info
        @self.app.get("/")
        async def root():
            return {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "methods": self.methods
            }
        
        # Health check endpoint
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "name": self.name,
                "version": self.version
            }
        
        # Dynamic method routing
        @self.app.post("/{method_name}")
        async def call_method(method_name: str, payload: Dict[str, Any]):
            if method_name not in self.methods:
                return {
                    "status": "error",
                    "message": f"Method {method_name} not found"
                }
            
            try:
                # Call the specific method
                method = getattr(self, method_name, None)
                if method is None:
                    return {
                        "status": "error",
                        "message": f"Method {method_name} not implemented"
                    }
                
                # Check if the method is async
                if asyncio.iscoroutinefunction(method):
                    result = await method(**payload)
                else:
                    result = method(**payload)
                
                return {
                    "status": "success",
                    "result": result
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def register_method(self, name: str, description: str = "", parameters: Optional[Dict] = None):
        """
        Register a method with the agent.
        
        Args:
            name: Name of the method
            description: Description of what the method does
            parameters: Dictionary describing the parameters the method accepts
        """
        if name not in self.methods:
            self.methods[name] = {
                "description": description,
                "parameters": parameters or {}
            }
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the external agent server.
        
        Args:
            host: Host address to run the server on (defaults to self.host)
            port: Port to run the server on (defaults to self.port)
        """
        run_host = host or self.host
        run_port = port or self.port
        
        self.logger.info(f"Starting external agent {self.name} on {run_host}:{run_port}")
        uvicorn.run(self.app, host=run_host, port=run_port)
    
    async def run_async(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the external agent server asynchronously.
        
        Args:
            host: Host address to run the server on (defaults to self.host)
            port: Port to run the server on (defaults to self.port)
        """
        run_host = host or self.host
        run_port = port or self.port
        
        self.logger.info(f"Starting external agent {self.name} on {run_host}:{run_port}")
        config = uvicorn.Config(self.app, host=run_host, port=run_port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_registration_info(self, endpoint_url: str, 
                            authentication: Optional[Dict] = None,
                            health_check_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the registration information needed to register this agent with UCS.
        
        Args:
            endpoint_url: The base URL where this agent is hosted
            authentication: Authentication configuration if required
            health_check_url: Custom health check URL (defaults to endpoint_url + /health)
            
        Returns:
            Dictionary containing registration information
        """
        registration_info = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "endpoint_url": endpoint_url,
            "methods": self.methods,
            "enabled": True,
            "settings": {
                "timeout": 30
            }
        }
        
        if authentication:
            registration_info["authentication"] = authentication
            
        if health_check_url:
            registration_info["health_check_url"] = health_check_url
        else:
            registration_info["health_check_url"] = f"{endpoint_url.rstrip('/')}/health"
            
        return registration_info


class SimpleMathAgent(BaseExternalAgent):
    """
    Example implementation of a simple math agent to demonstrate usage.
    """
    
    def __init__(self):
        super().__init__(
            name="SimpleMathAgent",
            version="1.0.0",
            description="A simple agent that performs basic math operations"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "add", 
            description="Add two numbers", 
            parameters={
                "a": {"type": "number", "description": "First number", "required": True},
                "b": {"type": "number", "description": "Second number", "required": True}
            }
        )
        
        self.register_method(
            "multiply", 
            description="Multiply two numbers", 
            parameters={
                "a": {"type": "number", "description": "First number", "required": True},
                "b": {"type": "number", "description": "Second number", "required": True}
            }
        )
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self.logger.info(f"Calculated {a} + {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self.logger.info(f"Calculated {a} * {b} = {result}")
        return result


if __name__ == "__main__":
    # Example usage
    agent = SimpleMathAgent()
    agent.run()