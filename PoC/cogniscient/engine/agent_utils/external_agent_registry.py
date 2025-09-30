"""Registry for external agents."""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from cogniscient.engine.agent_utils.external_agent_adapter import ExternalAgentAdapter


class ExternalAgentRegistry:
    """Handles registration, storage, and management of external agents."""

    def __init__(self, registry_file: str = None, runtime_data_dir: str = None):
        """Initialize the external agent registry.
        
        Args:
            registry_file: Path to the file where external agent configurations are stored
            runtime_data_dir: Directory where runtime data files are stored
        """
        import os
        from cogniscient.engine.config.settings import settings
        
        # Determine the runtime data directory
        if runtime_data_dir is None:
            # Use the settings directory if available
            runtime_data_dir = getattr(settings, 'runtime_data_dir', 'runtime_data')
        
        # Ensure the runtime data directory exists
        os.makedirs(runtime_data_dir, exist_ok=True)
        
        # If no specific registry file provided, use default in runtime data dir
        if registry_file is None:
            self.registry_file = os.path.join(runtime_data_dir, "external_agents_registry.json")
        else:
            self.registry_file = registry_file
        self.agents: Dict[str, ExternalAgentAdapter] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task = None
        self._running = False
        
        # Load existing agent configurations from file
        self.load_registry()
    
    def register_agent(self, agent_config: Dict[str, Any]) -> bool:
        """Register a new external agent.
        
        Args:
            agent_config: Configuration for the external agent
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        # Validate the configuration
        if not self._validate_agent_config(agent_config):
            return False
        
        agent_name = agent_config["name"]
        
        # Check if agent with this name already exists
        if agent_name in self.agents:
            print(f"Agent {agent_name} already registered, deregistering first")
            self.deregister_agent(agent_name)
        
        try:
            # Create and store the agent adapter
            agent_adapter = ExternalAgentAdapter(agent_config)
            self.agents[agent_name] = agent_adapter
            self.agent_configs[agent_name] = agent_config.copy()
            
            # Save to registry file
            self.save_registry()
            
            print(f"Successfully registered external agent: {agent_name}")
            return True
        except Exception as e:
            print(f"Failed to register external agent {agent_name}: {e}")
            return False
    
    def deregister_agent(self, agent_name: str) -> bool:
        """Deregister an external agent.
        
        Args:
            agent_name: Name of the agent to deregister
            
        Returns:
            bool: True if deregistration was successful, False otherwise
        """
        if agent_name not in self.agents:
            print(f"Agent {agent_name} not found in registry")
            return False
        
        try:
            # Close the agent adapter
            agent_adapter = self.agents[agent_name]
            agent_adapter.shutdown()
            
            # Remove from registries
            del self.agents[agent_name]
            del self.agent_configs[agent_name]
            
            # Save to registry file
            self.save_registry()
            
            print(f"Successfully deregistered external agent: {agent_name}")
            return True
        except Exception as e:
            print(f"Failed to deregister external agent {agent_name}: {e}")
            return False
    
    def get_agent(self, agent_name: str) -> Optional[ExternalAgentAdapter]:
        """Get an external agent by name.
        
        Args:
            agent_name: Name of the agent to retrieve
            
        Returns:
            The external agent adapter or None if not found
        """
        return self.agents.get(agent_name)
    
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for an external agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            The agent configuration or None if not found
        """
        return self.agent_configs.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all registered external agents.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def _validate_agent_config(self, agent_config: Dict[str, Any]) -> bool:
        """Validate the agent configuration.
        
        Args:
            agent_config: Configuration to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["name", "version", "endpoint_url", "methods"]
        for field in required_fields:
            if field not in agent_config:
                print(f"Missing required field: {field}")
                return False
        
        # Validate endpoint URL
        endpoint_url = agent_config["endpoint_url"]
        if not isinstance(endpoint_url, str) or not endpoint_url.startswith(("http://", "https://")):
            print(f"Invalid endpoint URL: {endpoint_url}")
            return False
        
        # Validate methods structure
        methods = agent_config["methods"]
        if not isinstance(methods, dict):
            print("Methods must be a dictionary")
            return False
        
        # Validate authentication if provided
        if "authentication" in agent_config:
            auth = agent_config["authentication"]
            if not isinstance(auth, dict):
                print("Authentication must be a dictionary")
                return False
            
            auth_type = auth.get("type")
            if auth_type not in ["api_key", "bearer", None]:
                print(f"Invalid authentication type: {auth_type}")
                return False
            
            if auth_type == "api_key" and "api_key" not in auth:
                print("API key authentication requires 'api_key' field")
                return False
            
            if auth_type == "bearer" and "token" not in auth:
                print("Bearer authentication requires 'token' field")
                return False
        
        return True
    
    def save_registry(self):
        """Save the current registry to the registry file."""
        try:
            # Write agent configs to registry file
            with open(self.registry_file, "w") as f:
                json.dump(self.agent_configs, f, indent=2)
        except Exception as e:
            print(f"Failed to save registry to {self.registry_file}: {e}")
    
    def load_registry(self):
        """Load the registry from the registry file."""
        registry_path = Path(self.registry_file)
        if not registry_path.exists():
            # Create an empty registry file if it doesn't exist
            with open(self.registry_file, "w") as f:
                json.dump({}, f)
            return
        
        try:
            with open(self.registry_file, "r") as f:
                self.agent_configs = json.load(f)
            
            # Reconstruct agent adapters from configurations
            for name, config in self.agent_configs.items():
                try:
                    agent_adapter = ExternalAgentAdapter(config)
                    self.agents[name] = agent_adapter
                except Exception as e:
                    print(f"Failed to reconstruct agent {name}: {e}")
                    # Remove the agent from the registry if it can't be reconstructed
                    del self.agent_configs[name]
        except Exception as e:
            print(f"Failed to load registry from {self.registry_file}: {e}")
    
    async def validate_agent_endpoint(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the external agent endpoint is accessible and responsive.
        
        Args:
            agent_config: Configuration of the agent to validate
            
        Returns:
            Dict containing validation results
        """
        endpoint_url = agent_config["endpoint_url"]
        
        try:
            # Create a temporary client with the agent's configuration
            client_kwargs = {}
            
            # Set up authentication
            if "authentication" in agent_config:
                auth_config = agent_config["authentication"]
                if auth_config.get("type") == "api_key":
                    header_name = auth_config.get("header_name", "X-API-Key")
                    header_value = auth_config["api_key"]
                    client_kwargs["headers"] = {header_name: header_value}
                elif auth_config.get("type") == "bearer":
                    client_kwargs["headers"] = {"Authorization": f"Bearer {auth_config['token']}"}
            
            # Set timeout
            timeout = agent_config.get("settings", {}).get("timeout", 10)
            client_kwargs["timeout"] = httpx.Timeout(timeout)
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                # Test the health check endpoint if provided
                health_url = agent_config.get("health_check_url", endpoint_url)
                
                response = await client.get(health_url)
                response.raise_for_status()
                
                # If we get here, the agent is accessible
                return {
                    "status": "success",
                    "message": "Agent endpoint is accessible and responsive",
                    "health_data": response.json() if response.content else {}
                }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": "Agent endpoint validation timed out"
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error", 
                "message": f"Agent endpoint returned error {e.response.status_code}: {e.response.text}"
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "message": f"Unable to reach agent endpoint: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error during agent validation: {str(e)}"
            }
    
    def set_health_check_interval(self, interval: int):
        """Set the interval for health checks.
        
        Args:
            interval: Interval in seconds between health checks
        """
        self._health_check_interval = interval
    
    async def start_health_checks(self):
        """Start periodic health checks for all registered agents."""
        if self._running:
            return
        
        self._running = True
        
        # Run health checks in the background
        self._health_check_task = asyncio.create_task(self._run_health_checks())
    
    async def stop_health_checks(self):
        """Stop periodic health checks."""
        if not self._running:
            return
        
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling the task
            self._health_check_task = None
    
    async def _run_health_checks(self):
        """Run periodic health checks for all registered agents."""
        while self._running:
            agents_to_remove = []
            
            for name, agent in self.agents.items():
                try:
                    health_result = await self.validate_agent_endpoint(agent.config)
                    
                    # Update health status in the agent's config
                    agent_config = self.agent_configs[name]
                    agent_config["health_status"] = health_result["status"]
                    agent_config["last_health_check"] = asyncio.get_event_loop().time()
                    
                    # Consider removing unhealthy agents (optional)
                    if health_result["status"] == "error":
                        print(f"Agent {name} is unhealthy: {health_result['message']}")
                        
                        # Optionally remove agents that have been unhealthy for a long time
                        # This is a simplified check - in practice, you might want more sophisticated logic
                        if agent_config.get("unhealthy_count", 0) > 5:
                            agents_to_remove.append(name)
                        else:
                            agent_config["unhealthy_count"] = agent_config.get("unhealthy_count", 0) + 1
                    else:
                        # Reset unhealthy count on successful health check
                        agent_config["unhealthy_count"] = 0
                except Exception as e:
                    # Update health status to reflect the error
                    agent_config = self.agent_configs[name]
                    agent_config["health_status"] = "error"
                    agent_config["health_status_error"] = str(e)
            
            # Remove unhealthy agents if any were identified
            for name in agents_to_remove:
                try:
                    agent_adapter = self.agents[name]
                    agent_adapter.shutdown()
                    del self.agents[name]
                    del self.agent_configs[name]
                    print(f"Removed unhealthy agent: {name}")
                except Exception as e:
                    print(f"Error removing unhealthy agent {name}: {e}")
            
            # Update the registry file after health checks
            self.save_registry()
            
            # Wait for the specified interval before the next health check
            await asyncio.sleep(self._health_check_interval)
    
    async def get_agent_health(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the health status of an external agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Health status information or None if agent not found
        """
        if agent_name not in self.agent_configs:
            return None
        
        agent_config = self.agent_configs[agent_name]
        return {
            "name": agent_name,
            "health_status": agent_config.get("health_status", "unknown"),
            "last_health_check": agent_config.get("last_health_check"),
            "unhealthy_count": agent_config.get("unhealthy_count", 0),
            "health_status_error": agent_config.get("health_status_error")
        }