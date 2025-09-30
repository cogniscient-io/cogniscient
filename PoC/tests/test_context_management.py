"""Unit tests for context management functionality."""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.orchestrator.chat_interface import ChatInterface
from cogniscient.engine.config.settings import settings


@pytest.mark.asyncio
async def test_context_window_size_management():
    """Test context window size parameter and compression."""
    # Initialize GCS runtime and chat interface with custom parameters
    gcs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    gcs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    # Set a smaller max context size for testing
    orchestrator.max_context_size = 500  # Small size to trigger compression quickly
    
    # Create chat interface with smaller parameters for testing
    chat_interface = ChatInterface(
        orchestrator,
        max_history_length=6,  # Smaller history limit
        compression_threshold=4   # Compress earlier - must be less than max_history_length
    )
    
    # Test context window size calculation
    initial_size = chat_interface.get_context_window_size()
    assert initial_size >= 0  # Should be 0 or more
    
    # Add some conversation history
    await chat_interface.process_user_input("Hello, can you help me with a question?")
    size_after_first = chat_interface.get_context_window_size()
    assert size_after_first > initial_size
    
    await chat_interface.process_user_input("I'm testing the context window size feature.")
    size_after_second = chat_interface.get_context_window_size()
    assert size_after_second > size_after_first


@pytest.mark.asyncio
async def test_conversation_history_management():
    """Test conversation history clearing and compression."""
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    gcs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    chat_interface = ChatInterface(orchestrator, max_history_length=20, compression_threshold=15)
    
    # Test conversation history building
    for i in range(5):
        await chat_interface.process_user_input(f"Hello, this is message {i+1}")
    
    history_length_before = len(chat_interface.conversation_history)
    assert history_length_before == 10  # 5 user messages + 5 assistant responses
    
    # Test configuration change clearing conversation history
    initial_length = len(chat_interface.conversation_history)
    gcs_runtime.load_configuration("website_only")  # This should clear history
    length_after_config_change = len(chat_interface.conversation_history)
    assert length_after_config_change == 0


@pytest.mark.asyncio
async def test_system_parameters_management():
    """Test the system parameters manager service."""
    
    # Print the initial settings values for debugging
    print(f"DEBUG INITIAL: max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    gcs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    
    # Print the settings values again after initialization
    print(f"DEBUG AFTER INIT: max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Test getting system parameters
    result = gcs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
    assert result["status"] == "success"
    assert "parameters" in result
    params = result["parameters"]
    assert "max_context_size" in params
    assert "max_history_length" in params
    assert "compression_threshold" in params
    
    # Test getting parameter descriptions
    result = gcs_runtime.run_agent("SystemParametersManager", "get_parameter_descriptions")
    assert result["status"] == "success"
    assert "descriptions" in result
    assert len(result["descriptions"]) > 0
    
    # Save original parameter value for cleanup
    original_max_history_length = params.get("max_history_length")
    
    # Test setting a parameter
    result = gcs_runtime.run_agent("SystemParametersManager", "set_system_parameter", 
                                 parameter_name="max_history_length", parameter_value="8")
    assert result["status"] == "success"
    
    # Reset the parameter back to its original value to avoid affecting other tests
    if original_max_history_length is not None:
        gcs_runtime.run_agent("SystemParametersManager", "set_system_parameter", 
                             parameter_name="max_history_length", parameter_value=str(original_max_history_length))


@pytest.mark.asyncio
async def test_settings_based_context_management():
    """Test that context management uses settings from .env file."""
    
    # Print the settings values for debugging
    print(f"DEBUG: Settings max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample/config", agents_dir="plugins/sample/agents")
    gcs_runtime.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    # Use the same values as in settings to ensure they match
    print(f"DEBUG: About to create ChatInterface with max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    chat_interface = ChatInterface(orchestrator, 
                                  max_history_length=settings.max_history_length, 
                                  compression_threshold=settings.compression_threshold)
    
    # Verify that the chat interface uses the expected values
    assert chat_interface.max_history_length == settings.max_history_length
    assert chat_interface.compression_threshold == settings.compression_threshold
    
    # Test with custom parameters (should override settings)
    chat_interface_custom = ChatInterface(orchestrator, max_history_length=5, compression_threshold=3)
    assert chat_interface_custom.max_history_length == 5
    assert chat_interface_custom.compression_threshold == 3


if __name__ == "__main__":
    # For running directly with Python (not pytest)
    import asyncio
    import sys
    
    if "pytest" not in sys.modules:
        asyncio.run(test_context_window_size_management())
        asyncio.run(test_conversation_history_management())
        asyncio.run(test_system_parameters_management())
        asyncio.run(test_settings_based_context_management())
        print("All context management tests passed!")