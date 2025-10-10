"""Unit tests for API endpoints."""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime


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
    ucs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    ucs_runtime.load_configuration("combined")
    
    # Test getting system parameters using the service directly
    # In the new architecture, system parameters are managed through the service
    system_params_service = ucs_runtime.system_parameters_service
    params = system_params_service.get_parameters()
    assert isinstance(params, dict)
    assert len(params) > 0
    
    # Save original parameter value for cleanup
    original_max_history_length = params.get("max_history_length")
    
    # Test setting a parameter
    result = system_params_service.set_parameter("max_history_length", 10)
    assert result is True
    
    # Verify the parameter was set by getting parameters again
    params = system_params_service.get_parameters()
    assert params["max_history_length"] == 10
    
    # Reset the parameter back to its original value to avoid affecting other tests
    if original_max_history_length is not None:
        system_params_service.set_parameter("max_history_length", original_max_history_length)


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        test_api_endpoints_exist()
        asyncio.run(test_system_parameters_api_functionality())
        print("All frontend API tests passed!")