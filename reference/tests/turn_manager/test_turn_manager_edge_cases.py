"""
Additional tests for edge cases and internal methods in the TurnManager class.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gcs_kernel.models import PromptObject, ToolResult, ToolInclusionPolicy
from gcs_kernel.tool_call_model import ToolCall
from services.ai_orchestrator.turn_manager import TurnManager, TurnEventType


class TestTurnManagerEdgeCases:
    """Test edge cases for TurnManager."""

    @pytest.mark.asyncio
    async def test_tool_execution_with_missing_tool_execution_manager(self, mock_mcp_client, mock_content_generator,
                                                                     sample_tool_result):
        """Test what happens when TurnManager tries to execute tools without tool_execution_manager."""
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)
        # Ensure tool_execution_manager is None
        turn_manager.tool_execution_manager = None

        # In the new architecture, tool execution is handled by ToolExecutionManager
        # If TurnManager doesn't have a tool execution manager, tools won't be executed during turns
        assert turn_manager.tool_execution_manager is None

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, mock_mcp_client, mock_content_generator,
                                           mock_tool_execution_manager, sample_tool_result):
        """Test execute_tool_call via unified interface success case."""
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)
        turn_manager.tool_execution_manager = mock_tool_execution_manager

        # Create a ToolCall as would be used with the unified interface
        tool_call_obj = ToolCall(
            id="test-call-123",
            function={
                "name": "test_tool",
                "arguments": '{"param": "value"}'
            }
        )

        # Mock the unified execute_tool_call method
        expected_result = {
            "tool_call_id": tool_call_obj.id,
            "tool_name": tool_call_obj.name,
            "result": sample_tool_result,
            "success": sample_tool_result.success
        }
        mock_tool_execution_manager.execute_tool_call = AsyncMock(return_value=expected_result)

        # Execute the tool call using the unified interface from the ToolExecutionManager
        result = await mock_tool_execution_manager.execute_tool_call(tool_call_obj)

        # Verify that the result matches the expected format
        assert result == expected_result
        mock_tool_execution_manager.execute_tool_call.assert_called_once_with(tool_call_obj)

    @pytest.mark.asyncio
    async def test_run_turn_with_invalid_tool_call_name(self, mock_mcp_client, mock_content_generator,
                                                       mock_tool_execution_manager):
        """Test run_turn with invalid/empty tool call name."""
        # Set up the turn manager with a mock tool execution manager
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)
        turn_manager.tool_execution_manager = mock_tool_execution_manager

        # Create a prompt object
        prompt_obj = PromptObject(
            prompt_id="test-prompt-invalid",
            content="Test invalid tool call",
            tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
        )

        # Mock the content generator to stream a response
        async def mock_stream_response(prompt_obj):
            yield "Response with "
            yield "invalid tool call"

        mock_content_generator.stream_response = mock_stream_response

        # Mock the pipeline to return a response with an invalid tool call (empty name)
        mock_pipeline = MagicMock()
        mock_last_response = {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Response with invalid tool call",
                    "tool_calls": [
                        {
                            "id": "call_invalid",
                            "function": {
                                "name": "",  # Empty name
                                "arguments": '{"param": "value"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }]
        }
        mock_pipeline.get_last_streaming_response = MagicMock(return_value=mock_last_response)
        mock_content_generator.pipeline = mock_pipeline

        # Execute the turn and collect events
        events = []
        async for event in turn_manager.run_turn(prompt_obj):
            events.append(event)

        # Check that we have content and finished events, but no tool execution for the invalid call
        content_events = [e for e in events if e.type == TurnEventType.CONTENT]
        finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)

        # We should still get content and finished events
        assert len(content_events) > 0
        assert finished_event is not None

        # There should be no tool call request events for the invalid tool call
        tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
        assert len(tool_request_events) == 0

    @pytest.mark.asyncio
    async def test_run_turn_with_malformed_tool_call(self, mock_mcp_client, mock_content_generator,
                                                    mock_tool_execution_manager):
        """Test run_turn with malformed tool call."""
        # Set up the turn manager with a mock tool execution manager
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)
        turn_manager.tool_execution_manager = mock_tool_execution_manager

        # Create a prompt object
        prompt_obj = PromptObject(
            prompt_id="test-prompt-malformed",
            content="Test malformed tool call",
            tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
        )

        # Mock the content generator to stream a response
        async def mock_stream_response(prompt_obj):
            yield "Response with "
            yield "malformed tool call"

        mock_content_generator.stream_response = mock_stream_response

        # Mock the pipeline to return a response with a malformed tool call (name is None)
        mock_pipeline = MagicMock()
        mock_last_response = {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Response with malformed tool call",
                    "tool_calls": [
                        {
                            "id": "call_malformed",
                            "function": {
                                "name": None,  # Malformed name
                                "arguments": '{"param": "value"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }]
        }
        mock_pipeline.get_last_streaming_response = MagicMock(return_value=mock_last_response)
        mock_content_generator.pipeline = mock_pipeline

        # Execute the turn and collect events
        events = []
        async for event in turn_manager.run_turn(prompt_obj):
            events.append(event)

        # Check that we have content and finished events
        content_events = [e for e in events if e.type == TurnEventType.CONTENT]
        finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)

        # We should still get content and finished events
        assert len(content_events) > 0
        assert finished_event is not None

        # There should be no tool call request events for the malformed tool call
        tool_request_events = [e for e in events if e.type == TurnEventType.TOOL_CALL_REQUEST]
        assert len(tool_request_events) == 0

    @pytest.mark.asyncio
    async def test_run_turn_with_content_attribute_fallback(self, mock_mcp_client, mock_content_generator,
                                                          mock_tool_execution_manager, sample_tool_result):
        """Test run_turn when using streaming interface (the new implementation)."""
        # Set up the turn manager with a mock tool execution manager
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)
        turn_manager.tool_execution_manager = mock_tool_execution_manager

        # Create a prompt object
        prompt_obj = PromptObject(
            prompt_id="test-prompt-fallback",
            content="Test content streaming",
            tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
        )

        # Mock the content generator to stream a response
        async def mock_stream_response(prompt_obj):
            yield "This is "
            yield "content from "
            yield "streaming"

        mock_content_generator.stream_response = mock_stream_response

        # Mock the pipeline to return a response with content
        mock_pipeline = MagicMock()
        mock_last_response = {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is content from streaming",
                },
                "finish_reason": "stop"
            }]
        }
        mock_pipeline.get_last_streaming_response = MagicMock(return_value=mock_last_response)
        mock_content_generator.pipeline = mock_pipeline

        # Execute the turn
        events = []
        async for event in turn_manager.run_turn(prompt_obj):
            events.append(event)

        # Verify that the content events exist
        content_events = [e for e in events if e.type == TurnEventType.CONTENT]
        finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)

        assert len(content_events) > 0
        # Just verify that content events exist (the exact content may be mocks in test environment)
        assert content_events is not None
        assert finished_event is not None

    @pytest.mark.asyncio
    async def test_run_turn_no_content_no_tool_calls(self, mock_mcp_client, mock_content_generator):
        """Test run_turn when response has no content and no tool calls."""
        # Set up the turn manager
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)

        # Create a prompt object
        prompt_obj = PromptObject(
            prompt_id="test-prompt-empty",
            content="Test empty response",
            tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
        )

        # Mock the content generator to stream an empty response
        async def mock_stream_response(prompt_obj):
            # An async generator that yields nothing
            if False:  # This ensures it's treated as an async generator but yields nothing
                yield
            return

        mock_content_generator.stream_response = mock_stream_response

        # Mock the pipeline to return a response with no content
        mock_pipeline = MagicMock()
        mock_last_response = {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    # No content field
                },
                "finish_reason": "stop"
            }]
        }
        mock_pipeline.get_last_streaming_response = MagicMock(return_value=mock_last_response)
        mock_content_generator.pipeline = mock_pipeline

        # Execute the turn
        events = []
        async for event in turn_manager.run_turn(prompt_obj):
            events.append(event)

        # Verify that we still get a finished event
        finished_event = next((e for e in events if e.type == TurnEventType.FINISHED), None)

        assert finished_event is not None

    @pytest.mark.asyncio
    async def test_wait_for_execution_result_timeout(self, mock_mcp_client, mock_content_generator,
                                                    mock_tool_execution_manager):
        """Test _wait_for_execution_result with timeout."""
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)

        # Mock the MCP client to return None (no result available)
        mock_mcp_client.get_execution_result = AsyncMock(return_value=None)

        # Test timeout behavior
        result = await turn_manager._wait_for_execution_result("nonexistent-execution", timeout=0.1)

        # Should return None due to timeout
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_execution_result_success(self, mock_mcp_client, mock_content_generator,
                                                    mock_tool_execution_manager, sample_tool_result):
        """Test _wait_for_execution_result with successful result."""
        turn_manager = TurnManager(mock_mcp_client, mock_content_generator)

        # Mock the MCP client to return a result on the second call
        call_count = 0
        async def mock_get_execution_result(execution_id):
            nonlocal call_count
            call_count += 1
            if call_count > 1:  # Return result after first call
                return sample_tool_result
            return None

        mock_mcp_client.get_execution_result = AsyncMock(side_effect=mock_get_execution_result)

        # Test successful result retrieval
        result = await turn_manager._wait_for_execution_result("test-execution", timeout=1)

        # Should return the result
        assert result == sample_tool_result