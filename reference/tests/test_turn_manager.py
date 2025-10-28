"""
Test suite for the Turn Manager in AI Orchestrator.

This module tests the TurnManager which handles the turn-based AI interaction,
managing the flow between streaming content and tool execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.turn_manager import TurnManager, TurnEventType, TurnEvent
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult
from gcs_kernel.registry import ToolRegistry


class MockContentGenerator(BaseContentGenerator):
    """Mock content generator for testing turn manager."""
    
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
    
    async def generate_response(self, prompt: str, system_context: str = None):
        """Mock generate_response with configurable responses."""
        self.call_count += 1
        
        # Return different responses based on call count
        if self.call_count <= len(self.responses):
            return self.responses[self.call_count - 1]
        else:
            # Default response
            class ResponseObj:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []
            return ResponseObj(content="Default response", tool_calls=[])
    
    async def stream_response(self, prompt: str, system_context: str = None):
        """Mock stream_response."""
        yield f"Streaming: {prompt}"


class MockTool:
    """Mock tool for testing tool execution."""
    
    def __init__(self, name="test_tool", description="Test tool"):
        self.name = name
        self.description = description
        self.parameter_schema = {"type": "object", "properties": {}}
        self.display_name = name
    
    async def execute(self, parameters):
        """Mock tool execution."""
        return ToolResult(
            tool_name=self.name,
            success=True,
            llm_content=f"Mock result for {self.name}",
            return_display=f"Mock result for {self.name}"
        )


@pytest.mark.asyncio
async def test_turn_manager_initialization():
    """Test that TurnManager initializes properly."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    
    assert turn_manager.kernel_client == mock_kernel_client
    assert turn_manager.content_generator == mock_content_generator
    assert turn_manager.conversation_history == []


@pytest.mark.asyncio
async def test_turn_manager_run_turn_simple_content():
    """Test run_turn with simple content (no tool calls)."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Configure content generator to return a simple response
    class MockResponse:
        def __init__(self, content):
            self.content = content
            self.tool_calls = []  # No tool calls
    
    mock_content_generator.responses = [MockResponse("Simple response")]
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Verify events
    assert len(events) >= 2  # Should have at least CONTENT and FINISHED events
    content_event = next((e for e in events if e.type == TurnEventType.CONTENT), None)
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    
    assert content_event is not None
    assert content_event.value == "Simple response"
    assert finished_event is not None


@pytest.mark.asyncio
async def test_turn_manager_run_turn_with_tool_call():
    """Test run_turn with a tool call."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a mock tool call
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.name = name
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    # Configure content generator to return a response with tool calls
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    mock_response_with_tool = MockResponse(
        content="I'll get that information for you",
        tool_calls=[MockToolCall("call_1", "echo_tool", {"test": "value"})]
    )
    
    mock_content_generator.responses = [mock_response_with_tool]
    
    # Set up kernel registry with a mock tool
    mock_registry = AsyncMock()
    mock_tool = MockTool(name="echo_tool")
    mock_registry.get_tool = AsyncMock(return_value=mock_tool)
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Verify events - should have TOOL_CALL_REQUEST, TOOL_CALL_RESPONSE, and FINISHED
    assert len(events) >= 3  # At least request, response, and finished events
    
    tool_request_event = next((e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST), None)
    tool_response_event = next((e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE), None)
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    
    assert tool_request_event is not None
    assert tool_response_event is not None
    assert finished_event is not None
    
    # Verify tool call details
    assert tool_request_event.value["name"] == "echo_tool"
    assert tool_request_event.value["arguments"]["test"] == "value"


@pytest.mark.asyncio
async def test_turn_manager_run_turn_multiple_tool_calls():
    """Test run_turn with multiple tool calls in sequence."""
    mock_kernel_client = AsyncMock()
    
    # Create a more sophisticated mock content generator that responds differently to tool results
    class MultiCallMockContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0
    
        async def generate_response(self, prompt: str, system_context: str = None):
            self.call_count += 1
            
            class MockResponse:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []
            
            # First call returns a tool call
            if self.call_count == 1:
                class MockToolCall:
                    def __init__(self, call_id, name, arguments):
                        self.id = call_id
                        self.name = name
                        self.arguments = arguments
                        self.arguments_json = '{"action": "step1"}'  # Required attribute
                
                return MockResponse(
                    content="First step",
                    tool_calls=[MockToolCall("call_1", "first_tool", {"action": "step1"})]
                )
            # Second call (after tool execution) returns another tool call
            elif self.call_count == 2:
                class MockToolCall:
                    def __init__(self, call_id, name, arguments):
                        self.id = call_id
                        self.name = name
                        self.arguments = arguments
                        self.arguments_json = '{"action": "step2"}'  # Required attribute
                
                return MockResponse(
                    content="Second step",
                    tool_calls=[MockToolCall("call_2", "second_tool", {"action": "step2"})]
                )
            # Third call and beyond return final response
            else:
                return MockResponse(content="Final response", tool_calls=[])
        
        async def stream_response(self, prompt: str, system_context: str = None):
            yield f"Streaming: {prompt}"
    
    mock_content_generator = MultiCallMockContentGenerator()
    
    # Set up kernel registry with mock tools
    mock_registry = AsyncMock()
    
    async def get_tool(name):
        if name in ["first_tool", "second_tool"]:
            return MockTool(name=name)
        return None
    
    mock_registry.get_tool = get_tool
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Should have tool call events from both calls
    tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
    tool_response_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE]
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    
    assert len(tool_request_events) == 2  # Two tool calls (first and second)
    assert len(tool_response_events) == 2  # Two tool responses
    assert finished_event is not None


@pytest.mark.asyncio
async def test_turn_manager_run_turn_recursive_tool_calls():
    """Test run_turn with recursive tool calls (tools that trigger more tools)."""
    mock_kernel_client = AsyncMock()
    
    # Create a mock content generator that generates a tool call, then when that result
    # is processed, generates another tool call, and finally a final response
    class RecursiveMockContentGenerator(BaseContentGenerator):
        def __init__(self):
            self.call_count = 0  # Track total calls to the generator
    
        async def generate_response(self, prompt: str, system_context: str = None):
            self.call_count += 1
            
            class MockResponse:
                def __init__(self, content, tool_calls=None):
                    self.content = content
                    self.tool_calls = tool_calls or []
            
            # First call returns a tool call (first step)
            if self.call_count == 1:
                class MockToolCall:
                    def __init__(self, call_id, name, arguments):
                        self.id = call_id
                        self.name = name
                        self.arguments = arguments
                        self.arguments_json = '{"step": "first"}'
                
                return MockResponse(
                    content="Need to do first step",
                    tool_calls=[MockToolCall("call_1", "first_tool", {"step": "first"})]
                )
            # Second call (after first tool result) returns another tool call (second step)
            elif self.call_count == 2:
                class MockToolCall:
                    def __init__(self, call_id, name, arguments):
                        self.id = call_id
                        self.name = name
                        self.arguments = arguments
                        self.arguments_json = '{"step": "second"}'
                
                return MockResponse(
                    content="Need to do second step",
                    tool_calls=[MockToolCall("call_2", "second_tool", {"step": "second"})]
                )
            # Third call (after second tool result) returns final response
            else:
                return MockResponse(content="All done", tool_calls=[])
        
        async def stream_response(self, prompt: str, system_context: str = None):
            yield f"Streaming: {prompt}"
    
    mock_content_generator = RecursiveMockContentGenerator()
    
    # Set up kernel registry with both tools
    mock_registry = AsyncMock()
    
    async def get_tool(name):
        if name in ["first_tool", "second_tool"]:
            return MockTool(name=name)
        return None
    
    mock_registry.get_tool = get_tool
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Should have events from both initial call and recursive call
    tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
    tool_response_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE]
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    
    # Should have at least 2 tool calls (first and recursive)
    assert len(tool_request_events) >= 2
    assert len(tool_response_events) >= 2
    assert finished_event is not None


@pytest.mark.asyncio
async def test_turn_manager_handles_empty_tool_calls_gracefully():
    """Test run_turn handles responses with empty or invalid tool calls."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a response with an invalid tool call (empty name)
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            # Use empty name to test invalid case
            self.name = name if name else ""
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    # Response with invalid tool call (empty name)
    mock_response = MockResponse(
        content="Attempting to call tool",
        tool_calls=[MockToolCall("call_1", "", {"test": "value"})]  # Empty name
    )
    
    mock_content_generator.responses = [mock_response]
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    # Don't set registry since we're testing invalid tool case
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Should still complete normally, handling the invalid tool call gracefully
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    assert finished_event is not None


@pytest.mark.asyncio
async def test_turn_manager_tool_not_found_handling():
    """Test run_turn handles tool not found gracefully."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a mock tool call
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.name = name
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    # Response with a tool call that will fail
    mock_response = MockResponse(
        content="Will try to execute tool",
        tool_calls=[MockToolCall("call_1", "nonexistent_tool", {"test": "value"})]
    )
    
    mock_content_generator.responses = [mock_response]
    
    # Set up registry to return None (tool not found) to simulate error
    mock_registry = AsyncMock()
    mock_registry.get_tool = AsyncMock(return_value=None)  # Tool not found
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Should still complete normally since tool errors are handled gracefully
    # and conversation continues via process_tool_result
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    assert finished_event is not None
    
    # Should have had a tool call request and response
    request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
    response_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE]
    
    # The tool should have been requested but the error handled gracefully
    assert len(request_events) == 1
    assert len(response_events) == 1


@pytest.mark.asyncio
async def test_turn_manager_execute_tool_exception():
    """Test run_turn handles exceptions during tool execution."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a mock tool call
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.name = name
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    # Response with a tool call
    mock_response = MockResponse(
        content="Will try to execute tool",
        tool_calls=[MockToolCall("call_1", "failing_tool", {"test": "value"})]
    )
    
    mock_content_generator.responses = [mock_response]
    
    # Create a mock tool that throws an exception
    class FailingMockTool:
        def __init__(self):
            self.name = "failing_tool"
            self.description = "A tool that fails"
            self.parameter_schema = {"type": "object", "properties": {}}
            self.display_name = "failing_tool"
        
        async def execute(self, parameters):
            raise Exception("Tool execution failed")
    
    # Set up registry to return the failing tool
    mock_registry = AsyncMock()
    failing_tool = FailingMockTool()
    mock_registry.get_tool = AsyncMock(return_value=failing_tool)
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # Should have an error event because of the exception during tool execution
    error_event = next((e for e in events if e.type == TurnEventType.ERROR), None)
    finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)
    
    assert error_event is not None
    assert "Error executing tool" in str(error_event.error)


@pytest.mark.asyncio
async def test_turn_manager_abort_signal():
    """Test run_turn with abort signal."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a mock tool call
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.name = name
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    mock_response = MockResponse(
        content="Will execute tool",
        tool_calls=[MockToolCall("call_1", "test_tool", {"test": "value"})]
    )
    
    mock_content_generator.responses = [mock_response]
    
    # Set up registry with a working tool
    mock_registry = AsyncMock()
    mock_tool = MockTool(name="test_tool")
    mock_registry.get_tool = AsyncMock(return_value=mock_tool)
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Create abort signal and set it before processing
    abort_signal = asyncio.Event()
    abort_signal.set()  # Set the signal to trigger early termination
    
    # Run the turn with abort signal already set
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context", abort_signal):
        events.append(event)
    
    # Should have an error event due to cancellation
    error_event = next((e for e in events if e.type == TurnEventType.ERROR), None)
    
    assert error_event is not None
    assert "Turn cancelled by user" in str(error_event.error)


@pytest.mark.asyncio
async def test_conversation_history_maintained_with_tool_calls():
    """Test that conversation history is properly maintained across tool calls."""
    mock_kernel_client = AsyncMock()
    mock_content_generator = MockContentGenerator()
    
    # Create a mock tool call
    class MockToolCall:
        def __init__(self, call_id, name, arguments):
            self.id = call_id
            self.name = name
            self.arguments = arguments
            self.arguments_json = '{"test": "value"}'  # Required attribute
    
    class MockResponse:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
    
    mock_response = MockResponse(
        content="I need to get some data",
        tool_calls=[MockToolCall("call_1", "test_tool", {"test": "value"})]
    )
    
    mock_content_generator.responses = [mock_response]
    
    # Set up registry
    mock_registry = AsyncMock()
    mock_tool = MockTool(name="test_tool")
    mock_registry.get_tool = AsyncMock(return_value=mock_tool)
    
    turn_manager = TurnManager(mock_kernel_client, mock_content_generator)
    turn_manager.registry = mock_registry
    
    # Run the turn
    events = []
    async for event in turn_manager.run_turn("Test prompt", "Test system context"):
        events.append(event)
    
    # After the turn, the conversation history should be updated
    # Check that it contains messages for user, assistant with tool call, and tool result
    assert len(turn_manager.conversation_history) >= 3  # user message, assistant tool call, tool result
    
    message_roles = [msg.get("role") for msg in turn_manager.conversation_history]
    assert "user" in message_roles
    assert "assistant" in message_roles
    assert "tool" in message_roles