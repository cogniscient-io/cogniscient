"""Unit tests for the loader component."""

import pytest
from control_system.loader import load_agent_module


def test_load_agent_module():
    """Should successfully load an agent module."""
    module = load_agent_module("sample_agent_a", "src/agents/sample_agent_a.py")
    assert hasattr(module, "SampleAgentA")


def test_load_nonexistent_module():
    """Should raise ImportError for nonexistent module."""
    with pytest.raises(ImportError):
        load_agent_module("nonexistent", "nonexistent.py")