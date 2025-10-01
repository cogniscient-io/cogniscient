"""
Test for MCP service integration with LLM
"""
import asyncio
from unittest.mock import Mock, AsyncMock

from cogniscient.engine.services.mcp_service import MCPService, create_mcp_service
from cogniscient.engine.services.contextual_llm_service import ContextualLLMService
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.gcs_runtime import GCSRuntime


async def test_mcp_service_integration():
    """Test that MCP service can be used by LLM via contextual service"""
    
    # Create a mock GCS runtime
    mock_runtime = Mock(spec=GCSRuntime)
    mock_runtime.agents = {
        "test_agent": Mock()
    }
    mock_runtime.run_agent = Mock(return_value={"result": "success"})
    
    # Create MCP service instance
    mcp_service = await create_mcp_service(mock_runtime)
    
    # Verify MCP service has the required methods that LLM can call
    assert hasattr(mcp_service, 'connect_to_external_agent')
    assert hasattr(mcp_service, 'get_connected_agents')
    assert hasattr(mcp_service, 'get_external_agent_capabilities')
    assert hasattr(mcp_service, 'call_external_agent_tool')
    assert hasattr(mcp_service, 'disconnect_from_external_agent')
    assert hasattr(mcp_service, 'get_registered_external_tools')
    assert hasattr(mcp_service, 'describe_mcp_service')
    
    # Verify describe_mcp_service returns proper structure
    service_info = mcp_service.describe_mcp_service()
    assert "name" in service_info
    assert "methods" in service_info
    assert "connect_to_external_agent" in service_info["methods"]
    
    print("✓ MCP service has all required methods")
    
    # Mock LLM service
    mock_llm_service = Mock(spec=LLMService)
    mock_llm_service.model = "test-model"
    mock_llm_service.api_key = "test-key"
    
    # Create contextual LLM service with MCP service as a system service
    system_services = {
        "MCPManager": mcp_service.describe_mcp_service()
    }
    
    contextual_service = ContextualLLMService(
        llm_service=mock_llm_service,
        system_services=system_services
    )
    
    # Verify that the system services are properly included
    capabilities_str = contextual_service._format_system_service_capabilities()
    
    # Check that MCP service is included in the system capabilities
    assert "MCPManager" in capabilities_str
    assert "Model Context Protocol service" in capabilities_str
    assert "connect_to_external_agent" in capabilities_str
    
    print("✓ MCP service is properly integrated with ContextualLLMService")
    
    # Test that we can access the MCP service's functionality through the contextual service
    agent_registry_with_mcp = {
        "mcp_service": mcp_service
    }
    
    contextual_service.set_agent_registry(agent_registry_with_mcp, system_services)
    
    print("✓ All integration tests passed")
    

async def test_mcp_service_with_mock_connection():
    """Test MCP service connection functionality with mock"""
    
    # Create a mock GCS runtime
    mock_runtime = Mock(spec=GCSRuntime)
    mock_runtime.agents = {}
    mock_runtime.run_agent = Mock(return_value={"result": "success"})
    
    # Create MCP service instance
    mcp_service = await create_mcp_service(mock_runtime)
    
    # Test that the service can report connected agents (should be empty initially)
    agents_info = mcp_service.get_connected_agents()
    assert agents_info["success"] is True
    assert agents_info["count"] == 0
    assert len(agents_info["connected_agents"]) == 0
    
    print("✓ MCP service correctly reports no connected agents initially")
    
    # Test the external tools registry (should be empty initially)
    tools_info = mcp_service.get_registered_external_tools()
    assert tools_info["success"] is True
    assert tools_info["total_tools"] == 0
    assert len(tools_info["external_agent_tools"]) == 0
    
    print("✓ MCP service correctly reports no registered external tools initially")
    
    # Test the describe method
    service_desc = mcp_service.describe_mcp_service()
    assert service_desc["name"] == "MCPService"
    assert "connect_to_external_agent" in service_desc["methods"]
    assert "get_registered_external_tools" in service_desc["methods"]
    
    print("✓ MCP service description includes all expected methods")


if __name__ == "__main__":
    print("Running MCP service integration tests...")
    
    # Run integration tests
    asyncio.run(test_mcp_service_integration())
    asyncio.run(test_mcp_service_with_mock_connection())
    
    print("\nAll tests passed! ✓")