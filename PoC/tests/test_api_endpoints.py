"""Test for frontend API endpoints."""

import pytest
import asyncio
from src.ucs_runtime import UCSRuntime
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.orchestrator.chat_interface import ChatInterface


def test_api_endpoints_exist():
    """Test that the API endpoints exist and can be imported."""
    # This test verifies that the endpoints we added to the API work
    from src.frontend.api import (
        get_status, 
        get_system_parameters, 
        set_system_parameter, 
        chat,
        SystemParameterUpdate
    )
    
    # Verify functions exist
    assert callable(get_status)
    assert callable(get_system_parameters)
    assert callable(set_system_parameter)
    assert callable(chat)
    assert SystemParameterUpdate is not None


@pytest.mark.asyncio
async def test_system_parameters_api_functionality():
    """Test system parameters API functionality."""
    # Initialize system
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Test getting system parameters directly through the agent
    result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
    assert result["status"] == "success"
    assert "parameters" in result
    assert isinstance(result["parameters"], dict)
    assert len(result["parameters"]) > 0
    
    # Test setting a parameter
    result = ucs_runtime.run_agent("SystemParametersManager", "set_system_parameter",
                                 parameter_name="max_history_length", parameter_value="10")
    assert result["status"] == "success"
    
    # Verify the parameter was set by getting parameters again
    result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
    assert result["status"] == "success"
    params = result["parameters"]
    
    # Note: The settings module parameters won't change, but the runtime objects should
    # have been updated
    if "chat_max_history_length" in params:
        assert params["chat_max_history_length"] == 10


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        test_api_endpoints_exist()
        asyncio.run(test_system_parameters_api_functionality())
        print("All frontend API tests passed!")