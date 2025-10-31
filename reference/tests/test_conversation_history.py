"""
Test suite for conversation history functionality in AI Orchestrator.

This module tests that conversation history is properly maintained across 
tool calls and responses, ensuring the LLM gets the full context to generate
meaningful responses after tool execution.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.test_mocks import MockContentGenerator, ToolCallingMockContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class TrackingMockContentGenerator(MockContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing conversation history.
    """
    def __init__(self, config=None):
        super().__init__(config)
        
        # Track calls to verify conversation history is passed
        self.generate_response_calls = []
        self.process_tool_result_calls = []
    
    async def generate_response(self, prompt: str, system_context: str = None, prompt_id: str = None):
        """
        Mock implementation of generate_response that tracks the call.
        """
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'prompt_id': prompt_id
        })
        
        # Use the parent implementation for the actual response
        response = await super().generate_response(prompt, system_context, prompt_id)
        
        # For testing purposes, return a response with a tool call sometimes
        if "time" in prompt.lower() or "date" in prompt.lower():
            # Create a mock tool call object for shell_command
            class MockToolCall:
                def __init__(self):
                    self.id = "call_time_1"
                    self.name = "shell_command"
                    self.parameters = {"command": "date"}
                    import json
                    self.arguments = self.parameters
                    self.arguments_json = json.dumps(self.parameters)
        
            return ResponseObj(
                content="I'll get the current time for you.",
                tool_calls=[MockToolCall()]
            )
        else:
            return ResponseObj(
                content=f"Response to: {prompt}",
                tool_calls=[]
            )
    
    async def process_tool_result(self, tool_result, conversation_history=None, prompt_id: str = None):
        """
        Mock implementation of process_tool_result that tracks conversation history.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'prompt_id': prompt_id
        })
        
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        # In the real system, the LLM looks at the conversation history for tool results
        # For the mock, let's check the conversation history for the most recent tool result
        actual_result_content = "Tool execution results provided."
        if conversation_history:
            # Look for the most recent tool message in the conversation history
            for msg in reversed(conversation_history):
                if msg.get("role") == "tool":
                    actual_result_content = msg.get("content", "Tool execution results provided.")
                    break
        
        # Use the actual result from conversation history if available, otherwise fall back
        response_content = f"The time is {actual_result_content.strip()}"
        return ResponseObj(content=response_content)
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of stream_response.
        """
        yield f"Streaming response to: {prompt}"
    
    async def generate_response_from_conversation(self, conversation_history: list, prompt_id: str = None):
        """
        Mock implementation of generate_response_from_conversation.
        """
        # Track the call for verification
        self.generate_response_calls.append({
            'conversation_history': conversation_history,
            'prompt_id': prompt_id
        })
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # For testing purposes, check if there's a tool result in the conversation history
        # that should trigger another response
        has_tool_result = any(msg.get("role") == "tool" for msg in conversation_history)
        
        # If there's a tool result in the conversation, provide the final answer
        if has_tool_result:
            # Look for the tool result content
            tool_content = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "tool":
                    tool_content = msg.get("content", "")
                    break
            
            # Return a final response based on the tool result
            return ResponseObj(
                content=f"The current date/time is: {tool_content.strip()}",
                tool_calls=[]
            )
        else:
            # Otherwise, check if there's a user prompt about time/date to generate a tool call
            last_user_message = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break
            
            if last_user_message and ("time" in last_user_message.lower() or "date" in last_user_message.lower()):
                # Create a mock tool call object for shell_command
                class MockToolCall:
                    def __init__(self):
                        self.id = "call_time_1"
                        self.name = "shell_command"
                        self.parameters = {"command": "date"}
                        import json
                        self.arguments = self.parameters
                        self.arguments_json = json.dumps(self.parameters)
        
                return ResponseObj(
                    content="I'll get the current time for you.",
                    tool_calls=[MockToolCall()]
                )
        
        # Default response
        return ResponseObj(
            content="Processed conversation",
            tool_calls=[]
        )


@pytest.mark.asyncio
async def test_conversation_history_with_tool_call():
    """
    Test that conversation history is properly maintained across tool calls.
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
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    

    
    # Use our mock content generator that tracks conversation history and returns tool calls for specific prompts
    mock_provider = ToolCallingMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the AI orchestrator with a prompt that should trigger a tool call
    response = await orchestrator.handle_ai_interaction("What is the current time?")
    
    # Verify the response contains the time (indicating the tool result was processed)
    assert "2025" in response
    assert "time" in response.lower()
    
    # Verify that conversation history was passed to process_tool_result
    assert len(mock_provider.process_tool_result_calls) > 0
    call_data = mock_provider.process_tool_result_calls[0]
    assert 'conversation_history' in call_data
    assert call_data['conversation_history'] is not None
    assert len(call_data['conversation_history']) > 0
    
    # Check that the conversation history contains the expected elements
    history = call_data['conversation_history']
    # Should have user message, assistant message with tool call, and tool result
    assert any(msg.get('role') == 'user' for msg in history)
    assert any(msg.get('role') == 'tool' for msg in history)


@pytest.mark.asyncio
async def test_multiple_tool_calls_maintain_conversation_history():
    """
    Test that conversation history is properly maintained across multiple tool calls.
    """
    # Create a mock content generator that will trigger two tool calls
    class MultiToolMockContentGenerator(MockContentGenerator):
        def __init__(self):
            super().__init__()
            self.call_count = 0
            self.process_tool_result_calls = []
        
        async def generate_response(self, prompt: str, system_context: str = None, prompt_id: str = None):
            self.call_count += 1
            
            class ResponseObj:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls if tool_calls else []
            
            # Return different responses depending on call count
            if self.call_count == 1:
                # First call returns a tool call
                class MockToolCall:
                    def __init__(self):
                        self.id = "call_1"
                        self.name = "shell_command"
                        self.parameters = {"command": "date"}
                        import json
                        self.arguments = self.parameters
                        self.arguments_json = json.dumps(self.parameters)
                
                return ResponseObj(
                    content="Getting the current time.",
                    tool_calls=[MockToolCall()]
                )
            else:
                # Second call (after tool result) returns final content
                return ResponseObj(
                    content="Final response after processing tool result.",
                    tool_calls=[]
                )
        
        async def process_tool_result(self, tool_result, conversation_history=None, prompt_id: str = None):
            self.process_tool_result_calls.append({
                'tool_result': tool_result,
                'conversation_history': conversation_history,
                'prompt_id': prompt_id
            })
            
            class ResponseObj:
                def __init__(self, content):
                    self.content = content
            
            return ResponseObj(content="Response after processing first tool result")
        
        async def generate_response_from_conversation(self, conversation_history: list, prompt_id: str = None):
            self.call_count += 1  # Increment call count like the original generate_response method
            
            class ResponseObj:
                def __init__(self, content, tool_calls):
                    self.content = content
                    self.tool_calls = tool_calls if tool_calls else []
            
            # Return different responses depending on call count
            if self.call_count == 1:
                # First call returns a tool call
                class MockToolCall:
                    def __init__(self):
                        self.id = "call_1"
                        self.name = "shell_command"
                        self.parameters = {"command": "date"}
                        import json
                        self.arguments = self.parameters
                        self.arguments_json = json.dumps(self.parameters)
                
                return ResponseObj(
                    content="Getting the current time.",
                    tool_calls=[MockToolCall()]
                )
            else:
                # Second call (after tool result) returns final content
                return ResponseObj(
                    content="Final response after processing tool result.",
                    tool_calls=[]
                )
    
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
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    

    
    # Use our multi-tool mock content generator
    mock_provider = MultiToolMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the AI orchestrator
    response = await orchestrator.handle_ai_interaction("Get the time and process it.")
    
    # Verify the response was generated
    assert response is not None
    
    # Verify that conversation history was passed to process_tool_result
    assert len(mock_provider.process_tool_result_calls) > 0
    call_data = mock_provider.process_tool_result_calls[0]
    assert call_data['conversation_history'] is not None
    assert len(call_data['conversation_history']) > 0


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
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    

    
    mock_provider = TrackingMockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Call the orchestrator
    response = await orchestrator.handle_ai_interaction("What time is it?")
    
    # Check that the conversation history has the expected structure
    call_data = mock_provider.process_tool_result_calls[0]
    history = call_data['conversation_history']
    
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
    Test that the enhanced conversation management functions work properly.
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
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    

    
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Test initial state
    assert len(orchestrator.get_conversation_history()) == 0
    
    # Call the orchestrator
    response = await orchestrator.handle_ai_interaction("What time is it?")
    
    # Verify conversation history now has messages
    history = orchestrator.get_conversation_history()
    assert len(history) >= 2  # Should have at least user and tool messages
    
    # Verify we can add messages manually
    initial_history_count = len(orchestrator.get_conversation_history())
    orchestrator.add_message_to_history("assistant", "Final response after processing")
    
    # Check that the new message was added
    updated_history = orchestrator.get_conversation_history()
    assert len(updated_history) == initial_history_count + 1
    assert updated_history[-1]['role'] == 'assistant'
    assert updated_history[-1]['content'] == 'Final response after processing'


@pytest.mark.asyncio
async def test_conversation_reset_functionality():
    """
    Test that conversation history can be properly reset.
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
    
    orchestrator = AIOrchestratorService(mock_kernel_client)
    

    
    mock_provider = MockContentGenerator()
    orchestrator.set_content_generator(mock_provider)
    
    # Verify initial state is empty
    assert len(orchestrator.get_conversation_history()) == 0
    
    # Run an interaction to populate history
    response = await orchestrator.handle_ai_interaction("Get time")
    
    # Verify history is now populated
    history = orchestrator.get_conversation_history()
    assert len(history) >= 1
    
    # Reset the conversation
    await orchestrator.reset_conversation()
    
    # Verify it's empty again
    assert len(orchestrator.get_conversation_history()) == 0