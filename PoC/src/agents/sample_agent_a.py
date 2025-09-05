"""Sample agent A implementation."""

from agents.base import Agent


class SampleAgentA(Agent):
    """Sample agent A implementation."""

    def self_describe(self):
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration.
        """
        return {
            "name": "SampleAgentA",
            "version": "1.0",
            "enabled": True,
            "settings": {
                "timeout": 30,
                "retries": 3
            }
        }