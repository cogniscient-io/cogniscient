#!/usr/bin/env python3
"""
Utility to handle graceful shutdown and prevent aiohttp warnings during exit
"""

import atexit
import signal
import sys
import gc
import asyncio
import logging
from typing import Callable, Any


class GracefulShutdown:
    """
    Handles graceful shutdown to prevent aiohttp ClientSession warnings during exit.
    """
    
    def __init__(self):
        self._shutdown_handlers = []
        self._setup_signal_handlers()
        self._setup_exit_handler()
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        # Handle SIGTERM and SIGINT for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _setup_exit_handler(self):
        """Setup atexit handler for graceful shutdown."""
        atexit.register(self._perform_cleanup)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, performing graceful shutdown...")
        self._perform_cleanup()
        sys.exit(0)
        
    def _perform_cleanup(self):
        """Perform all cleanup tasks."""
        # Run all registered shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # For async handlers, try to run them if there's a loop
                    try:
                        loop = asyncio.get_event_loop()
                        if not loop.is_closed():
                            loop.run_until_complete(handler())
                    except RuntimeError:
                        # No event loop available, skip async handler
                        pass
                else:
                    # Synchronous handler
                    handler()
            except Exception:
                pass  # Ignore errors during shutdown
        
        # Force garbage collection to clean up any remaining resources
        gc.collect()
        
        # Properly shutdown logging
        try:
            logging.shutdown()
        except:
            pass
    
    def register_shutdown_handler(self, handler: Callable[[], Any]):
        """Register a function to be called during shutdown."""
        self._shutdown_handlers.append(handler)


# Global instance to handle shutdowns
graceful_shutdown = GracefulShutdown()