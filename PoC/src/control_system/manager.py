"""Manager component for the dynamic control system."""

from typing import List, Any


class ControlSystemManager:
    """Manages loaded agents and their configurations."""

    def __init__(self) -> None:
        """Initialize the control system manager."""
        self.agents: List[Any] = []

    def add_agent(self, agent: Any) -> None:
        """Add an agent to the manager.
        
        Args:
            agent (Agent): The agent to add.
        """
        self.agents.append(agent)

    def list_agents(self) -> List[str]:
        """List all loaded agents.
        
        Returns:
            list: A list of agent names.
        """
        return [agent.self_describe()["name"] for agent in self.agents]

    def register_all_configs(self) -> None:
        """Register all loaded agents (without auto-generating config files).
        
        This approach prevents duplication between code and config files.
        """
        print("Agents registered. Configuration files should be managed separately.")