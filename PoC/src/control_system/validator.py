"""Validator component for the dynamic control system."""

import json
import jsonschema
from jsonschema import validate
from typing import Dict, Any


def load_schema() -> Dict[str, Any]:
    """Load the JSON schema for agent configurations.
    
    Returns:
        dict: The JSON schema.
    """
    with open("src/config/agent_schema.json", "r") as f:
        return json.load(f)


def validate_agent_config(config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate an agent configuration against the schema.
    
    Args:
        config (dict): The agent configuration to validate.
        schema (dict): The JSON schema to validate against.
        
    Returns:
        bool: True if the configuration is valid, False otherwise.
    """
    try:
        validate(instance=config, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"Configuration is invalid: {e}")
        return False