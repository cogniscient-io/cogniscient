"""Base agent class for the dynamic control system."""

from abc import ABC, abstractmethod


class Agent(ABC):
    """Abstract base class for all agents in the control system."""

    @abstractmethod
    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration.
        """
        pass