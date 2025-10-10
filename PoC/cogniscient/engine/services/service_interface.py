"""Base service interface definitions for the ringed architecture."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Service(ABC):
    """Base interface for all services in the ringed architecture."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the service."""
        pass


class ConfigServiceInterface(Service):
    """Service interface for configuration management."""
    
    @abstractmethod
    async def load_configuration(self, config_name: str) -> Dict[str, Any]:
        """Load a specific configuration."""
        pass
    
    @abstractmethod
    def list_configurations(self) -> List[str]:
        """List all available configurations."""
        pass
    
    @abstractmethod
    def update_config_dir(self, config_dir: str) -> None:
        """Update the configuration directory."""
        pass


class AgentServiceInterface(Service):
    """Service interface for agent lifecycle management."""
    
    @abstractmethod
    async def load_agent(self, agent_name: str) -> Any:
        """Load an agent by name."""
        pass
    
    @abstractmethod
    async def unload_agent(self, agent_name: str) -> bool:
        """Unload an agent by name."""
        pass
    
    @abstractmethod
    async def run_agent_method(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Execute a method on an agent."""
        pass


class LLMServiceInterface(Service):
    """Service interface for LLM provider abstraction."""
    
    @abstractmethod
    async def generate_response(self, prompt: str, domain: str = "general") -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def set_provider(self, provider_name: str) -> None:
        """Set the LLM provider."""
        pass


class AuthServiceInterface(Service):
    """Service interface for authentication and authorization."""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate a user."""
        pass
    
    @abstractmethod
    async def get_token(self) -> Optional[str]:
        """Get an authentication token."""
        pass


class StorageServiceInterface(Service):
    """Service interface for data persistence."""
    
    @abstractmethod
    async def save_data(self, key: str, data: Any) -> bool:
        """Save data to storage."""
        pass
    
    @abstractmethod
    async def load_data(self, key: str) -> Optional[Any]:
        """Load data from storage."""
        pass