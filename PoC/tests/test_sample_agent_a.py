"""Unit tests for Sample Agent A."""

import time
import pytest
from agents.sample_agent_a import SampleAgentA


def test_sample_agent_a_dns_lookup():
    """Should perform DNS lookup successfully."""
    agent = SampleAgentA()
    result = agent.perform_dns_lookup()
    assert result["status"] == "success"
    assert "addresses" in result


def test_sample_agent_a_dns_lookup_with_delay():
    """Should perform DNS lookup with artificial delay."""
    agent = SampleAgentA()
    # Modify agent configuration to include delay
    original_describe = agent.self_describe
    def mock_describe():
        config = original_describe()
        config["response_controls"]["delay_ms"] = 100  # 100ms delay
        return config
    agent.self_describe = mock_describe
    
    start_time = time.time()
    result = agent.perform_dns_lookup()
    elapsed_time = time.time() - start_time
    
    assert result["status"] == "success"
    assert elapsed_time >= 0.1  # Should take at least 100ms