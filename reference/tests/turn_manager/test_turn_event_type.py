"""
Tests for the TurnEventType enum in the AI Orchestrator.
"""

import pytest
from services.ai_orchestrator.turn_manager import TurnEventType


class TestTurnEventType:
    """Test the TurnEventType enum."""
    
    def test_turn_event_type_values(self):
        """Test that all TurnEventType values are correct."""
        assert TurnEventType.CONTENT == "content"
        assert TurnEventType.TOOL_CALL_REQUEST == "tool_call_request"
        assert TurnEventType.TOOL_CALL_RESPONSE == "tool_call_response"
        assert TurnEventType.FINISHED == "finished"
        assert TurnEventType.ERROR == "error"
    
    def test_turn_event_type_membership(self):
        """Test that all expected event types are in the enum."""
        expected_types = {"content", "tool_call_request", "tool_call_response", "finished", "error"}
        actual_types = {event_type.value for event_type in TurnEventType}
        
        assert actual_types == expected_types
    
    def test_turn_event_type_str_representation(self):
        """Test string representation of TurnEventType values."""
        assert TurnEventType.CONTENT.value == "content"
        assert TurnEventType.TOOL_CALL_REQUEST.value == "tool_call_request"
        assert TurnEventType.TOOL_CALL_RESPONSE.value == "tool_call_response"
        assert TurnEventType.FINISHED.value == "finished"
        assert TurnEventType.ERROR.value == "error"