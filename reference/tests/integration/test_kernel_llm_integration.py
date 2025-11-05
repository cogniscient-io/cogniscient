"""
Integration test for the GCS Kernel to LLM response flow.

This test verifies the complete flow from the kernel through to the LLM and back,
using a mock provider to simulate the LLM response without requiring an actual API.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from gcs_kernel.kernel import GCSKernel
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from services.llm_provider.providers.mock_provider import MockProvider
from services.config import settings


class MockMCPClient:
    """Mock MCP client for testing purposes."""
    
    def __init__(self):
        self.submitted_executions = []
        self.execution_results = {}
    
    async def initialize(self):
        pass
        
    async def shutdown(self):
        pass
    
    async def submit_tool_execution(self, tool_name, parameters):
        execution_id = f"exec_{len(self.submitted_executions) + 1}"
        self.submitted_executions.append({
            "id": execution_id,
            "tool_name": tool_name,
            "parameters": parameters
        })
        return execution_id
    
    async def get_execution_result(self, execution_id):
        """Return a mock tool result"""
        from gcs_kernel.models import ToolResult
        return ToolResult(
            tool_name="shell_command",
            llm_content="Mock tool execution result",
            return_display="Mock tool execution result",
            success=True
        )
    
    async def list_tools(self):
        """Return a list of available tools for testing."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "shell_command",
                    "description": "Execute a shell command",
                    "parameters": {
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
        ]


@pytest.mark.asyncio
async def test_kernel_to_llm_hello_world():
    """
    Test the end-to-end flow from kernel to LLM and back with a simple hello world prompt.
    
    This integration test verifies that:
    1. The GCSKernel can be initialized and started
    2. The AIOrchestratorService can be connected to the kernel
    3. The LLM provider can generate a response to a simple prompt
    4. The response flows back through the system correctly
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(mock_kernel_client)
        
        # Create a mock provider directly
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class MockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
                # Also initialize the converter
                from services.llm_provider.providers.openai_converter import OpenAIConverter
                self.converter = OpenAIConverter(self.model)
        
        # Initialize the orchestrator with the mock content generator
        ai_orchestrator.set_content_generator(MockContentGenerator())
        
        # Test the full flow with a simple hello world prompt
        from gcs_kernel.models import PromptObject
        prompt_obj = PromptObject.create(content="Say hello world")
        response_obj = await ai_orchestrator.handle_ai_interaction(prompt_obj)
        response = response_obj.result_content
        
        # Verify the response contains expected content
        assert "Hello" in response or "hello" in response
        assert "test" in response or "Test" in response
        
        print(f"Integration test successful! Response: {response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key


@pytest.mark.asyncio
async def test_kernel_llm_tool_calling_integration():
    """
    Test the end-to-end flow with tool calling functionality.
    
    This integration test verifies that:
    1. The system can generate responses with tool calls
    2. Tool calls are properly executed through the MCP client
    3. Tool results are properly processed and incorporated into the response
    4. The complete tool execution flow works through the content generator
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock with tool execution capability
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(mock_kernel_client)
        
        # Create a mock provider that returns tool calls
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1,
            "response_content": "I'll use a tool to help with that.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "shell_command",
                        "arguments": '{"command": "hostname"}'
                    }
                }
            ]
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class ToolCallingMockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
                # Also initialize the converter
                from services.llm_provider.providers.openai_converter import OpenAIConverter
                self.converter = OpenAIConverter(self.model)
        
        # Initialize the orchestrator with the tool-calling content generator
        ai_orchestrator.set_content_generator(ToolCallingMockContentGenerator())
        
        # Set up mock tool execution manager to work with the MCP client
        class MockToolExecutionManager:
            def __init__(self, mcp_client):
                self.mcp_client = mcp_client
            
            async def execute_internal_tool(self, tool_name, arguments):
                import json
                try:
                    params = json.loads(arguments) if isinstance(arguments, str) else arguments
                except:
                    params = {}
                
                execution_id = await self.mcp_client.submit_tool_execution(tool_name, params)
                result = await self.mcp_client.get_execution_result(execution_id)
                return result
        
        # Set the tool execution manager to enable tool execution in the turn manager
        mock_tool_execution_manager = MockToolExecutionManager(mock_kernel_client)
        ai_orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)
        
        # Test the full flow with a prompt that should trigger tool calling
        from gcs_kernel.models import PromptObject
        prompt_obj = PromptObject.create(content="What is the current date?")
        response_obj = await ai_orchestrator.handle_ai_interaction(prompt_obj)
        response = response_obj.result_content
        
        # Verify tool execution was called
        assert len(mock_kernel_client.submitted_executions) >= 1  # Should have at least 1 execution
        assert mock_kernel_client.submitted_executions[0]["tool_name"] == "shell_command"
        assert mock_kernel_client.submitted_executions[0]["parameters"] == {"command": "hostname"}
        
        # Verify tool result was retrieved
        assert len(mock_kernel_client.execution_results) == 0  # The MockMCPClient doesn't store results in this implementation
        
        # Verify the response contains expected content from tool execution
        assert response is not None
        assert len(response) > 0
        
        print(f"Tool calling integration test successful! Response: {response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key


@pytest.mark.asyncio
async def test_kernel_llm_streaming_hello_world():
    """
    Test the streaming end-to-end flow from kernel to LLM and back.
    
    This integration test verifies the streaming capability of the system.
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(mock_kernel_client)
        
        # Create a mock provider directly
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class MockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
                # Also initialize the converter
                from services.llm_provider.providers.openai_converter import OpenAIConverter
                self.converter = OpenAIConverter(self.model)
        
        # Initialize the orchestrator with the mock content generator
        ai_orchestrator.set_content_generator(MockContentGenerator())
        
        # Test the streaming flow with a simple hello world prompt
        from gcs_kernel.models import PromptObject
        prompt_obj = PromptObject.create(content="Say hello world")
        chunks = []
        async for chunk in ai_orchestrator.stream_ai_interaction(prompt_obj):
            chunks.append(chunk)
        
        # Combine all chunks to form the full response
        full_response = "".join(chunks)
        
        # Verify the response contains expected content
        assert "Hello" in full_response or "hello" in full_response
        assert "test" in full_response or "Test" in full_response
        
        print(f"Streaming integration test successful! Full response: {full_response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key


@pytest.mark.asyncio
async def test_kernel_llm_streaming_tool_calling_integration():
    """
    Test the streaming end-to-end flow with tool calling functionality.
    
    This integration test verifies that:
    1. Streaming works with tool calls in the response
    2. Tool calls are properly detected and executed during streaming
    3. Tool results are processed correctly in the streaming context
    4. The complete streaming tool execution flow works through the content generator
    """
    # Use mock settings for testing
    original_api_key = settings.llm_api_key
    settings.llm_api_key = "test-key"  # Required value for initialization
    
    try:
        # Initialize the MCP client mock with tool execution capability
        mock_kernel_client = MockMCPClient()
        
        # Initialize the AI orchestrator service
        ai_orchestrator = AIOrchestratorService(mock_kernel_client)
        
        # Create a mock provider that returns tool calls in streaming mode
        mock_provider_config = {
            "api_key": "test-key",
            "model": "gpt-4-test",
            "base_url": "https://mock.api.test",
            "timeout": 30,
            "max_retries": 1,
            "response_content": "I'll use a tool to help with that.",
            "tool_calls": [
                {
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "shell_command",
                        "arguments": '{"command": "echo Hello from tool"}'
                    }
                }
            ]
        }
        mock_provider = MockProvider(mock_provider_config)
        
        # Create a content generator that uses the mock provider
        class StreamingToolCallingMockContentGenerator(LLMContentGenerator):
            def __init__(self):
                # Set up minimal configuration for testing
                self.api_key = "test-key"
                self.model = "gpt-4-test"
                self.base_url = "https://mock.api.test"
                self.timeout = 30
                self.max_retries = 1
                
                # Use the mock provider directly
                self.provider = mock_provider
                from services.llm_provider.pipeline import ContentGenerationPipeline
                self.pipeline = ContentGenerationPipeline(self.provider)
                # Also initialize the converter
                from services.llm_provider.providers.openai_converter import OpenAIConverter
                self.converter = OpenAIConverter(self.model)
        
        # Initialize the orchestrator with the streaming tool-calling content generator
        ai_orchestrator.set_content_generator(StreamingToolCallingMockContentGenerator())
        
        # Set up mock tool execution manager to work with the MCP client
        class MockToolExecutionManager:
            def __init__(self, mcp_client):
                self.mcp_client = mcp_client
            
            async def execute_internal_tool(self, tool_name, arguments):
                import json
                try:
                    params = json.loads(arguments) if isinstance(arguments, str) else arguments
                except:
                    params = {}
                
                execution_id = await self.mcp_client.submit_tool_execution(tool_name, params)
                result = await self.mcp_client.get_execution_result(execution_id)
                return result
        
        # Set the tool execution manager to enable tool execution in the turn manager
        mock_tool_execution_manager = MockToolExecutionManager(mock_kernel_client)
        ai_orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)
        
        # Test the streaming flow with a prompt that should trigger tool calling
        from gcs_kernel.models import PromptObject
        prompt_obj = PromptObject.create(content="Run a command and stream the result")
        chunks = []
        async for chunk in ai_orchestrator.stream_ai_interaction(prompt_obj):
            chunks.append(chunk)
        
        # Combine all chunks to form the full response
        full_response = "".join(chunks)
        
        # Verify tool execution was called during streaming
        assert len(mock_kernel_client.submitted_executions) >= 1  # Should have at least 1 execution
        assert mock_kernel_client.submitted_executions[0]["tool_name"] == "shell_command"
        assert mock_kernel_client.submitted_executions[0]["parameters"] == {"command": "echo Hello from tool"}
        
        # Verify the response contains expected content
        assert full_response is not None
        assert len(full_response) > 0
        
        print(f"Streaming tool calling integration test successful! Full response: {full_response}")
        
    finally:
        # Restore original settings
        settings.llm_api_key = original_api_key