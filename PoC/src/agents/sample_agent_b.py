"""Sample agent B implementation."""

from agents.base import Agent


class SampleAgentB(Agent):
    """Sample agent B implementation."""

    def self_describe(self):
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration.
        """
        return {
            "name": "SampleAgentB",
            "version": "1.0",
            "enabled": True,
            "settings": {
                "timeout": 60,
                "retries": 5
            }
        }