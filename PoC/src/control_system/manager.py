"""Manager component for the dynamic control system."""

from typing import List, Any
from control_system.generator import generate_agent_config


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

    def generate_all_configs(self) -> None:
        """Generate configuration files for all loaded agents."""
        for agent in self.agents:
            generate_agent_config(agent)