"""
Test suite for the AI Orchestrator with LLM Integration.

This module tests the AIOrchestratorService's integration with LLM providers using the new architecture.
"""
import pytest
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.test_mocks import MockContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class AIOrchestratorTestContentGenerator(MockContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing AI orchestrator.
    """
    def __init__(self, config=None, response_content="Mock response content", tool_calls=None, should_stream=True):
        super().__init__(
            config=config,
            response_content=response_content,
            tool_calls=tool_calls,
            should_stream=should_stream
        )
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response taking a prompt object.
        """
        from gcs_kernel.models import PromptObject
        from gcs_kernel.tool_call_model import ToolCall
        
        # Track the call for testing purposes - extract content from prompt object
        self.generate_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # Check if there are already tool results in the conversation history to respond to
        has_tool_result = any(msg.get("role") == "tool" for msg in prompt_obj.conversation_history)
        
        if has_tool_result:
            # Create final response when tool results are present
            # Find the tool result content to include in the response
            tool_content = None
            for msg in reversed(prompt_obj.conversation_history):  # Look from most recent backwards
                if msg.get("role") == "tool":
                    tool_content = msg.get("content", "")
                    break
            
            if tool_content:
                # Create a response incorporating the tool result
                result_prompt_obj = PromptObject.create(
                    content=f"Based on the tool result: {tool_content.strip()}",
                    role="assistant",
                    conversation_history=prompt_obj.conversation_history
                )
                result_prompt_obj.result_content = f"Based on the tool result: {tool_content.strip()}"
            else:
                # Fallback response if we can't find the tool content
                result_prompt_obj = PromptObject.create(
                    content="Based on the tool results, I've completed your request.",
                    role="assistant",
                    conversation_history=prompt_obj.conversation_history
                )
                result_prompt_obj.result_content = "Based on the tool results, I've completed your request."
            
            result_prompt_obj.mark_completed(result_prompt_obj.result_content)
            return result_prompt_obj
        elif "use tool" in prompt_obj.content.lower() or "tool" in prompt_obj.content.lower():
            # Create a mock tool call object with the expected attributes
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.arguments = {"command": "echo hello"}  # Using a real tool with valid parameters
                    self.parameters = {"command": "echo hello"}  # For compatibility
                    import json
                    self.arguments_json = json.dumps(self.arguments)  # JSON string format for OpenAI compatibility

            # Return a PromptObject with tool calls
            result_prompt_obj = PromptObject.create(
                content="I'll use a tool to help with that.",
                role="assistant",
                conversation_history=prompt_obj.conversation_history
            )
            # Create a proper ToolCall object to add to the prompt
            from gcs_kernel.tool_call_model import ToolCall
            tool_call_obj = ToolCall.from_dict_arguments(
                id="call_123",
                name="shell_command",
                arguments={"command": "echo hello"}
            )
            result_prompt_obj.add_tool_call(tool_call_obj)
            result_prompt_obj.result_content = "I'll use a tool to help with that."
            result_prompt_obj.mark_completed(result_prompt_obj.result_content)
            return result_prompt_obj
        else:
            # Return a PromptObject without tool calls
            result_prompt_obj = PromptObject.create(
                content=f"Response to: {prompt_obj.content}",
                role="assistant",
                conversation_history=prompt_obj.conversation_history
            )
            result_prompt_obj.result_content = f"Response to: {prompt_obj.content}"
            result_prompt_obj.mark_completed(result_prompt_obj.result_content)
            return result_prompt_obj
    
    async def process_tool_result(self, tool_result, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of process_tool_result taking a prompt object.
        """
        from gcs_kernel.models import PromptObject
        
        # Return a PromptObject with the processed result
        result_prompt_obj = PromptObject.create(
            content=f"Processed tool result: {tool_result.llm_content}",
            role="assistant",
            conversation_history=prompt_obj.conversation_history
        )
        result_prompt_obj.result_content = f"Processed tool result: {tool_result.llm_content}"
        result_prompt_obj.mark_completed(result_prompt_obj.result_content)
        return result_prompt_obj

    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Mock implementation of stream_response taking a prompt object.
        """
        yield f"Streaming response to: {prompt_obj.content}"
    
    async def generate_response_from_conversation(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response_from_conversation taking a prompt object.
        """
        from gcs_kernel.models import PromptObject
        from gcs_kernel.tool_call_model import ToolCall
        
        # Check for user messages in conversation history
        last_user_message = None
        for msg in reversed(prompt_obj.conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # Track the call for testing purposes
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'prompt_id': prompt_obj.prompt_id
        })
        
        # For testing purposes, return a response with a tool call sometimes
        if last_user_message and ("use tool" in last_user_message.lower() or "tool" in last_user_message.lower()):
            # Create a mock tool call object with the expected attributes
            class MockToolCall:
                def __init__(self):
                    self.id = "call_123"
                    self.name = "shell_command"
                    self.arguments = {"command": "echo hello"}  # Using a real tool with valid parameters
                    self.parameters = {"command": "echo hello"}  # For compatibility
                    import json
                    self.arguments_json = json.dumps(self.arguments)  # JSON string format for OpenAI compatibility

            # Return a PromptObject with tool calls
            result_prompt_obj = PromptObject.create(
                content="I'll use a tool to help with that based on our conversation.",
                role="assistant",
                conversation_history=prompt_obj.conversation_history
            )
            # Create a proper ToolCall object to add to the prompt
            from gcs_kernel.tool_call_model import ToolCall
            tool_call_obj = ToolCall.from_dict_arguments(
                id="call_123",
                name="shell_command",
                arguments={"command": "echo hello"}
            )
            result_prompt_obj.add_tool_call(tool_call_obj)
            result_prompt_obj.result_content = "I'll use a tool to help with that based on our conversation."
            result_prompt_obj.mark_completed(result_prompt_obj.result_content)
            return result_prompt_obj
        else:
            # Return a PromptObject without tool calls
            result_prompt_obj = PromptObject.create(
                content=f"Response to: {last_user_message}",
                role="assistant",
                conversation_history=prompt_obj.conversation_history
            )
            result_prompt_obj.result_content = f"Response to: {last_user_message}"
            result_prompt_obj.mark_completed(result_prompt_obj.result_content)
            return result_prompt_obj


@pytest.mark.asyncio
async def test_ai_orchestrator_initialization():
    """
    Test that AIOrchestratorService initializes properly with MCP client.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    
    assert orchestrator.mcp_client == kernel_client
    assert orchestrator.content_generator is None
    # Ensure all new components are initialized
    assert orchestrator.turn_manager is not None
    assert orchestrator.tool_executor is not None


@pytest.mark.asyncio
async def test_ai_orchestrator_set_content_generator():
    """
    Test that AIOrchestratorService can have its content generator set.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    mock_provider = AIOrchestratorTestContentGenerator()
    
    orchestrator.set_content_generator(mock_provider)
    
    assert orchestrator.content_generator == mock_provider
    # Verify components were also updated
    assert orchestrator.turn_manager.content_generator == mock_provider


@pytest.mark.asyncio
async def test_ai_orchestrator_handle_ai_interaction():
    """
    Test that AIOrchestratorService can handle an AI interaction.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    # Use mock generator with custom response content that will include the prompt
    mock_provider = AIOrchestratorTestContentGenerator(response_content="Response to")
    orchestrator.set_content_generator(mock_provider)
    
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Hello, how are you?")
    response = await orchestrator.handle_ai_interaction(prompt_obj)
    
    assert response.result_content is not None
    assert len(response.result_content) > 0


@pytest.mark.asyncio
async def test_ai_orchestrator_handle_ai_interaction_with_tool_call():
    """
    Test that AIOrchestratorService can handle an AI interaction with tool calls.
    """
    # Mock the kernel client to simulate tool execution
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.return_value = "exec_123"
    
    # Mock the list_tools method for backward compatibility
    mock_kernel_client.list_tools.return_value = {
        "shell_command": {
            "name": "shell_command",
            "description": "Execute a shell command and return the output",
            "parameters": {  # Using OpenAI-compatible format
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    }
    
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="hello\n",  # Output of echo hello
        return_display="hello\n",
        success=True
    )
    mock_kernel_client.get_execution_result.return_value = tool_result
    
    # Create a mock tool execution manager for the test
    mock_tool_execution_manager = AsyncMock()
    mock_tool_execution_manager.execute_internal_tool.return_value = tool_result
    mock_tool_execution_manager.registry = None  # Mock registry as None for test
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Set kernel services to provide the mock tool execution manager
    orchestrator.set_kernel_services(tool_execution_manager=mock_tool_execution_manager)
    
    # Update the content generator reference in turn manager and other components too
    mock_provider = AIOrchestratorTestContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Create a prompt object and process it
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Please use a tool to help me.")
    result_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    
    # The response should be a valid PromptObject with some content
    assert result_obj.result_content is not None
    assert len(result_obj.result_content) > 0


@pytest.mark.asyncio
async def test_ai_orchestrator_stream_ai_interaction():
    """
    Test that AIOrchestratorService can stream an AI interaction.
    """
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    orchestrator = AIOrchestratorService(kernel_client)
    mock_provider = AIOrchestratorTestContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Hello, stream this.")
    chunks = []
    async for chunk in orchestrator.stream_ai_interaction(prompt_obj):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    # When streaming, the first chunk might be a tool request or content
    # depending on the mock behavior


@pytest.mark.asyncio
async def test_turn_manager_with_tool_calls():
    """
    Test that the TurnManager properly handles tool calls in a turn.
    """
    from services.ai_orchestrator.turn_manager import TurnManager
    
    # Create mock tool execution manager
    mock_tool_execution_manager = AsyncMock()
    tool_result = ToolResult(
        tool_name="shell_command",
        llm_content="hello\n",  # Output of echo hello
        return_display="hello\n",
        success=True
    )
    mock_tool_execution_manager.execute_internal_tool.return_value = tool_result
    mock_tool_execution_manager.registry = None  # Mock registry as None for test
    
    # Create mock kernel client (using MCPClient class structure)
    from gcs_kernel.mcp.client import MCPClient
    from gcs_kernel.models import MCPConfig
    mcp_config = MCPConfig(server_url="http://test-url")
    kernel_client = MCPClient(mcp_config)
    
    mock_provider = AIOrchestratorTestContentGenerator()
    turn_manager = TurnManager(kernel_client, mock_provider)
    
    # Set the tool execution manager on the turn manager
    turn_manager.tool_execution_manager = mock_tool_execution_manager
    
    # Create an abort signal for the turn
    import asyncio
    abort_signal = asyncio.Event()
    
    # Run a turn with a prompt that triggers a tool call
    events = []
    import uuid
    from gcs_kernel.models import PromptObject
    prompt_obj = PromptObject.create(content="Please use a tool to help me.")
    prompt_obj.conversation_history = [{"role": "system", "content": "System context for testing"}]
    async for event in turn_manager.run_turn(
        prompt_obj,
        abort_signal
    ):
        events.append(event)
    
    # Verify we got the expected events
    assert len(events) > 0
    # Should have at least one content event or tool request event
    event_types = [e.type for e in events]
    assert any(t in ['content', 'tool_call_request', 'finished', 'tool_call_response'] for t in event_types)