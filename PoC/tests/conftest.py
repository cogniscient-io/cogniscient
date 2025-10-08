"""
Pytest configuration file for the test suite.
"""
import asyncio
import pytest
import gc
from typing import Dict, Any, Optional


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Called after whole test run finished, right before returning the exit status to the system.
    This is where we can perform cleanup tasks.
    """
    print("Running cleanup after test session...")
    # Import and run the cleanup for LiteLLM clients
    try:
        import litellm
        # We'll run the cleanup in a new event loop to ensure it executes properly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(litellm.close_litellm_async_clients())
        finally:
            loop.close()
            # Explicitly clear the current event loop
            asyncio.set_event_loop(None)
    except Exception as e:
        print(f"Error during cleanup of LiteLLM clients: {e}")
    
    # Force garbage collection to clean up any remaining resources
    gc.collect()