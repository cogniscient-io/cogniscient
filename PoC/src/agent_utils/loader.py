"""Loader component for the dynamic control system."""

import importlib.util
from typing import Any


def load_agent_module(name: str, path: str) -> Any:
    """Dynamically load an agent module from a file path.
    
    Args:
        name (str): The name to give the module.
        path (str): The file path to the module.
        
    Returns:
        module: The loaded module.
        
    Raises:
        ImportError: If the module cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise ImportError(f"Could not load spec for {name}")
    
    module = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(module)
    return module