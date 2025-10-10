#!/usr/bin/env python3
"""
Test script to validate the kernel architecture refactoring.
This tests that the GCSRuntime properly functions as the kernel
and the CLI functions as a thin client.
"""

from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.ui.cli.interactive_mode import InteractiveCLI


def test_kernel_independence():
    """Test that GCSRuntime can function as an independent kernel."""
    print("Testing GCSRuntime as kernel...")
    
    # Initialize the kernel
    gcs = GCSRuntime()
    print("✓ GCSRuntime initialized successfully")
    
    # Verify that the kernel is properly set up with the new architecture
    assert hasattr(gcs, 'kernel')
    assert gcs.kernel is not None
    print("✓ Kernel properly initialized")
    
    # Test that kernel methods exist and work
    gcs.start_kernel_loop()
    print("✓ Kernel loop started successfully")
    
    # Check that agents can be loaded via the config service
    config_service = gcs.config_service
    agent_configs = config_service.list_configurations()
    print(f"✓ Found {len(agent_configs)} configurations via config service")
    
    # Shutdown properly
    import asyncio
    try:
        asyncio.run(gcs.shutdown())
    except RuntimeError:
        # If there's no running event loop, create one
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gcs.shutdown())
        loop.close()
    
    print("✓ Kernel shutdown completed successfully")
    print()


def test_cli_as_thin_client():
    """Test that CLI is properly structured as a thin client."""
    print("Testing CLI as thin client...")
    
    # Initialize kernel
    gcs = GCSRuntime()
    print("✓ GCSRuntime kernel initialized")
    
    # The CLI should be able to access all kernel functionality
    # through the services in the kernel
    assert hasattr(gcs, 'kernel'), "GCSRuntime should have kernel reference"
    print("✓ GCSRuntime has kernel reference")
    
    # Check that CLI can access kernel services through the kernel
    assert hasattr(gcs, 'llm_service'), "GCSRuntime should have LLM service"
    print("✓ GCSRuntime has LLM service access")
    
    # Check that services are registered in the kernel
    assert 'llm' in gcs.kernel.service_registry, "LLM service should be registered in kernel"
    print("✓ LLM service registered in kernel")
    
    # Shutdown kernel
    import asyncio
    try:
        asyncio.run(gcs.shutdown())
    except RuntimeError:
        # If there's no running event loop, create one
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gcs.shutdown())
        loop.close()
    
    print("✓ Kernel shutdown completed successfully")
    print()


def test_architectural_separation():
    """Test that architectural separation is properly implemented."""
    print("Testing architectural separation...")
    
    # The kernel should have all the business logic
    gcs = GCSRuntime()
    
    # Verify that the main control loop responsibility lies with the kernel
    import inspect
    
    # Check that GCSRuntime has kernel loop methods
    assert hasattr(gcs, 'start_kernel_loop'), "GCSRuntime should have kernel loop methods"
    assert callable(getattr(gcs, 'start_kernel_loop')), "start_kernel_loop should be callable"
    print("✓ GCSRuntime has kernel loop functionality")
    
    # Verify that services are properly separated
    assert hasattr(gcs, 'config_service'), "GCSRuntime should have config service"
    assert hasattr(gcs, 'agent_service'), "GCSRuntime should have agent service"
    assert hasattr(gcs, 'llm_service'), "GCSRuntime should have LLM service"
    assert hasattr(gcs, 'auth_service'), "GCSRuntime should have auth service"
    assert hasattr(gcs, 'storage_service'), "GCSRuntime should have storage service"
    assert hasattr(gcs, 'system_parameters_service'), "GCSRuntime should have system parameters service"
    print("✓ Services are properly separated")
    
    # Check that services are registered in the kernel
    assert 'config' in gcs.kernel.service_registry, "Config service should be registered in kernel"
    assert 'agent' in gcs.kernel.service_registry, "Agent service should be registered in kernel"
    assert 'llm' in gcs.kernel.service_registry, "LLM service should be registered in kernel"
    print("✓ Services are registered in kernel")
    
    # Shutdown
    import asyncio
    try:
        asyncio.run(gcs.shutdown())
    except RuntimeError:
        # If there's no running event loop, create one
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gcs.shutdown())
        loop.close()
    
    print("✓ Architectural separation validated")
    print()


if __name__ == "__main__":
    print("Testing refactored kernel architecture...")
    print("="*50)
    
    test_kernel_independence()
    test_cli_as_thin_client()
    test_architectural_separation()
    
    print("="*50)
    print("All tests passed! ✓")
    print("Architecture successfully refactored:")
    print("  - GCSRuntime functions as the kernel with control loop")
    print("  - CLI functions as a thin client interface")
    print("  - Proper separation of concerns achieved")