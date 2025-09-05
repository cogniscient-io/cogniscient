"""Unit tests for the generator component."""

import os
import pytest
from agents.sample_agent_a import SampleAgentA
from control_system.generator import generate_agent_config


def test_generate_agent_config():
    """Should generate valid JSON configuration file."""
    agent = SampleAgentA()
    assert generate_agent_config(agent) == True
    # Check that file was created
    assert os.path.exists("config_SampleAgentA.json")
    
    # Clean up
    if os.path.exists("config_SampleAgentA.json"):
        os.remove("config_SampleAgentA.json")