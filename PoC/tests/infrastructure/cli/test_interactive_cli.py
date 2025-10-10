"""
Test for the interactive CLI functionality, specifically the asyncio import issue.

This test reproduces the error from the issue: "local variable 'asyncio' referenced before assignment"
"""
import pytest
import sys
from unittest.mock import MagicMock, patch

from cogniscient.ui.cli.interactive_mode import InteractiveCLI
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings


def test_asyncio_import_issue_reproduction():
    """
    Test to reproduce the asyncio import issue.
    
    This test verifies that the 'local variable 'asyncio' referenced before assignment'
    error does not occur when checking the status in interactive CLI.
    """
    # Initialize GCS runtime
    gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    
    # Create the interactive CLI instance
    interactive_cli = InteractiveCLI(gcs)
    
    # Mock the session manager to avoid config service issues
    mock_session_info = {
        "start_time": "2023-01-01",
        "interaction_count": 1,
        "active_config": "default",
        "active_agents": [],
        "session_context": {}
    }
    
    # Mock session manager methods that have issues
    interactive_cli.session_manager.get_session_info = lambda: mock_session_info
    interactive_cli.session_manager.get_recent_context = lambda n: []
    
    # Mock the _get_auth_status method to avoid actual async execution
    async def mock_get_auth_status():
        return "Valid credentials found"
    
    # Temporarily replace the method
    original_method = interactive_cli._get_auth_status
    interactive_cli._get_auth_status = mock_get_auth_status
    
    try:
        # This should not raise an "asyncio referenced before assignment" error
        user_input = "status"
        result = interactive_cli.process_input(user_input)
        
        # Verify that we get a response without asyncio errors
        assert "System Status:" in result
        assert "Current provider:" in result
    finally:
        # Restore original method
        interactive_cli._get_auth_status = original_method


def test_interactive_cli_process_input():
    """
    Test that the interactive CLI can process basic commands without errors.
    """
    # Initialize GCS runtime
    gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    
    # Create the interactive CLI instance
    interactive_cli = InteractiveCLI(gcs)
    
    # Mock session manager methods that have issues
    mock_session_info = {
        "start_time": "2023-01-01",
        "interaction_count": 1,
        "active_config": "default",
        "active_agents": [],
        "session_context": {}
    }
    
    interactive_cli.session_manager.get_session_info = lambda: mock_session_info
    interactive_cli.session_manager.get_recent_context = lambda n: []
    
    # Test basic help command
    result = interactive_cli.process_input("help")
    assert "Cogniscient Interactive CLI Help:" in result
    
    # Test status command
    result = interactive_cli.process_input("status")
    assert "System Status:" in result
    
    # Test handling of empty input
    result = interactive_cli.process_input("")
    assert result == ""
    
    # Test handling of unknown command (this would normally go to LLM processing)
    # This should not raise an asyncio error
    try:
        result = interactive_cli.process_input("hello?")
        # If we get here without exception, the asyncio issue is fixed
        # The LLM might still fail for other reasons, but not asyncio
        assert True  # Successfully processed without asyncio error
    except NameError as e:
        if "asyncio" in str(e):
            assert False, f"asyncio error still exists: {e}"
        else:
            # Some other error is acceptable as it's not the asyncio issue
            pass


@pytest.mark.asyncio
async def test_async_methods_in_interactive_cli():
    """
    Test the async methods in the interactive CLI.
    """
    gcs = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    interactive_cli = InteractiveCLI(gcs)
    
    # Test _get_auth_status method
    auth_status = await interactive_cli._get_auth_status()
    assert isinstance(auth_status, str)
    
    # Test _switch_provider method
    result = await interactive_cli._switch_provider("litellm")
    assert "Provider switched to: litellm" in result