"""Unit tests for the manager component."""

from control_system.manager import ControlSystemManager
from agents.sample_agent_a import SampleAgentA
from agents.sample_agent_b import SampleAgentB


def test_add_agent():
    """Should add an agent to the manager."""
    manager = ControlSystemManager()
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    
    assert len(manager.agents) == 2


def test_list_agents():
    """Should list all loaded agents."""
    manager = ControlSystemManager()
    agent_a = SampleAgentA()
    agent_b = SampleAgentB()
    
    manager.add_agent(agent_a)
    manager.add_agent(agent_b)
    
    agent_names = manager.list_agents()
    assert "SampleAgentA" in agent_names
    assert "SampleAgentB" in agent_names
    assert len(agent_names) == 2