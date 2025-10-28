"""
Test suite for the AI Orchestrator with LLM Integration.

This module tests the AIOrchestratorService's integration with LLM providers using the new architecture.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class MockContentGenerator(BaseContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing purposes.
    """
    def __init__(self, config=None):
        # Initialize with an empty config to avoid errors
        self.config = config or {}
        # Set up any attributes needed for testing from the config
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout")
        self.max_retries = self.config.get("max_retries")
    
    def __init__(self, config=None):
        # Initialize with an empty config to avoid errors
        self.config = config or {}
        # Set up any attributes needed for testing from the config
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout")
        self.max_retries = self.config.get("max_retries")
        # Track call count to change behavior
        self.call_count = 0
    
    async def generate_response(self, prompt: str, system_context: str = None):
        """
        Mock implementation of generate_response.
        """
        from services.llm_provider.tool_call_processor import ToolCall
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # Increment call count to change behavior on subsequent calls
        self.call_count += 1
        
        # For testing purposes, return a response with a tool call sometimes (first call)
        if self.call_count == 1 and ("use tool" in prompt.lower() or "tool" in prompt.lower()):
            # Create a mock tool call object with the expected attributes
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.arguments = {"command": "echo hello"}  # Using a real tool with valid parameters
                    import json
                    self.arguments_json = json.dumps(self.arguments)  # JSON string format for OpenAI compatibility

            return ResponseObj(
                content="I'll use a tool to help with that.",
                tool_calls=[MockToolCall()]
            )
        elif self.call_count > 1:
            # On subsequent calls (after tool execution), return a response that includes the result
            return ResponseObj(
                content="The tool was executed and returned: hello",
                tool_calls=[]
            )
        else:
            return ResponseObj(
                content=f"Response to: {prompt}",
                tool_calls=[]
            )
    
    async def stream_response(self, prompt: str, system_context: str = None):
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt}"


@pytest.mark.asyncio
async def test_ai_orchestrator_initialization():
    """
    Test that AIOrchestratorService initializes properly with MCP client.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    
    assert orchestrator.kernel_client == kernel_client
    assert orchestrator.content_generator is None
    # Ensure all new components are initialized
    assert orchestrator.turn_manager is not None
    assert orchestrator.tool_executor is not None
    assert orchestrator.streaming_handler is not None


@pytest.mark.asyncio
async def test_ai_orchestrator_set_content_generator():
    """
    Test that AIOrchestratorService can have its content generator set.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    mock_provider = MockContentGenerator()
    
    orchestrator.set_content_generator(mock_provider)
    
    assert orchestrator.content_generator == mock_provider
    # Verify components were also updated
    assert orchestrator.turn_manager.content_generator == mock_provider
    assert orchestrator.streaming_handler.content_generator == mock_provider


@pytest.mark.asyncio
async def test_ai_orchestrator_handle_ai_interaction():
    """
    Test that AIOrchestratorService can handle an AI interaction.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    response = await orchestrator.handle_ai_interaction("Hello, how are you?")
    
    assert "Hello, how are you?" in response


@pytest.mark.asyncio
async def test_ai_orchestrator_handle_ai_interaction_with_tool_call():
    """
    Test that AIOrchestratorService can handle an AI interaction with tool calls.
    """
    # Mock the kernel client to simulate tool execution
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    # Mock the list_tools method for backward compatibility
    mock_kernel_client.list_tools.return_value = {
        "shell_command": {
            "name": "shell_command",
            "description": "Execute a shell command and return the output",
            "parameter_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="hello\n",  # Output of echo hello
        return_display="hello\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Update the content generator reference in turn manager and other components too
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    response = await orchestrator.handle_ai_interaction("Please use a tool to help me.")
    
    # The response should include the content from the tool execution
    assert "hello" in response.lower()


@pytest.mark.asyncio
async def test_ai_orchestrator_stream_ai_interaction():
    """
    Test that AIOrchestratorService can stream an AI interaction.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    chunks = []
    async for chunk in orchestrator.stream_ai_interaction("Hello, stream this."):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    # When streaming, the first chunk might be a tool request or content
    # depending on the mock behavior


@pytest.mark.asyncio
async def test_turn_manager_with_tool_calls():
    """
    Test that the TurnManager properly handles tool calls in a turn.
    """
    from services.ai_orchestrator.turn_manager import TurnManager
    
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    mock_provider = MockContentGenerator()
    turn_manager = TurnManager(kernel_client, mock_provider)
    
    # Create an abort signal for the turn
    import asyncio
    abort_signal = asyncio.Event()
    
    # Run a turn with a prompt that triggers a tool call
    events = []
    async for event in turn_manager.run_turn(
        "Please use a tool to help me.",
        "System context for testing",
        abort_signal
    ):
        events.append(event)
    
    # Verify we got the expected events
    assert len(events) > 0
    # Should have at least one content event or tool request event
    event_types = [e.type for e in events]
    assert any(t in ['content', 'tool_call_request', 'finished', 'tool_call_response'] for t in event_types)