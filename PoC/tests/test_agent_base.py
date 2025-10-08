"""Unit tests for the agent base class."""

from cogniscient.engine.agent_utils.base_agent import Agent


def test_agent_base_class():
    """Should define an abstract base class for agents."""
    # This test primarily ensures the module can be imported
    # and the abstract base class exists
    assert Agent.__name__ == "Agent"