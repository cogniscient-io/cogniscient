"""
Tests for the TurnEvent class in the AI Orchestrator.
"""

import pytest
from gcs_kernel.models import ToolResult
from services.ai_orchestrator.turn_manager import TurnEvent, TurnEventType


class TestTurnEvent:
    """Test the TurnEvent class."""
    
    def test_turn_event_creation_with_content(self):
        """Test creating a TurnEvent with content."""
        event = TurnEvent(TurnEventType.CONTENT, "Hello, world!")
        
        assert event.type == TurnEventType.CONTENT
        assert event.value == "Hello, world!"
        assert event.error is None
    
    def test_turn_event_creation_with_error(self):
        """Test creating a TurnEvent with an error."""
        error = Exception("Test error")
        event = TurnEvent(TurnEventType.ERROR, error=error)
        
        assert event.type == TurnEventType.ERROR
        assert event.value is None
        assert event.error == error
    
    def test_turn_event_creation_with_tool_call_request(self):
        """Test creating a TurnEvent for tool call request."""
        tool_data = {
            "call_id": "test-call-123",
            "name": "test_tool",
            "arguments": '{"param": "value"}'
        }
        event = TurnEvent(TurnEventType.TOOL_CALL_REQUEST, tool_data)
        
        assert event.type == TurnEventType.TOOL_CALL_REQUEST
        assert event.value == tool_data
        assert event.error is None
    
    def test_turn_event_creation_with_tool_call_response(self):
        """Test creating a TurnEvent for tool call response."""
        tool_result = ToolResult(
            tool_name="test_tool",
            llm_content="Result from tool",
            return_display="Result from tool",
            success=True
        )
        response_data = {
            "call_id": "test-call-123",
            "result": tool_result
        }
        event = TurnEvent(TurnEventType.TOOL_CALL_RESPONSE, response_data)
        
        assert event.type == TurnEventType.TOOL_CALL_RESPONSE
        assert event.value == response_data
        assert event.error is None
    
    def test_turn_event_creation_with_finished(self):
        """Test creating a TurnEvent for finished status."""
        event = TurnEvent(TurnEventType.FINISHED)
        
        assert event.type == TurnEventType.FINISHED
        assert event.value is None
        assert event.error is None