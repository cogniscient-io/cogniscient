"""Unit tests for the generator component."""

import os
from agents.sample_agent_a import SampleAgentA
from agent_utils.generator import generate_agent_config


def test_generate_agent_config():
    """Should generate valid JSON configuration file."""
    agent = SampleAgentA()
    assert generate_agent_config(agent)
    # Check that file was created
    assert os.path.exists("config_SampleAgentA.json")
    
    # Clean up
    if os.path.exists("config_SampleAgentA.json"):
        os.remove("config_SampleAgentA.json")