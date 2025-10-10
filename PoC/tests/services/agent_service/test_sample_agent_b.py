"""Unit tests for Sample Agent B."""

from plugins.sample_internal.agents.sample_agent_b import SampleAgentB


def test_sample_agent_b_self_describe():
    """Should return a valid self-description."""
    agent = SampleAgentB()
    description = agent.self_describe()
    
    assert "name" in description
    assert "version" in description
    assert "enabled" in description
    assert description["name"] == "SampleAgentB"
    assert description["version"] == "1.0"
    assert description["enabled"] is True


def test_sample_agent_b_perform_website_check():
    """Should perform a website check."""
    agent = SampleAgentB()
    result = agent.perform_website_check()
    
    assert "status" in result
    assert result["status"] in ["success", "error"]