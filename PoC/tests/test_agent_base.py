"""Unit tests for the base agent class."""

import pytest
from agents.base import Agent


def test_agent_base_cannot_be_instantiated():
    """Abstract base class cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Agent()