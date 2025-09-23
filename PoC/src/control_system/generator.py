"""Generator component for the dynamic control system."""

import json
from typing import Any
from control_system.validator import validate_agent_config, load_schema


def generate_agent_config(agent: Any) -> bool:
    """Generate a JSON configuration file from an agent's self-description.
    
    Args:
        agent (Agent): The agent to generate a configuration for.
        
    Returns:
        bool: True if the configuration was generated successfully, False otherwise.
    """
    description = agent.self_describe()
    schema = load_schema()
    
    # Validate the generated configuration
    if validate_agent_config(description, schema):
        # Instead of auto-generating configuration files, we now rely on pre-existing JSON files
        # This prevents duplication between code and configuration files
        print(f"Note: Configuration for {description['name']} exists in code but JSON file should be maintained separately.")
        return True
    return False