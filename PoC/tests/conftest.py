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
    print("\nRunning cleanup after test session...")
    # Import and run the comprehensive cleanup for LiteLLM clients
    try:
        import litellm
        import asyncio
        import gc
        
        # Process any pending logs to prevent the async_success_handler warning
        if hasattr(litellm, 'batch_logging'):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(litellm.batch_logging())
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        # Try to properly close module-level clients
        # Check if the close method is async (coroutine)
        if hasattr(litellm, 'module_level_aclient'):
            try:
                close_method = litellm.module_level_aclient.close
                if asyncio.iscoroutinefunction(close_method):
                    # If it's a coroutine, run it in a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(close_method())
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
                else:
                    # If it's not a coroutine, call it directly
                    close_method()
            except Exception:
                pass  # Ignore errors during close attempt

        if hasattr(litellm, 'module_level_client'):
            try:
                litellm.module_level_client.close()
            except Exception:
                pass  # Ignore errors during close attempt

        # Try to properly close cached clients in LLMClientCache
        if hasattr(litellm, 'in_memory_llm_clients_cache'):
            try:
                # Get the cached clients and close them
                cache = litellm.in_memory_llm_clients_cache
                if hasattr(cache, 'cache_dict'):
                    for key, cached_client in list(cache.cache_dict.items()):
                        if hasattr(cached_client, 'close'):
                            try:
                                close_method = cached_client.close
                                if asyncio.iscoroutinefunction(close_method):
                                    # Run in a separate event loop for cached async clients
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        loop.run_until_complete(close_method())
                                    finally:
                                        loop.close()
                                        asyncio.set_event_loop(None)
                                else:
                                    close_method()
                            except Exception:
                                pass  # Ignore errors during close attempt
                    # Clear the cache after closing
                    cache.cache_dict.clear()
            except Exception:
                pass  # Ignore errors during cache cleanup

        # Try to properly close any async clients
        if hasattr(litellm, 'aclient_session') and litellm.aclient_session:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(litellm.aclient_session.aclose())
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        # Clear callback lists to prevent async handlers from running
        if hasattr(litellm, 'success_callback'):
            litellm.success_callback = []
        if hasattr(litellm, 'failure_callback'):
            litellm.failure_callback = []
        if hasattr(litellm, '_async_success_callback'):
            litellm._async_success_callback = []
        if hasattr(litellm, '_async_failure_callback'):
            litellm._async_failure_callback = []

        # Force garbage collection to clean up any remaining resources
        gc.collect()

    except Exception as e:
        print(f"Error during cleanup of LiteLLM clients: {e}")
    
    # Force garbage collection to clean up any remaining resources
    gc.collect()