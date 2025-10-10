"""
Utility functions for the Cogniscient CLI.
"""
import re
from typing import Dict, Any
from cogniscient.engine.gcs_runtime import GCSRuntime

def extract_entities(text: str, gcs_runtime: GCSRuntime) -> Dict[str, Any]:
    """
    Extract entities from natural language text.
    
    Args:
        text: Input text to extract entities from
        gcs_runtime: GCS runtime instance for context
        
    Returns:
        Dictionary containing extracted entities
    """
    entities = {}
    
    # Detect configuration names based on available configurations
    configs = gcs_runtime.list_available_configurations()
    for config in configs:
        if config.lower() in text.lower():
            entities["configuration"] = config
            break
            
    # Detect agent names based on available agents
    for agent_name in gcs_runtime.agents:
        if agent_name.lower() in text.lower():
            entities["agent"] = agent_name
    
    # Detect method names (for agent methods)
    # Common method patterns
    method_indicators = [
        r"run (\w+)",  # "run" agent method
        r"execute (\w+)",  # "execute" agent method
        r"call (\w+)",  # "call" agent method
    ]
    
    for pattern in method_indicators:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities["method"] = match.group(1)
            break
    
    return entities

def identify_intent(text: str) -> str:
    """
    Identify the intent from the user's text.
    
    Args:
        text: Input text to identify intent from
        
    Returns:
        String representing the identified intent
    """
    # Convert to lowercase for easier matching
    text_lower = text.lower().strip()
    
    # Define intent patterns
    intent_patterns = {
        "list_configs": [
            r"what.*config", r"list.*config", r"show.*config", 
            r"available.*config", r"configuration.*available"
        ],
        "list_agents": [
            r"what.*agent", r"list.*agent", r"show.*agent", 
            r"available.*agent", r"agent.*available"
        ],
        "run_agent": [
            r"run.*agent", r"execute.*agent", r"call.*agent",
            r"start.*agent", r"use.*agent"
        ],
        "help": [
            r"what.*can.*do", r"help", r"how.*do", r"show.*help",
            r"what.*available", r"options"
        ],
        "status": [
            r"status", r"check.*status", r"is.*running"
        ],
        "load_config": [
            r"load.*config", r"use.*config", r"switch.*config"
        ]
    }
    
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return intent
                
    # If no specific intent matched, return "natural_language" for further processing
    return "natural_language"