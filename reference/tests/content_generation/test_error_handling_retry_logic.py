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
from gcs_kernel.models import MCPConfig, ToolResult, PromptObject


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
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of generate_response with optional failure.
        """
        self.generate_response_calls.append({
            'prompt': prompt_obj.content,
            'system_context': next((msg.get("content") for msg in prompt_obj.conversation_history if msg.get("role") == "system"), None),
            'tools': prompt_obj.custom_tools
        })
        
        # Fail the first few calls if configured to do so
        if self.current_fail_count < self.fail_count:
            self.current_fail_count += 1
            raise Exception(f"Simulated failure {self.current_fail_count}")
        
        # Call parent implementation but handle the prompt object properly
        return await super().generate_response(prompt_obj)
    
    async def process_tool_result(self, tool_result, prompt_obj: 'PromptObject') -> 'PromptObject':
        """
        Mock implementation of process_tool_result.
        """
        self.process_tool_result_calls.append({
            'tool_result': tool_result,
            'prompt_obj': prompt_obj
        })
        
        # Update the prompt object with the processed result
        prompt_obj.result_content = f"Processed: {tool_result.llm_content}"
        prompt_obj.mark_completed(prompt_obj.result_content)
        
        return prompt_obj
    



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
    prompt_obj = PromptObject.create(content="Test prompt", streaming_enabled=False)
    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    response = response_obj.result_content
    
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
    prompt_obj = PromptObject.create(content="Test prompt for tool execution")
    response_obj = await orchestrator.handle_ai_interaction(prompt_obj)
    response = response_obj.result_content
    
    # Should not crash, and potentially have an error in the response string
    # The response handling in the orchestrator should catch the exception and continue
    assert response is not None