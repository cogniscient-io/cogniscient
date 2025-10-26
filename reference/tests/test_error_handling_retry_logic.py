"""
Test suite for robust error handling and retry logic in AI Orchestrator.

This module tests that error handling and retry mechanisms work properly,
similar to Qwen Code's implementation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService, ToolCallStatus
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class MockContentGenerator(BaseContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing error handling.
    """
    def __init__(self, config=None, should_fail=False, fail_count=0):
        self.config = config or {}
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fail_count = 0
        self.generate_response_calls = []
        self.process_tool_result_calls = []
    
    async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of generate_response with optional failure.
        """
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'tools': tools
        })
        
        # Fail the first few calls if configured to do so
        if self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # Return a response with a tool call for testing
        class MockToolCall:
            def __init__(self):
                self.id = "test_call_123"
                self.name = "shell_command"
                self.parameters = {"command": "echo hello"}
        
        return ResponseObj(
            content="I'll use a tool to help with that.",
            tool_calls=[MockToolCall()] if not self.should_fail else []
        )
    
    async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
        """
        Mock implementation of process_tool_result.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'available_tools': available_tools
        })
        
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed: {tool_result.llm_content}")
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt}"


@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    """
    Test that the retry mechanism works correctly and eventually succeeds.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a function that fails twice then succeeds
    call_count = 0
    def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception(f"Simulated failure on attempt {call_count}")
        return "Success after retries"
    
    async def async_failing_func():
        return failing_func()
    
    # Execute with retry - should succeed after 2 failures
    result = await orchestrator._retry_with_backoff(
        async_failing_func,
        max_retries=3,
        base_delay=0.01,  # Very short delay for testing
        jitter=False  # Disable jitter for predictable testing
    )
    
    assert result == "Success after retries"
    assert call_count == 3  # Initial attempt + 2 retries


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    """
    Test that the retry mechanism eventually gives up after max retries.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a function that always fails
    def always_fail():
        raise Exception("Always fails")
    
    async def async_always_fail():
        return always_fail()
    
    # Execute with retry - should eventually raise the exception
    with pytest.raises(Exception, match="Always fails"):
        await orchestrator._retry_with_backoff(
            async_always_fail,
            max_retries=2,
            base_delay=0.01,  # Very short delay for testing
            jitter=False  # Disable jitter for predictable testing
        )


@pytest.mark.asyncio
async def test_error_categorization():
    """
    Test that different types of errors are properly categorized.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Test network error
    network_error = ConnectionError("Connection failed")
    assert orchestrator._categorize_error(network_error) == "NETWORK_ERROR"
    
    # Test timeout error
    timeout_error = TimeoutError("Request timed out")
    assert orchestrator._categorize_error(timeout_error) == "NETWORK_ERROR"
    
    # Test auth error
    auth_error = Exception("Unauthorized access")
    assert orchestrator._categorize_error(auth_error) == "AUTH_ERROR"
    
    # Test rate limit error
    rate_limit_error = Exception("Rate limit exceeded: 429")
    assert orchestrator._categorize_error(rate_limit_error) == "RATE_LIMIT_ERROR"
    
    # Test server error
    server_error = Exception("Internal server error 500")
    assert orchestrator._categorize_error(server_error) == "SERVER_ERROR"
    
    # Test validation error
    validation_error = Exception("Invalid input provided")
    assert orchestrator._categorize_error(validation_error) == "VALIDATION_ERROR"
    
    # Test unknown error
    unknown_error = Exception("Some other error")
    assert orchestrator._categorize_error(unknown_error) == "UNKNOWN_ERROR"


@pytest.mark.asyncio
async def test_error_context_creation():
    """
    Test that error context is properly created with relevant information.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Add some conversation history to test context
    orchestrator.conversation_history = [{"role": "user", "content": "test"}] * 5
    orchestrator.active_tool_calls = {"test": "value"}
    orchestrator.completed_tool_calls = {"completed": "value"}
    
    # Create error context
    context = orchestrator._create_error_context("test_operation", {"custom": "value"})
    
    # Verify context contains expected information
    assert context["operation"] == "test_operation"
    assert context["conversation_length"] == 5
    assert context["active_tools"] == 1
    assert context["completed_tools"] == 1
    assert context["custom"] == "value"


@pytest.mark.asyncio
async def test_error_handling_with_context():
    """
    Test the complete error handling with context reporting.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create an exception
    test_error = ValueError("Test error message")
    
    # Handle the error with context
    context = orchestrator._create_error_context("test_operation", {"input": "value"})
    result = await orchestrator._handle_error_with_context(test_error, context)
    
    # Verify the result contains error information
    assert result["error_type"] == "ValueError"
    assert result["error_message"] == "Test error message"
    assert result["error_category"] == "UNKNOWN_ERROR"
    assert result["operation"] == "test_operation"


@pytest.mark.asyncio
async def test_robust_content_generation_with_retries():
    """
    Test that content generation is robust with retry logic.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a content generator that fails initially but succeeds later
    mock_provider = MockContentGenerator(should_fail=False, fail_count=2)  # Will fail first 2 attempts
    orchestrator.set_content_generator(mock_provider)
    
    # Mock the system_context_builder
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
    
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools
    
    # Call the orchestrator - should succeed after retries
    response = await orchestrator.handle_ai_interaction("Test prompt")
    
    # Verify the response was generated despite initial failures
    assert "Error generating response" not in response  # Should not have the error message
    assert len(mock_provider.generate_response_calls) >= 3  # Should have retried at least once


@pytest.mark.asyncio
async def test_tool_execution_error_handling():
    """
    Test that tool execution errors are handled gracefully.
    """
    # Create mock kernel client that fails on submit_tool_execution
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.side_effect = Exception("Service unavailable")
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a content generator that returns a tool call
    mock_provider = MockContentGenerator(should_fail=False, fail_count=0)
    orchestrator.set_content_generator(mock_provider)
    
    # Mock the system_context_builder
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
    
    orchestrator.system_context_builder.get_available_tools = mock_get_available_tools
    
    # Call the orchestrator - tool submission will fail, but should be handled gracefully
    response = await orchestrator.handle_ai_interaction("Test prompt for tool execution")
    
    # Should not crash, and potentially have an error in the response string
    # The response handling in the orchestrator should catch the exception and continue
    assert response is not None