"""Unit tests for Sample Agent B."""

import time
import pytest
from agents.sample_agent_b import SampleAgentB


def test_sample_agent_b_website_check():
    """Should perform website check successfully."""
    agent = SampleAgentB()
    result = agent.perform_website_check()
    assert result["status"] == "success"
    assert "status_code" in result


def test_sample_agent_b_website_check_with_delay():
    """Should perform website check with artificial delay."""
    agent = SampleAgentB()
    # Modify agent configuration to include delay
    original_describe = agent.self_describe
    def mock_describe():
        config = original_describe()
        config["response_controls"]["delay_ms"] = 100  # 100ms delay
        return config
    agent.self_describe = mock_describe
    
    start_time = time.time()
    result = agent.perform_website_check()
    elapsed_time = time.time() - start_time
    
    assert result["status"] == "success"
    assert elapsed_time >= 0.1  # Should take at least 100ms