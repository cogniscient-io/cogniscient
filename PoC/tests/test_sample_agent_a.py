"""Unit tests for Sample Agent A."""

from plugins.sample.agents.sample_agent_a import SampleAgentA


def test_sample_agent_a_self_describe():
    """Should return a valid self-description."""
    agent = SampleAgentA()
    description = agent.self_describe()
    
    assert "name" in description
    assert "version" in description
    assert "enabled" in description
    assert description["name"] == "SampleAgentA"
    assert description["version"] == "1.0"
    assert description["enabled"] is True


def test_sample_agent_a_perform_dns_lookup():
    """Should perform a DNS lookup."""
    agent = SampleAgentA()
    result = agent.perform_dns_lookup()
    
    assert "status" in result
    assert result["status"] in ["success", "error"]