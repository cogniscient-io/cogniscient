"""
Test suite for the AI Orchestrator with LLM Integration.

This module tests the AIOrchestratorService's integration with LLM providers.
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
    
    async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of generate_response.
        """
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # For testing purposes, return a response with a tool call sometimes
        if "use tool" in prompt.lower() or "tool" in prompt.lower():
            # Create a mock tool call object with the expected attributes
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.parameters = {"command": "echo hello"}  # Using a real tool with valid parameters
        
            return ResponseObj(
                content="I'll use a tool to help with that.",
                tool_calls=[MockToolCall()]
            )
        else:
            return ResponseObj(
                content=f"Response to: {prompt}",
                tool_calls=[]
            )
    
    async def process_tool_result(self, tool_result, conversation_history=None):
        """
        Mock implementation of process_tool_result.
        """
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed tool result: {tool_result}")
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
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
        "tools": [
            {
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
        ]
    }
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="hello\n",  # Output of echo hello
        return_display="hello\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Mock the system_context_builder to return the available tools
    async def mock_get_available_tools():
        return {
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
    
    # Replace the system_context_builder's method with our mock
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools
    
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    response = await orchestrator.handle_ai_interaction("Please use a tool to help me.")
    
    # Verify that tool execution was called (the prompt contains 'use tool' which triggers the mock to return a tool call)
    mock_kernel_client.submit_tool_execution.assert_called()
    mock_kernel_client.get_execution_result.assert_called_once_with("exec_123")
    
    # Verify the response includes the processed tool result
    assert "Processed tool result" in response


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
    assert "Hello, stream this." in chunks[0]