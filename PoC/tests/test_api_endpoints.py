"""Unit tests for API endpoints."""

import pytest
from cogniscient.engine.ucs_runtime import UCSRuntime
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.orchestrator.chat_interface import ChatInterface
from fastapi.testclient import TestClient
from frontend.api import (
    app
)


def test_api_endpoints_exist():
    """Test that the API endpoints exist and can be imported."""
    # This test verifies that the endpoints we added to the API work
    from frontend.api import (
        get_status,
        get_system_parameters,
        set_system_parameter,
        SystemParameterUpdate
    )
    
    # Verify functions exist
    assert callable(get_status)
    assert callable(get_system_parameters)
    assert callable(set_system_parameter)
    assert SystemParameterUpdate is not None


@pytest.mark.asyncio
async def test_system_parameters_api_functionality():
    """Test system parameters API functionality."""
    # Initialize system
    ucs_runtime = UCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    ucs_runtime.load_configuration("combined")
    
    # Test getting system parameters
    result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
    assert result["status"] == "success"
    assert "parameters" in result
    assert isinstance(result["parameters"], dict)
    assert len(result["parameters"]) > 0
    
    # Save original parameter value for cleanup
    original_max_history_length = result["parameters"].get("max_history_length")
    
    # Test setting a parameter
    result = ucs_runtime.run_agent("SystemParametersManager", "set_system_parameter",
                                 parameter_name="max_history_length", parameter_value="10")
    assert result["status"] == "success"
    
    # Verify the parameter was set by getting parameters again
    result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
    assert result["status"] == "success"
    params = result["parameters"]
    
    # Verify the parameter was set in the settings
    assert params["max_history_length"] == 10
    
    # Reset the parameter back to its original value to avoid affecting other tests
    if original_max_history_length is not None:
        ucs_runtime.run_agent("SystemParametersManager", "set_system_parameter", 
                             parameter_name="max_history_length", parameter_value=str(original_max_history_length))


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        test_api_endpoints_exist()
        asyncio.run(test_system_parameters_api_functionality())
        print("All frontend API tests passed!")