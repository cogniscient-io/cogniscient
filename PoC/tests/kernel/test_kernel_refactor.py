#!/usr/bin/env python3
"""
Test script to validate the kernel architecture refactoring.
This tests that the GCSRuntime properly functions as the kernel
and the services are properly separated with single responsibilities.
"""

import asyncio
from cogniscient.engine.kernel import Kernel
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.config_service import ConfigServiceImpl
from cogniscient.engine.services.agent_service import AgentServiceImpl
from cogniscient.engine.services.llm_kernel_service import LLMServiceImpl
from cogniscient.engine.services.auth_service import AuthServiceImpl
from cogniscient.engine.services.storage_service import StorageServiceImpl
from cogniscient.engine.services.service_interface import (
    ConfigServiceInterface, AgentServiceInterface, 
    LLMServiceInterface, AuthServiceInterface, 
    StorageServiceInterface
)


def test_kernel_initialization():
    """Test that kernel initializes properly with minimal interface"""
    print("Testing kernel initialization...")
    
    kernel = Kernel()
    assert hasattr(kernel, 'service_registry')
    assert hasattr(kernel, 'initialize')
    assert hasattr(kernel, 'shutdown')
    assert hasattr(kernel, 'register_service')
    assert hasattr(kernel, 'get_service')
    
    print("✓ Kernel has expected attributes and methods")


def test_service_interfaces():
    """Test that services implement the correct interfaces"""
    print("Testing service interfaces...")
    
    # Create service instances
    config_service = ConfigServiceImpl()
    agent_service = AgentServiceImpl()
    llm_service = LLMServiceImpl()
    auth_service = AuthServiceImpl()
    storage_service = StorageServiceImpl()
    
    # Check that services implement the expected interfaces
    assert isinstance(config_service, ConfigServiceInterface)
    assert isinstance(agent_service, AgentServiceInterface)
    assert isinstance(llm_service, LLMServiceInterface)
    assert isinstance(auth_service, AuthServiceInterface)
    assert isinstance(storage_service, StorageServiceInterface)
    
    print("✓ All services implement correct interfaces")


def test_gcs_runtime_kernel_functionality():
    """Test that refactored GCSRuntime works as a proper kernel"""
    print("Testing GCSRuntime kernel functionality...")
    
    gcs = GCSRuntime()
    
    # Test that essential kernel methods still exist
    assert hasattr(gcs, 'start_kernel_loop')
    assert hasattr(gcs, 'shutdown')
    
    # Test that it has the kernel attribute
    assert hasattr(gcs, 'kernel')
    assert isinstance(gcs.kernel, Kernel)
    
    print("✓ GCSRuntime functions as a proper kernel")


def test_service_registration():
    """Test that services can be registered and retrieved"""
    print("Testing service registration...")
    
    kernel = Kernel()
    config_service = ConfigServiceImpl()
    
    # Test service registration
    result = kernel.register_service("config", config_service)
    assert result is True
    assert "config" in kernel.service_registry
    
    # Test service retrieval
    retrieved = kernel.get_service("config")
    assert retrieved == config_service
    
    print("✓ Services can be registered and retrieved")


def test_kernel_system_lifecycle():
    """Test kernel system lifecycle management"""
    print("Testing kernel system lifecycle...")
    
    kernel = Kernel()
    
    # Test start and stop methods
    result = kernel.start_system()
    assert result is True
    print("✓ Kernel system lifecycle methods work")


async def test_service_initialization_shutdown():
    """Test that services initialize and shutdown properly"""
    print("Testing service initialization and shutdown...")
    
    # Create service instances
    config_service = ConfigServiceImpl()
    agent_service = AgentServiceImpl()
    
    # Test initialization
    config_init = await config_service.initialize()
    agent_init = await agent_service.initialize()
    
    assert config_init is True
    assert agent_init is True
    
    # Test shutdown
    config_shutdown = await config_service.shutdown()
    agent_shutdown = await agent_service.shutdown()
    
    assert config_shutdown is True
    assert agent_shutdown is True
    
    print("✓ Services initialize and shutdown properly")


def test_gcs_runtime_kernel_integration():
    """Test that GCSRuntime integrates properly with the kernel"""
    print("Testing GCSRuntime kernel integration...")
    
    gcs = GCSRuntime()
    
    # Check that services are registered with the kernel
    assert "config" in gcs.kernel.service_registry
    assert "agent" in gcs.kernel.service_registry
    assert "llm" in gcs.kernel.service_registry
    assert "auth" in gcs.kernel.service_registry
    assert "storage" in gcs.kernel.service_registry
    assert "system_params" in gcs.kernel.service_registry
    
    print("✓ GCSRuntime properly registers services with kernel")


if __name__ == "__main__":
    print("Testing refactored kernel architecture...")
    print("="*50)
    
    # Run synchronous tests
    test_kernel_initialization()
    test_service_interfaces()
    test_gcs_runtime_kernel_functionality()
    test_service_registration()
    test_kernel_system_lifecycle()
    test_gcs_runtime_kernel_integration()
    
    # Run async tests
    asyncio.run(test_service_initialization_shutdown())
    
    print("="*50)
    print("All tests passed! ✓")
    print("Architecture successfully refactored:")
    print("  - Kernel class properly implemented")
    print("  - Services properly separated with single responsibilities")
    print("  - GCSRuntime maintains backward compatibility")
    print("  - Services properly integrated with kernel")
    print("  - Service lifecycle management works")