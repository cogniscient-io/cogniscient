"""
Test suite for robust error handling and retry logic in AI Orchestrator.

This module tests that error handling and retry mechanisms work properly,
similar to Qwen Code's implementation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.test_mocks import MockContentGenerator
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult


class ErrorSimulatingMockContentGenerator(MockContentGenerator):
    """
    Mock implementation of BaseContentGenerator for testing error handling.
    """
    def __init__(self, config=None, should_fail=False, fail_count=0):
        super().__init__(config)
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fail_count = 0
        self.generate_response_calls = []
        self.process_tool_result_calls = []
    
    async def generate_response(self, prompt: str, system_context: str = None, tools: list = None):
        """
        Mock implementation of generate_response with optional failure.
        """
        self.generate_response_calls.append({
            'prompt': prompt,
            'system_context': system_context,
            'tools': tools
        })
        
        # Fail the first few calls if configured to do so
        if self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        # Use the parent implementation to generate the response
        response = await super().generate_response(prompt, system_context, tools=tools)
        
        # Return a response with a tool call for testing
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        class MockToolCall:
            def __init__(self):
                self.id = "test_call_123"
                self.name = "shell_command"
                self.parameters = {"command": "echo hello"}
                import json
                self.arguments = self.parameters  # Use parameters directly as arguments
                self.arguments_json = json.dumps(self.parameters)
        
        return ResponseObj(
            content="I'll use a tool to help with that.",
            tool_calls=[MockToolCall()] if not self.should_fail else []
        )
    
    async def process_tool_result(self, tool_result, conversation_history=None, available_tools=None):
        """
        Mock implementation of process_tool_result.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'conversation_history': conversation_history,
            'available_tools': available_tools
        })
        
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed: {tool_result.llm_content}")
    
    async def generate_response_from_conversation(self, conversation_history: list, tools: list = None):
        """
        Mock implementation of generate_response_from_conversation with optional failure.
        """
        # Track the call for verification (similar to generate_response)
        last_user_message = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        self.generate_response_calls.append({
            'prompt': last_user_message,
            'system_context': next((msg.get("content") for msg in conversation_history if msg.get("role") == "system"), None),
            'tools': tools
        })
        
        # Fail the first few calls if configured to do so
        if self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
        
        # Check if there's a tool result in the conversation history to respond to
        has_tool_result = any(msg.get("role") == "tool" for msg in conversation_history)
        if has_tool_result:
            # Create final response when tool results are present
            return ResponseObj(
                content="Based on the tool results, I've completed your request.",
                tool_calls=[]
            )
        
        # Otherwise, return a response with a tool call for testing
        class MockToolCall:
            def __init__(self):
                self.id = "test_call_123"
                self.name = "shell_command"
                self.parameters = {"command": "echo hello"}
                import json
                self.arguments = self.parameters  # Use parameters directly as arguments
                self.arguments_json = json.dumps(self.parameters)
        
        return ResponseObj(
            content="I'll use a tool to help with that.",
            tool_calls=[MockToolCall()] if not self.should_fail else []
        )


@pytest.mark.asyncio
async def test_content_generation_functionality():
    """
    Test that content generation works properly.
    """
    # Create orchestrator
    mock_kernel_client = AsyncMock()
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a content generator
    mock_provider = MockContentGenerator(should_fail=False, fail_count=0)  # No failures
    orchestrator.set_content_generator(mock_provider)
    

    
    # Call the orchestrator - should work properly
    response = await orchestrator.handle_ai_interaction("Test prompt")
    
    # Verify the response was generated
    assert response is not None
    assert len(mock_provider.generate_response_calls) == 1  # Should be called once


@pytest.mark.asyncio
async def test_tool_execution_error_handling():
    """
    Test that tool execution errors are handled gracefully.
    """
    # Create mock kernel client that fails on submit_tool_execution
    mock_kernel_client = AsyncMock()
    mock_kernel_client.submit_tool_execution.side_effect = Exception("Service unavailable")
    
    # Create orchestrator
    orchestrator = AIOrchestratorService(mock_kernel_client)
    
    # Create a content generator that returns a tool call
    mock_provider = MockContentGenerator(should_fail=False, fail_count=0)
    orchestrator.set_content_generator(mock_provider)
    

    
    # Call the orchestrator - tool submission will fail, but should be handled gracefully
    response = await orchestrator.handle_ai_interaction("Test prompt for tool execution")
    
    # Should not crash, and potentially have an error in the response string
    # The response handling in the orchestrator should catch the exception and continue
    assert response is not None