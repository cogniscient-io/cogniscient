"""Unit tests for the loader component."""

import os
import tempfile
from cogniscient.engine.agent_utils.loader import load_agent_module


def test_load_agent_module():
    """Should dynamically load an agent module."""
    # Create a temporary Python file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def hello():
    return "Hello, World!"
""")
        temp_path = f.name

    try:
        # Load the module
        module = load_agent_module("test_module", temp_path)
        
        # Verify the module was loaded correctly
        assert hasattr(module, "hello")
        assert module.hello() == "Hello, World!"
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)