"""Unit tests for the manager component."""

import pytest
from control_system.manager import ControlSystemManager
from agents.sample_agent_a import SampleAgentA
from agents.sample_agent_b import SampleAgentB


def test_add_agent():
    """Should add agent to manager."""
    manager = ControlSystemManager()
    agent = SampleAgentA()
    manager.add_agent(agent)
    assert len(manager.agents) == 1


def test_list_agents():
    """Should list all added agents."""
    manager = ControlSystemManager()
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    assert len(manager.list_agents()) == 2