"""External agent adapter that implements the Agent interface but calls remote endpoints."""

import asyncio
import json
from typing import Any, Dict, List
import httpx
from agents.base import Agent


class ExternalAgentAdapter(Agent):
    """Adapter for external agents that implements the Agent interface but calls remote endpoints."""

    def __init__(self, agent_config: Dict[str, Any]):
        """Initialize the external agent adapter.
        
        Args:
            agent_config: Configuration containing endpoint_url, methods, authentication, etc.
        """
        self.config = agent_config
        self.name = agent_config.get("name", "UnknownExternalAgent")
        self.session = None
        self._client_kwargs = {}
        
        # Set up authentication if provided
        if "authentication" in agent_config:
            auth_config = agent_config["authentication"]
            if auth_config.get("type") == "api_key":
                header_name = auth_config.get("header_name", "X-API-Key")
                header_value = auth_config["api_key"]
                self._client_kwargs["headers"] = {header_name: header_value}
            elif auth_config.get("type") == "bearer":
                self._client_kwargs["headers"] = {"Authorization": f"Bearer {auth_config['token']}"}
        
        # Set timeout
        timeout = agent_config.get("settings", {}).get("timeout", 30)
        self._client_kwargs["timeout"] = httpx.Timeout(timeout)
    
    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration and methods.
        """
        return self.config
    
    async def _make_request(self, method_name: str, *args, **kwargs):
        """Make an HTTP request to the external agent endpoint.
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
            
        Returns:
            The response from the external agent
        """
        if self.session is None:
            self.session = httpx.AsyncClient(**self._client_kwargs)
        
        # Construct the endpoint URL
        base_url = self.config["endpoint_url"]
        endpoint = f"{base_url.rstrip('/')}/{method_name.lstrip('/')}"
        
        # Prepare the request data
        request_data = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs
        }
        
        try:
            response = await self.session.post(
                endpoint,
                json=request_data,
                headers=self._client_kwargs.get("headers", {})
            )
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            # Parse and return the response
            return response.json()
        except httpx.TimeoutException:
            return {"status": "error", "message": "Request timed out"}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            return {"status": "error", "message": f"Request error: {str(e)}"}
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON response from external agent"}
    
    def __getattr__(self, name: str):
        """Dynamically create methods that call the external agent endpoint.
        
        Args:
            name: Name of the method to call
            
        Returns:
            A function that makes the appropriate call to the external agent
        """
        # Check if this method is defined in the agent's configuration
        methods = self.config.get("methods", {})
        if name not in methods:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
        async def method_caller(*args, **kwargs):
            return await self._make_request(name, *args, **kwargs)
        
        return method_caller
    
    async def close(self):
        """Close the HTTP client session."""
        if self.session:
            await self.session.aclose()
            self.session = None
    
    def shutdown(self):
        """Synchronous shutdown method that can be called from sync context."""
        # If we're in an event loop, use create_task, otherwise run directly
        try:
            loop = asyncio.get_running_loop()
            # If we're inside an event loop, schedule the async close
            task = loop.create_task(self.close())
            # Mark the task to prevent warnings about unawaited coroutines
            task.add_done_callback(lambda f: f.result())
        except RuntimeError:
            # No event loop running, run the async close in a new event loop
            import asyncio as ai
            ai.run(self.close())