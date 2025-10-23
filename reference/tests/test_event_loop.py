"""
Test suite for the GCS Kernel Event Loop.

This module contains tests for the EventLoop component of the GCS Kernel.
"""
import pytest
import asyncio
from gcs_kernel.event_loop import EventLoop
from gcs_kernel.models import Event


@pytest.mark.asyncio
async def test_event_loop_initialization():
    """Test that EventLoop initializes properly."""
    event_loop = EventLoop()
    
    assert event_loop.is_running is False
    assert event_loop.event_queue is not None
    assert event_loop.handlers == {}
    assert event_loop.turn_queue is not None


@pytest.mark.asyncio
async def test_event_submission():
    """Test submitting events to the event loop."""
    event_loop = EventLoop()
    
    # Create a test event
    test_event = Event(type="test_event", data={"test": "data"})
    
    # Submit the event
    event_loop.submit_event(test_event)
    
    # Verify it's in the queue
    assert event_loop.event_queue.qsize() == 1


@pytest.mark.asyncio
async def test_turn_submission():
    """Test submitting turns to the event loop."""
    event_loop = EventLoop()
    
    # Submit a test turn
    event_loop.submit_turn({"turn_data": "test"})
    
    # Verify it's in the queue
    assert event_loop.turn_queue.qsize() == 1