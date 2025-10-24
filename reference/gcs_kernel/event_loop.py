"""
Master Event Loop (Turn Processing) implementation for the GCS Kernel.

This module implements the core event loop that processes streaming AI responses
and tool execution events in real-time, inspired by Qwen Code's event loop architecture.
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from gcs_kernel.models import Event


class EventLoop:
    """
    Master Event Loop (Turn Processing) that handles streaming AI responses
    and tool execution events in real-time.
    """
    
    def __init__(self):
        """Initialize the event loop with necessary components."""
        self.is_running = False
        self.event_queue = asyncio.Queue()
        self.handlers: Dict[str, Callable] = {}
        self.turn_queue = asyncio.Queue()  # For processing AI response turns
        self.logger = None  # Will be set by kernel

    async def run(self):
        """Main event loop that processes streaming AI responses and tool execution events in real-time."""
        self.is_running = True
        
        # Start processing tasks concurrently
        await asyncio.gather(
            self._process_events(),
            self._process_turns(),
            return_exceptions=True
        )

    async def shutdown(self):
        """Gracefully shut down the event loop."""
        self.is_running = False

    async def _process_events(self):
        """Process kernel events in the main event loop."""
        while self.is_running:
            try:
                # Non-blocking event processing with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                await self._handle_event(event)
            except asyncio.TimeoutError:
                # Continue loop even if no events
                continue
            except Exception as e:
                # Error handling without stopping the loop
                if self.logger:
                    self.logger.error(f"Error in event processing: {e}")

    async def _process_turns(self):
        """Process AI response turns in the event loop."""
        while self.is_running:
            try:
                # Process AI response turns separately
                turn = await asyncio.wait_for(self.turn_queue.get(), timeout=0.1)
                await self._handle_turn(turn)
            except asyncio.TimeoutError:
                # Continue loop even if no turns
                continue
            except Exception as e:
                # Error handling without stopping the loop
                if self.logger:
                    self.logger.error(f"Error in turn processing: {e}")

    async def _handle_event(self, event: Event):
        """Handle an event based on its type."""
        handler = self.handlers.get(event.type)
        if handler:
            await handler(event)
        else:
            if self.logger:
                self.logger.warning(f"No handler for event type: {event.type}")

    async def _handle_turn(self, turn):
        """Handle AI response turn processing."""
        # Process the turn based on its content (Content Events, Tool Call Events, etc.)
        pass

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for a specific event type."""
        self.handlers[event_type] = handler

    def submit_event(self, event: Event):
        """Submit an event to the event loop for processing."""
        self.event_queue.put_nowait(event)

    def submit_turn(self, turn_data: Any):
        """Submit an AI response turn to the event loop for processing."""
        self.turn_queue.put_nowait(turn_data)