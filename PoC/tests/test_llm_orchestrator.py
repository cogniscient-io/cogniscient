"""Unit tests for LLM orchestrator functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.gcs_runtime import GCSRuntime


def test_llm_orchestrator_initialization():
    """Should initialize LLM orchestrator successfully."""
    gcs_runtime = GCSRuntime()
    orchestrator = LLMOrchestrator(gcs_runtime)
    assert orchestrator is not None
    assert orchestrator.gcs_runtime == gcs_runtime


@pytest.mark.asyncio
async def test_parameter_adaptation_within_range():
    """Should adapt parameters within acceptable ranges."""
    gcs_runtime = GCSRuntime()
    orchestrator = LLMOrchestrator(gcs_runtime)
    
    # Set up parameter ranges
    orchestrator.parameter_ranges = {
        "SampleAgentA": {
            "dns_settings.timeout": {"min": 1, "max": 30, "default": 5}
        }
    }
    
    # Set up test configuration
    gcs_runtime.agent_configs = {
        "SampleAgentA": {
            "name": "SampleAgentA",
            "version": "1.0",
            "enabled": True,
            "dns_settings": {
                "target_domain": "example.com",
                "dns_server": "8.8.8.8",
                "timeout": 5
            }
        }
    }
    
    # Test adaptation within range
    changes = {"dns_settings.timeout": 10}
    result = await orchestrator.adapt_parameters("SampleAgentA", changes)
    assert result
    assert gcs_runtime.agent_configs["SampleAgentA"]["dns_settings"]["timeout"] == 10


@pytest.mark.asyncio
async def test_approval_workflow_escalation():
    """Should escalate changes outside acceptable ranges for approval."""
    gcs_runtime = GCSRuntime()
    orchestrator = LLMOrchestrator(gcs_runtime)

    # Set up parameter ranges in the parameter adaptation module
    orchestrator.parameter_adaptation.parameter_ranges = {
        "SampleAgentA": {
            "dns_settings.timeout": {"min": 1, "max": 30, "default": 5}
        }
    }
    
    # Set up test configuration
    gcs_runtime.agent_configs = {
        "SampleAgentA": {
            "name": "SampleAgentA",
            "version": "1.0",
            "enabled": True,
            "dns_settings": {
                "target_domain": "example.com",
                "dns_server": "8.8.8.8",
                "timeout": 5
            }
        }
    }
    
    # Test escalation for out-of-range change
    changes = {"dns_settings.timeout": 50}  # Outside max range of 30
    result = await orchestrator.adapt_parameters("SampleAgentA", changes)
    # Should return False or trigger approval workflow
    assert not result  # Assuming approval workflow returns False initially


@pytest.mark.asyncio
async def test_is_within_range():
    """Should correctly check if parameter values are within range."""
    gcs_runtime = GCSRuntime()
    orchestrator = LLMOrchestrator(gcs_runtime)

    # Set up parameter ranges in the parameter adaptation module
    orchestrator.parameter_adaptation.parameter_ranges = {
        "SampleAgentA": {
            "dns_settings.timeout": {"min": 1, "max": 30, "default": 5}
        }
    }
    
    # Test values within range
    assert orchestrator.is_within_range("SampleAgentA", "dns_settings.timeout", 15)
    assert orchestrator.is_within_range("SampleAgentA", "dns_settings.timeout", 1)
    assert orchestrator.is_within_range("SampleAgentA", "dns_settings.timeout", 30)
    
    # Test values outside range
    assert not orchestrator.is_within_range("SampleAgentA", "dns_settings.timeout", 0)
    assert not orchestrator.is_within_range("SampleAgentA", "dns_settings.timeout", 31)


@pytest.mark.asyncio
async def test_orchestrate_agent():
    """Should orchestrate agent execution with LLM evaluation."""
    # Mock GCS runtime
    gcs_runtime = Mock()
    gcs_runtime.run_agent.return_value = {"status": "success", "data": "test"}
    gcs_runtime.agent_configs = {}
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    
    # Mock LLM service
    with patch.object(orchestrator.llm_service, 'generate_response', new=AsyncMock(return_value='{"decision": "continue"}')) as mock_generate:
        result = await orchestrator.orchestrate_agent("SampleAgentA", "perform_test")
        
        # Verify the agent was called
        gcs_runtime.run_agent.assert_called_once_with("SampleAgentA", "perform_test")
        
        # Verify LLM service was called
        mock_generate.assert_called_once()
        
        # Verify result structure
        assert "agent" in result
        assert "method" in result
        assert "result" in result
        assert "evaluation" in result
        assert result["agent"] == "SampleAgentA"
        assert result["method"] == "perform_test"
        assert result["result"] == {"status": "success", "data": "test"}