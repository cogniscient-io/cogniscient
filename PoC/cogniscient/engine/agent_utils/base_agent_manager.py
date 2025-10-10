"""
Simplified base agent manager interfaces for MCP-compliant system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAgentManager(ABC):
    """Simplified base class for all agent managers, MCP-first design."""
    
    @abstractmethod
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name."""
        pass
    
    @abstractmethod
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all loaded agents."""
        pass
    
    @abstractmethod
    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent."""
        pass