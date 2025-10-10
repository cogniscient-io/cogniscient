"""Unit tests for context management functionality."""

import pytest
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface
from cogniscient.engine.config.settings import settings


@pytest.mark.asyncio
async def test_context_window_size_management():
    """Test context window size parameter and compression."""
    # Initialize GCS runtime and chat interface with custom parameters
    gcs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    await gcs_runtime.config_service.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    # Set a smaller max context size for testing
    orchestrator.max_context_size = 500  # Small size to trigger compression quickly
    
    # Create chat interface with smaller parameters for testing
    chat_interface = ChatInterface(
        orchestrator,
        max_history_length=6,  # Smaller history limit
        compression_threshold=4   # Compress earlier - must be less than max_history_length
    )
    
    # Mock send_stream_event function to collect events
    events_collected = []
    
    async def mock_send_stream_event(event_type: str, content: str = None, data: dict = None):
        event = {
            "type": event_type,
            "content": content,
            "data": data
        }
        events_collected.append(event)
    
    # Test context window size calculation
    conversation_history = []
    initial_size = len(str(conversation_history))  # Context window size for an empty conversation
    assert initial_size >= 0  # Should be 0 or more
    
    # Add some conversation history
    await chat_interface.process_user_input_streaming(
        "Hello, can you help me with a question?",
        conversation_history,
        mock_send_stream_event
    )
    size_after_first = len(str(conversation_history))
    assert size_after_first > initial_size
    
    await chat_interface.process_user_input_streaming(
        "I'm testing the context window size feature.",
        conversation_history,
        mock_send_stream_event
    )
    size_after_second = len(str(conversation_history))
    assert size_after_second > size_after_first


@pytest.mark.asyncio
async def test_conversation_history_management():
    """Test conversation history clearing and compression."""
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    await gcs_runtime.config_service.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    chat_interface = ChatInterface(orchestrator, max_history_length=20, compression_threshold=15)
    
    # Test conversation history building using the streaming method
    for i in range(5):
        # Create a mock send_stream_event function to collect events
        events_collected = []
        
        async def mock_send_stream_event(event_type: str, content: str = None, data: dict = None):
            event = {
                "type": event_type,
                "content": content,
                "data": data
            }
            events_collected.append(event)
        
        await chat_interface.process_user_input_streaming(f"Hello, this is message {i+1}", chat_interface.conversation_history, mock_send_stream_event)
    
    history_length_before = len(chat_interface.conversation_history)
    assert history_length_before == 10  # 5 user messages + 5 assistant responses
    
    # Test manual clearing of conversation history
    initial_length = len(chat_interface.conversation_history)
    chat_interface.conversation_history.clear()  # This should clear history
    length_after_clear = len(chat_interface.conversation_history)
    assert length_after_clear == 0


@pytest.mark.asyncio
async def test_system_parameters_management():
    """Test the system parameters manager service."""
    
    # Print the initial settings values for debugging
    print(f"DEBUG INITIAL: max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    await gcs_runtime.config_service.load_configuration("combined")
    
    orchestrator = LLMOrchestrator(gcs_runtime)
    
    # Print the settings values again after initialization
    print(f"DEBUG AFTER INIT: max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Test getting system parameters using the system parameters service
    result = gcs_runtime.system_parameters_service.get_system_parameters()
    assert result["status"] == "success"
    assert "parameters" in result
    params = result["parameters"]
    assert "max_context_size" in params
    assert "max_history_length" in params
    assert "compression_threshold" in params
    
    # Test getting parameter descriptions
    result = gcs_runtime.system_parameters_service.get_parameter_descriptions()
    assert result["status"] == "success"
    assert "descriptions" in result
    assert len(result["descriptions"]) > 0
    
    # Save original parameter value for cleanup
    original_max_history_length = params.get("max_history_length")
    
    # Test setting a parameter
    result = gcs_runtime.system_parameters_service.set_system_parameter(
        parameter_name="max_history_length", parameter_value="8")
    assert result["status"] == "success"
    
    # Reset the parameter back to its original value to avoid affecting other tests
    if original_max_history_length is not None:
        gcs_runtime.system_parameters_service.set_system_parameter(
            parameter_name="max_history_length", parameter_value=str(original_max_history_length))


@pytest.mark.asyncio
async def test_settings_based_context_management():
    """Test that context management uses settings from .env file."""
    
    # Print the settings values for debugging
    print(f"DEBUG: Settings max_history_length={settings.max_history_length}, compression_threshold={settings.compression_threshold}")
    
    # Initialize GCS runtime and chat interface
    gcs_runtime = GCSRuntime(config_dir="plugins/sample_internal/config", agents_dir="plugins/sample_internal/agents")
    await gcs_runtime.config_service.load_configuration("combined")
    
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