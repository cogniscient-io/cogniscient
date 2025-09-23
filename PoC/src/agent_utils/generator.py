"""Generator component for the dynamic control system.

Note: This module no longer auto-generates configuration files to prevent
duplication with configuration stored in JSON files. It's kept for potential
future use or development tools.
"""

import json
from typing import Any
from agent_utils.validator import validate_agent_config, load_schema


def generate_agent_config(agent: Any) -> bool:
    """Report agent configuration (without generating files).
    
    Args:
        agent (Agent): The agent to report configuration for.
        
    Returns:
        bool: True if the configuration is valid, False otherwise.
    """
    description = agent.self_describe()
    schema = load_schema()
    
    # Validate the configuration against schema
    if validate_agent_config(description, schema):
        # No longer auto-generate files to prevent duplication
        print(f"Note: Configuration for {description['name']} exists in code but JSON file should be maintained separately.")
        return True
    else:
        print(f"Configuration for {description['name']} does not match schema.")
        return False