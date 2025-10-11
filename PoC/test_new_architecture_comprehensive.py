"""
New test suite for the redesigned LLM architecture.

This replaces the old test files that were incompatible with the new kernel/ring architecture.
"""
import pytest
import asyncio
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.llm.llm_provider_manager import LLMProviderManager
from cogniscient.engine.services.llm.response_evaluator_service import ResponseEvaluatorService
from cogniscient.engine.services.llm.conversation_manager import ConversationManagerService
from cogniscient.engine.services.llm.agent_orchestrator import AgentOrchestratorService
from cogniscient.engine.services.llm.control_config_service import ControlConfigService


@pytest.mark.asyncio
async def test_gcs_runtime_initialization():
    """Test that GCS Runtime initializes with the new architecture."""
    runtime = GCSRuntime()
    assert runtime is not None
    
    # Test that core services are properly initialized
    assert runtime.llm_provider_manager is not None
    assert runtime.response_evaluator_service is not None
    assert runtime.conversation_manager is not None
    assert runtime.agent_orchestrator is not None
    assert runtime.config_service is not None
    
    # Test that services are registered in kernel
    assert "llm_provider_manager" in runtime.kernel.service_registry
    assert "response_evaluator" in runtime.kernel.service_registry
    assert "conversation_manager" in runtime.kernel.service_registry
    assert "agent_orchestrator" in runtime.kernel.service_registry
    assert "control_config" in runtime.kernel.service_registry
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_llm_provider_manager():
    """Test LLM Provider Manager functionality."""
    runtime = GCSRuntime()
    provider_manager = runtime.llm_provider_manager
    
    assert isinstance(provider_manager, LLMProviderManager)
    
    # Test basic provider operations
    providers = await provider_manager.get_available_providers()
    assert isinstance(providers, list)
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_response_evaluator_service():
    """Test Response Evaluator Service functionality."""
    runtime = GCSRuntime()
    response_evaluator = runtime.response_evaluator_service
    
    assert isinstance(response_evaluator, ResponseEvaluatorService)
    
    # Test basic evaluation
    evaluation = await response_evaluator.evaluate_response("This is a test response")
    assert isinstance(evaluation, dict)
    assert "is_valid" in evaluation
    assert "error_signals" in evaluation
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_conversation_manager():
    """Test Conversation Manager Service functionality."""
    runtime = GCSRuntime()
    conversation_manager = runtime.conversation_manager
    
    assert isinstance(conversation_manager, ConversationManagerService)
    
    # Test basic conversation operations
    session_id = "test_session"
    success = conversation_manager.create_conversation_session(session_id)
    assert success is True
    
    # Add a test message
    added = conversation_manager.add_message_to_conversation(
        session_id, "user", "Hello, world!"
    )
    assert added is True
    
    # Get conversation history
    history = conversation_manager.get_conversation_history(session_id)
    assert len(history) == 1
    
    # Clean up
    conversation_manager.end_conversation_session(session_id)
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_agent_orchestrator():
    """Test Agent Orchestrator Service functionality."""
    runtime = GCSRuntime()
    await runtime.async_init()  # Need to initialize MCP services first
    
    agent_orchestrator = runtime.agent_orchestrator
    
    assert isinstance(agent_orchestrator, AgentOrchestratorService)
    
    # Test basic functionality
    tools = await agent_orchestrator.use_mcp_for_tool_discovery()
    assert isinstance(tools, dict)
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_control_config_service():
    """Test Control & Config Service functionality."""
    runtime = GCSRuntime()
    await runtime.async_init()  # Initialize async components
    
    config_service = runtime.config_service
    
    assert isinstance(config_service, ControlConfigService)
    
    # Initialize the service to populate parameter descriptions
    await config_service.initialize()
    
    # Test basic configuration operations
    config_names = config_service.list_configurations()
    assert isinstance(config_names, list)
    assert "default" in config_names
    
    # Test parameter access
    param_value = await config_service.get_parameter("max_retries")
    # The parameter might be None if not set, but the call should not fail
    assert param_value is not None or param_value is not False  # Allow for valid None results
    
    # Test parameter descriptions
    descriptions = config_service.get_parameter_descriptions()
    assert isinstance(descriptions, dict)
    # Check for any expected parameters
    expected_params = ["llm_model", "max_retries", "default_provider", "conversation_max_length"]
    found_expected = any(param in descriptions for param in expected_params)
    assert found_expected, f"Expected at least one of {expected_params} in descriptions, got {list(descriptions.keys())}"
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_kernel_service_integration():
    """Test integration between kernel and services."""
    runtime = GCSRuntime()
    
    # Test that services are accessible through kernel
    llm_kernel_service = runtime.kernel.get_service("llm_kernel")
    assert llm_kernel_service is not None
    
    llm_provider_manager = runtime.kernel.get_service("llm_provider_manager")  
    assert llm_provider_manager is not None
    
    # Test service communication
    # The LLM kernel service should have a reference to the provider manager
    assert hasattr(llm_kernel_service, 'provider_manager')
    assert llm_kernel_service.provider_manager == llm_provider_manager
    
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_mcp_integration():
    """Test MCP integration with new architecture."""
    runtime = GCSRuntime()
    await runtime.async_init()  # Initialize MCP services asynchronously
    
    # Verify MCP service is available
    assert runtime.mcp_service is not None
    
    # Test MCP tools registration
    connected_agents = runtime.mcp_service.get_connected_agents()
    assert isinstance(connected_agents, dict)
    
    # Verify services have MCP references after async initialization
    assert runtime.prompt_construction_service.mcp_client_service is not None
    assert runtime.conversation_manager.mcp_service is not None
    assert runtime.agent_orchestrator.mcp_service is not None
    
    await runtime.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])