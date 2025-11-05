"""
Test suite for Turn Manager streaming vs non-streaming modes.

This module tests that the TurnManager properly handles both streaming and non-streaming
modes based on the streaming_enabled flag in the PromptObject.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from gcs_kernel.models import PromptObject, ToolInclusionPolicy, ToolResult
from services.ai_orchestrator.turn_manager import TurnManager, TurnEventType
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient


class StreamingTestContentGenerator(BaseContentGenerator):
    """Test content generator that supports both streaming and non-streaming responses."""
    
    def __init__(self, response_content="Test response", has_tool_calls=False, tool_call_name="test_tool"):
        self.response_content = response_content
        self.has_tool_calls = has_tool_calls
        self.tool_call_name = tool_call_name
        self.generate_response_call_count = 0
        self.stream_response_call_count = 0
        self.first_call_only_has_tool_calls = True  # Only add tool calls on first call to prevent recursion
        
    async def generate_response(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """Simulate non-streaming response generation."""
        self.generate_response_call_count += 1
        prompt_obj.result_content = self.response_content
        
        # Only add tool calls on first call to prevent recursive tool calls in testing
        if self.has_tool_calls and (self.first_call_only_has_tool_calls and self.generate_response_call_count == 1):
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": self.tool_call_name,
                    "arguments": '{"param": "value"}'
                }
            })
        elif not self.first_call_only_has_tool_calls and self.has_tool_calls:
            # If not first-only mode, always add tool calls (for other test cases)
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": self.tool_call_name,
                    "arguments": '{"param": "value"}'
                }
            })
            
        prompt_obj.mark_completed(prompt_obj.result_content)

    async def stream_response(self, prompt_obj: 'PromptObject') -> 'AsyncIterator[str]':
        """Simulate streaming response generation."""
        self.stream_response_call_count += 1
        # Yield content in chunks
        content = self.response_content
        chunk_size = len(content) // 3 if len(content) > 3 else len(content)
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size]
            
        # Update the prompt object with the full content and potential tool calls
        prompt_obj.result_content = content
        
        # Only add tool calls on first call to prevent recursive tool calls in testing
        if self.has_tool_calls and (self.first_call_only_has_tool_calls and self.stream_response_call_count == 1):
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": self.tool_call_name,
                    "arguments": '{"param": "value"}'
                }
            })
        elif not self.first_call_only_has_tool_calls and self.has_tool_calls:
            # If not first-only mode, always add tool calls (for other test cases)
            prompt_obj.add_tool_call({
                "id": "call_123",
                "function": {
                    "name": self.tool_call_name,
                    "arguments": '{"param": "value"}'
                }
            })

    def process_streaming_chunks(self, chunks: list):
        """Process streaming chunks."""
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test processed content"
                },
                "finish_reason": "stop"
            }]
        }


@pytest.mark.asyncio
async def test_turn_manager_with_streaming_enabled():
    """Test that turn manager uses streaming path when streaming_enabled=True."""
    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    
    # Create content generator that tracks which method is called
    content_generator = StreamingTestContentGenerator(
        response_content="Streaming test response",
        has_tool_calls=False
    )
    
    # Create turn manager
    turn_manager = TurnManager(mock_mcp_client, content_generator)
    
    # Create a prompt object with streaming enabled
    prompt_obj = PromptObject.create(
        content="Test prompt",
        streaming_enabled=True  # This should trigger streaming path
    )
    
    # Run the turn and collect events
    events = []
    async for event in turn_manager.run_turn(prompt_obj):
        events.append(event)
    
    # Verify that the stream_response method was called (not generate_response)
    assert content_generator.stream_response_call_count == 1
    assert content_generator.generate_response_call_count == 0
    
    # Verify that content events were yielded
    content_events = [e for e in events if e.type == TurnEventType.CONTENT]
    assert len(content_events) > 0
    
    # Verify completion
    finished_events = [e for e in events if e.type == TurnEventType.FINISHED]
    assert len(finished_events) > 0


@pytest.mark.asyncio
async def test_turn_manager_with_streaming_disabled():
    """Test that turn manager uses non-streaming path when streaming_enabled=False."""
    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    
    # Create content generator that tracks which method is called
    content_generator = StreamingTestContentGenerator(
        response_content="Non-streaming test response",
        has_tool_calls=False
    )
    
    # Create turn manager
    turn_manager = TurnManager(mock_mcp_client, content_generator)
    
    # Create a prompt object with streaming disabled
    prompt_obj = PromptObject.create(
        content="Test prompt",
        streaming_enabled=False  # This should trigger non-streaming path
    )
    
    # Run the turn and collect events
    events = []
    async for event in turn_manager.run_turn(prompt_obj):
        events.append(event)
    
    # Verify that the generate_response method was called (not stream_response)
    assert content_generator.generate_response_call_count == 1
    assert content_generator.stream_response_call_count == 0
    
    # Verify that at least one content event was yielded (from the complete response)
    content_events = [e for e in events if e.type == TurnEventType.CONTENT]
    assert len(content_events) >= 1
    
    # Verify completion
    finished_events = [e for e in events if e.type == TurnEventType.FINISHED]
    assert len(finished_events) > 0


@pytest.mark.asyncio 
async def test_turn_manager_with_tool_calls_streaming():
    """Test that turn manager properly handles tool calls in streaming mode."""
    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.get_execution_result.return_value = ToolResult(
        tool_name="test_tool",
        llm_content="Tool execution result",
        return_display="Tool execution result",
        success=True
    )
    
    # Create mock tool execution manager
    mock_tool_execution_manager = AsyncMock()
    tool_result = ToolResult(
        tool_name="test_tool",
        llm_content="Tool execution result",
        return_display="Tool execution result", 
        success=True
    )
    mock_tool_execution_manager.execute_internal_tool = AsyncMock(return_value=tool_result)
    
    # Create content generator that returns tool calls
    content_generator = StreamingTestContentGenerator(
        response_content="Response with tool call",
        has_tool_calls=True,
        tool_call_name="test_tool"
    )
    
    # Create turn manager and set tool execution manager
    turn_manager = TurnManager(mock_mcp_client, content_generator)
    turn_manager.tool_execution_manager = mock_tool_execution_manager
    
    # Create a prompt object with streaming enabled
    prompt_obj = PromptObject.create(
        content="Test prompt with tool call",
        streaming_enabled=True
    )
    
    # Run the turn and collect events
    events = []
    async for event in turn_manager.run_turn(prompt_obj):
        events.append(event)
    
    # Verify that streaming path was used
    assert content_generator.stream_response_call_count == 1
    
    # Verify that tool call events were generated
    tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
    tool_response_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE]
    
    assert len(tool_request_events) >= 1
    assert len(tool_response_events) >= 1
    
    # Verify completion
    finished_events = [e for e in events if e.type == TurnEventType.FINISHED]
    assert len(finished_events) > 0


@pytest.mark.asyncio
async def test_turn_manager_with_tool_calls_non_streaming():
    """Test that turn manager properly handles tool calls in non-streaming mode."""
    # Create mock MCP client
    mock_mcp_client = AsyncMock()
    mock_mcp_client.get_execution_result.return_value = ToolResult(
        tool_name="test_tool",
        llm_content="Tool execution result",
        return_display="Tool execution result",
        success=True
    )
    
    # Create mock tool execution manager
    mock_tool_execution_manager = AsyncMock()
    tool_result = ToolResult(
        tool_name="test_tool",
        llm_content="Tool execution result",
        return_display="Tool execution result",
        success=True
    )
    mock_tool_execution_manager.execute_internal_tool = AsyncMock(return_value=tool_result)
    
    # Create content generator that returns tool calls
    content_generator = StreamingTestContentGenerator(
        response_content="Response with tool call",
        has_tool_calls=True,
        tool_call_name="test_tool"
    )
    
    # Create turn manager and set tool execution manager
    turn_manager = TurnManager(mock_mcp_client, content_generator)
    turn_manager.tool_execution_manager = mock_tool_execution_manager
    
    # Create a prompt object with streaming disabled
    prompt_obj = PromptObject.create(
        content="Test prompt with tool call",
        streaming_enabled=False
    )
    
    # Run the turn and collect events
    events = []
    async for event in turn_manager.run_turn(prompt_obj):
        events.append(event)
    
    # Verify that non-streaming path was used (streaming path was not used)
    # The content generator may be called multiple times during recursive tool handling
    assert content_generator.stream_response_call_count == 0  # No streaming calls
    assert content_generator.generate_response_call_count >= 1  # At least one non-streaming call
    
    # Verify that tool call events were generated
    tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
    tool_response_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_RESPONSE]
    
    assert len(tool_request_events) >= 1
    assert len(tool_response_events) >= 1
    
    # Verify completion
    finished_events = [e for e in events if e.type == TurnEventType.FINISHED]
    assert len(finished_events) > 0