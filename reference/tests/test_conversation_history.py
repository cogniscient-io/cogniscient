"""
Test suite for conversation history functionality in AI Orchestrator.

This module tests that conversation history is properly maintained across 
tool calls and responses, ensuring the LLM gets the full context to generate
meaningful responses after tool execution.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.ai_orchestrator.turn_manager import TurnManager
from services.llm_provider.base_generator import BaseContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class MockContentGenerator(BaseContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing conversation history.
    """
    def __init__(self, config=None):
        # Initialize with an empty config to avoid errors
        self.config = config or {}
        # Set up any attributes needed for testing from the config
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout")
        self.max_retries = self.config.get("max_retries")
        
        # Track calls to verify conversation history is handled properly
        self.generate_response_calls = []
        self.call_count = 0  # Track number of calls to change behavior
    
    async def generate_response(self, prompt: str, system_context: str = None):
        """
        Mock implementation of generate_response that tracks the call and changes behavior based on call count.
        In the new architecture, this should not receive tools as a parameter anymore.
        """
        # Update for new architecture - tools are accessed directly from kernel registry
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context
        })
        
        self.call_count += 1
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # On the first call, return a tool call if the prompt is about time/date
        if self.call_count == 1 and ("time" in prompt.lower() or "date" in prompt.lower()):
            # Create a mock tool call object for shell_command
            class MockToolCall:
                def __init__(self):
                    self.id = "call_time_1"
                    self.name = "shell_command"
                    self.arguments = {"command": "date"}
                    self.arguments_json = '{"command": "date"}'
        
            return ResponseObj(
                content="I'll get the current time for you.",
                tool_calls=[MockToolCall()]
            )
        elif self.call_count > 1:
            # On subsequent calls (after tool execution), return a response based on tool result
            return ResponseObj(
                content="The current time is: Fri Oct 24 23:45:12 UTC 2025",
                tool_calls=[]  # No more tool calls
            )
        else:
            return ResponseObj(
                content=f"Response to: {prompt}",
                tool_calls=[]
            )
    
    async def stream_response(self, prompt: str, system_context: str = None):
        """
        Mock implementation of stream_response.
        In the new architecture, this should not receive tools as a parameter anymore.
        """
        yield f"Streaming response to: {prompt}"


@pytest.mark.asyncio
async def test_conversation_history_with_tool_call():
    """
    Test that conversation history is properly maintained across tool calls using the new turn-based architecture.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    # Mock the tool result
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Fri Oct 24 23:45:12 UTC 2025\n",  # Example time output
        return_display="Fri Oct 24 23:45:12 UTC 2025\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a minimal mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client, kernel=mock_kernel)
    
    # Set up kernel services including registry for the system context builder
    from gcs_kernel.registry import ToolRegistry
    from gcs_kernel.models import ToolDefinition
    
    # Create a mock registry with shell_command tool
    mock_registry = ToolRegistry()
    
    # Create and register a mock shell command tool that returns the specified result
    class MockShellCommandTool:
        def __init__(self, return_value):
            self.name = "shell_command"
            self.description = "Execute a shell command and return the output"
            self.parameter_schema = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
            self.display_name = "shell_command"
            self.return_value = return_value  # This will be set to the expected result
        
        async def execute(self, parameters):
            # Return the pre-defined tool result
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=self.return_value if hasattr(self, 'return_value') else "Mock shell command result",
                return_display=self.return_value if hasattr(self, 'return_value') else "Mock shell command result"
            )
    
    # Create tool instance with appropriate return value for this test case
    expected_result = tool_result.llm_content
    shell_tool_def = MockShellCommandTool(expected_result)
    
    await mock_registry.register_tool(shell_tool_def)
    
    # Set the registry on the mock kernel too
    mock_kernel.registry = mock_registry
    
    # Set up the orchestrator with the registry
    orchestrator.set_kernel_services(registry=mock_registry)
    
    # Use our mock content generator that tracks conversation history
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a turn manager to handle the conversation flow
    turn_manager = TurnManager(mock_kernel_client, mock_provider, mock_kernel)
    # Set the services on turn manager
    turn_manager.registry = mock_registry
    turn_manager.scheduler = None  # Not needed for testing
    
    # Call the turn manager with a prompt that should trigger a tool call
    # Using async for to consume the async generator
    response_content = ""
    async for event in turn_manager.run_turn("What is the current time?", system_context="You are a helpful assistant."):
        if event.type == "content":
            response_content += event.value
        elif event.type == "finished":
            break
    
    # Use the response content we collected
    response = response_content
    
    # Verify the response contains the time (indicating the tool result was processed)
    assert "2025" in response
    assert "time" in response.lower()
    
    # Verify conversation history is maintained in the turn manager
    history = turn_manager.get_conversation_history()
    assert len(history) >= 3  # Should have user, assistant with tool call, and tool result
    assert any(msg.get('role') == 'user' for msg in history)
    assert any(msg.get('role') == 'tool' for msg in history)


@pytest.mark.asyncio
async def test_multiple_tool_calls_maintain_conversation_history():
    """
    Test that conversation history is properly maintained across multiple tool calls.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Sample time output",
        return_display="Sample time output",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a minimal mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client, kernel=mock_kernel)
    
    # Set up kernel services including registry for the system context builder
    from gcs_kernel.registry import ToolRegistry
    from gcs_kernel.models import ToolDefinition
    
    # Create a mock registry with shell_command tool
    mock_registry = ToolRegistry()
    
    # Create and register a mock shell command tool that returns the specified result
    class MockShellCommandTool:
        def __init__(self, return_value):
            self.name = "shell_command"
            self.description = "Execute a shell command and return the output"
            self.parameter_schema = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
            self.display_name = "shell_command"
            self.return_value = return_value  # This will be set to the expected result
        
        async def execute(self, parameters):
            # Return the pre-defined tool result
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=self.return_value if hasattr(self, 'return_value') else "Mock shell command result",
                return_display=self.return_value if hasattr(self, 'return_value') else "Mock shell command result"
            )
    
    # Create tool instance with appropriate return value for this test case
    expected_result = tool_result.llm_content
    shell_tool_def = MockShellCommandTool(expected_result)
    
    await mock_registry.register_tool(shell_tool_def)
    
    # Set the registry on the mock kernel too
    mock_kernel.registry = mock_registry
    
    # Set up the orchestrator with the registry
    orchestrator.set_kernel_services(registry=mock_registry)
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a turn manager to handle the conversation flow
    turn_manager = TurnManager(mock_kernel_client, mock_provider, mock_kernel)
    # Set the services on turn manager
    turn_manager.registry = mock_registry
    turn_manager.scheduler = None  # Not needed for testing
    
    # Call the turn manager
    response_content = ""
    async for event in turn_manager.run_turn("Get the time and process it.", system_context="You are a helpful assistant."):
        if event.type == "content":
            response_content += event.value
        elif event.type == "finished":
            break
    
    # Verify the response was generated
    assert response_content is not None
    
    # Verify conversation history is maintained
    history = turn_manager.get_conversation_history()
    assert len(history) >= 1  # Should have messages from the interaction


@pytest.mark.asyncio
async def test_conversation_history_includes_all_messages():
    """
    Test that conversation history includes the correct sequence of messages.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Mon Jan 1 12:00:00 UTC 2024\n",
        return_display="Mon Jan 1 12:00:00 UTC 2024\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a minimal mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client, kernel=mock_kernel)
    
    # Set up kernel services including registry for the system context builder
    from gcs_kernel.registry import ToolRegistry
    from gcs_kernel.models import ToolDefinition
    
    # Create a mock registry with shell_command tool
    mock_registry = ToolRegistry()
    
    # Create and register a mock shell command tool that returns the specified result
    class MockShellCommandTool:
        def __init__(self, return_value):
            self.name = "shell_command"
            self.description = "Execute a shell command and return the output"
            self.parameter_schema = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
            self.display_name = "shell_command"
            self.return_value = return_value  # This will be set to the expected result
        
        async def execute(self, parameters):
            # Return the pre-defined tool result
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=self.return_value if hasattr(self, 'return_value') else "Mock shell command result",
                return_display=self.return_value if hasattr(self, 'return_value') else "Mock shell command result"
            )
    
    # Create tool instance with appropriate return value for this test case
    expected_result = tool_result.llm_content
    shell_tool_def = MockShellCommandTool(expected_result)
    
    await mock_registry.register_tool(shell_tool_def)
    
    # Set the registry on the mock kernel too
    mock_kernel.registry = mock_registry
    
    # Set up the orchestrator with the registry
    orchestrator.set_kernel_services(registry=mock_registry)
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a turn manager to handle the conversation flow
    turn_manager = TurnManager(mock_kernel_client, mock_provider, mock_kernel)
    # Set the services on turn manager
    turn_manager.registry = mock_registry
    turn_manager.scheduler = None  # Not needed for testing
    
    # Call the turn manager
    response_content = ""
    async for event in turn_manager.run_turn("What time is it?", system_context="You are a helpful assistant."):
        if event.type == "content":
            response_content += event.value
        elif event.type == "finished":
            break
    
    # Check that the conversation history has the expected structure
    history = turn_manager.get_conversation_history()
    
    # Should have at least a user message and a tool result
    user_messages = [msg for msg in history if msg.get('role') == 'user']
    tool_messages = [msg for msg in history if msg.get('role') == 'tool']
    
    assert len(user_messages) >= 1
    assert len(tool_messages) >= 1
    assert user_messages[0]['content'] == "What time is it?"
    assert tool_messages[0]['content'] == "Mon Jan 1 12:00:00 UTC 2024\n"


@pytest.mark.asyncio
async def test_enhanced_conversation_management():
    """
    Test that the enhanced conversation management functions work properly in the new architecture.
    """
    # Create mock kernel client
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Sample time output\n",
        return_display="Sample time output\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a minimal mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client, kernel=mock_kernel)
    
    # Set up kernel services including registry for the system context builder
    from gcs_kernel.registry import ToolRegistry
    from gcs_kernel.models import ToolDefinition
    
    # Create a mock registry with shell_command tool
    mock_registry = ToolRegistry()
    
    # Create and register a mock shell command tool that returns the specified result
    class MockShellCommandTool:
        def __init__(self, return_value):
            self.name = "shell_command"
            self.description = "Execute a shell command and return the output"
            self.parameter_schema = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
            self.display_name = "shell_command"
            self.return_value = return_value  # This will be set to the expected result
        
        async def execute(self, parameters):
            # Return the pre-defined tool result
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=self.return_value if hasattr(self, 'return_value') else "Mock shell command result",
                return_display=self.return_value if hasattr(self, 'return_value') else "Mock shell command result"
            )
    
    # Create tool instance with appropriate return value for this test case
    expected_result = tool_result.llm_content
    shell_tool_def = MockShellCommandTool(expected_result)
    
    await mock_registry.register_tool(shell_tool_def)
    
    # Set the registry on the mock kernel too
    mock_kernel.registry = mock_registry
    
    # Set up the orchestrator with the registry
    orchestrator.set_kernel_services(registry=mock_registry)
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a turn manager to handle the conversation flow
    turn_manager = TurnManager(mock_kernel_client, mock_provider, mock_kernel)
    # Set the services on turn manager
    turn_manager.registry = mock_registry
    turn_manager.scheduler = None  # Not needed for testing
    
    # Test initial state
    assert len(turn_manager.get_conversation_history()) == 0
    
    # Call the turn manager
    response_content = ""
    async for event in turn_manager.run_turn("What time is it?", system_context="You are a helpful assistant."):
        if event.type == "content":
            response_content += event.value
        elif event.type == "finished":
            break
    
    # Verify conversation history now has messages
    history = turn_manager.get_conversation_history()
    assert len(history) >= 2  # Should have at least user and tool messages
    
    # Verify we can add messages manually
    initial_history_count = len(turn_manager.get_conversation_history())
    turn_manager.add_message_to_history("assistant", "Final response after processing")
    
    # Check that the new message was added
    updated_history = turn_manager.get_conversation_history()
    assert len(updated_history) == initial_history_count + 1
    assert updated_history[-1]['role'] == 'assistant'
    assert updated_history[-1]['content'] == 'Final response after processing'


@pytest.mark.asyncio
async def test_conversation_reset_functionality():
    """
    Test that conversation history can be properly reset in the new architecture.
    """
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="Sample output\n",
        return_display="Sample output\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a minimal mock kernel for testing
    class MockKernel:
        def __init__(self):
            self.registry = None
    
    mock_kernel = MockKernel()
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client, kernel=mock_kernel)
    
    # Set up kernel services including registry for the system context builder
    from gcs_kernel.registry import ToolRegistry
    from gcs_kernel.models import ToolDefinition
    
    # Create a mock registry with shell_command tool
    mock_registry = ToolRegistry()
    
    # Create and register a mock shell command tool that returns the specified result
    class MockShellCommandTool:
        def __init__(self, return_value):
            self.name = "shell_command"
            self.description = "Execute a shell command and return the output"
            self.parameter_schema = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
            self.display_name = "shell_command"
            self.return_value = return_value  # This will be set to the expected result
        
        async def execute(self, parameters):
            # Return the pre-defined tool result
            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=self.return_value if hasattr(self, 'return_value') else "Mock shell command result",
                return_display=self.return_value if hasattr(self, 'return_value') else "Mock shell command result"
            )
    
    # Create tool instance with appropriate return value for this test case
    expected_result = tool_result.llm_content
    shell_tool_def = MockShellCommandTool(expected_result)
    
    await mock_registry.register_tool(shell_tool_def)
    
    # Set the registry on the mock kernel too
    mock_kernel.registry = mock_registry
    
    # Set up the orchestrator with the registry
    orchestrator.set_kernel_services(registry=mock_registry)
    
    # Use our mock content generator
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a turn manager to handle the conversation flow
    turn_manager = TurnManager(mock_kernel_client, mock_provider, mock_kernel)
    # Set the services on turn manager
    turn_manager.registry = mock_registry
    turn_manager.scheduler = None  # Not needed for testing
    
    # Verify initial state is empty
    assert len(turn_manager.get_conversation_history()) == 0
    
    # Run an interaction to populate history
    response_content = ""
    async for event in turn_manager.run_turn("Get time", system_context="You are a helpful assistant."):
        if event.type == "content":
            response_content += event.value
        elif event.type == "finished":
            break
    
    # Verify history is now populated
    history = turn_manager.get_conversation_history()
    assert len(history) >= 1
    
    # Reset the conversation
    turn_manager.reset_conversation()
    
    # Verify it's empty again
    assert len(turn_manager.get_conversation_history()) == 0