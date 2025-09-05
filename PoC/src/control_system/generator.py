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
        with open(f"config_{description['name']}.json", "w") as f:
            json.dump(description, f, indent=2)
        return True
    return False