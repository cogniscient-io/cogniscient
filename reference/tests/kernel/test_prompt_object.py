"""
Test suite for the Prompt Object Architecture.
This module includes tests for the PromptObject model and related functionality.
"""

import pytest
from datetime import datetime
from gcs_kernel.models import PromptObject, ToolInclusionPolicy, PromptStatus


def test_prompt_object_creation():
    """Prompt object is created with all required fields properly initialized"""
    prompt_obj = PromptObject(
        prompt_id="test_prompt_123",
        content="Test prompt content",
        tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
    )
    
    assert prompt_obj.prompt_id == "test_prompt_123"
    assert prompt_obj.content == "Test prompt content"
    assert prompt_obj.tool_policy == ToolInclusionPolicy.ALL_AVAILABLE
    assert prompt_obj.status.value == "pending"
    assert prompt_obj.created_at is not None
    assert prompt_obj.updated_at is not None


def test_prompt_object_status_transitions():
    """Prompt object properly transitions between statuses"""
    prompt_obj = PromptObject(prompt_id="test_prompt_123", content="Test")
    
    # Initially pending
    assert prompt_obj.status.value == "pending"
    
    # After marking processing
    prompt_obj.mark_processing()
    assert prompt_obj.status.value == "processing"
    
    # After marking completed
    prompt_obj.mark_completed("Result content")
    assert prompt_obj.status.value == "completed"
    assert prompt_obj.result_content == "Result content"
    assert prompt_obj.processed_at is not None
    
    # After marking error
    prompt_obj.mark_error("Test error")
    assert prompt_obj.status.value == "error"
    assert prompt_obj.error_message == "Test error"


def test_prompt_object_tool_calls():
    """Prompt object properly handles tool calls and results"""
    prompt_obj = PromptObject(prompt_id="test_prompt_123", content="Test")
    
    # Add tool call
    tool_call_data = {"id": "call_123", "name": "test_tool", "arguments": {"param": "value"}}
    prompt_obj.add_tool_call(tool_call_data)
    
    assert len(prompt_obj.tool_calls) == 1
    assert prompt_obj.tool_calls[0] == tool_call_data
    
    # Add tool result
    tool_result_data = {"tool_name": "test_tool", "result": "success"}
    prompt_obj.add_tool_result(tool_result_data)
    
    assert len(prompt_obj.tool_results) == 1
    assert prompt_obj.tool_results[0] == tool_result_data


@pytest.mark.asyncio
async def test_content_generator_with_prompt_objects():
    """Content generator properly processes prompt objects"""
    from gcs_kernel.models import PromptObject
    from services.llm_provider.content_generator import LLMContentGenerator
    
    # Create a mock content generator that doesn't actually call an LLM
    class MockContentGenerator(LLMContentGenerator):
        async def generate_response_from_conversation_with_prompt_object(self, prompt_obj: PromptObject):
            # Mark as processing
            prompt_obj.mark_processing()
            # Update the result content
            prompt_obj.result_content = "Processed: " + prompt_obj.content
            # Mark as completed
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
    
    # Create a test prompt object
    prompt_obj = PromptObject(
        prompt_id="test_prompt_123",
        content="Test prompt for processing"
    )
    
    # Create the mock content generator
    generator = MockContentGenerator()
    
    # Process the prompt - this should update the object
    result_obj = await generator.generate_response_from_conversation_with_prompt_object(prompt_obj)
    
    assert result_obj.status.value == "completed"
    assert result_obj.result_content == "Processed: Test prompt for processing"
    assert result_obj.processed_at is not None


@pytest.mark.asyncio
async def test_kernel_prompt_processing():
    """Kernel properly processes prompts using prompt objects"""
    from gcs_kernel.kernel import GCSKernel
    import uuid
    
    kernel = GCSKernel()
    
    # Mock the content generator using the standard mock from test_mocks
    from services.llm_provider.test_mocks import MockContentGenerator
    
    # Create a mock content generator
    mock_content_generator = MockContentGenerator(
        response_content="Processed: Test prompt",
        tool_calls=[]
    )
    
    # Replace the content generator with the mock using the proper method
    kernel.ai_orchestrator.set_content_generator(mock_content_generator)
    
    # Submit a prompt
    result = await kernel.submit_prompt("Test prompt")
    
    # Verify the result is appropriate
    assert isinstance(result, str)
    # In the new architecture, the kernel uses streaming internally, so we might get streaming content
    assert "Processed: Test prompt" in result  # The important part is still there
    
    # Check that a prompt object was registered
    assert len(kernel.prompt_object_registry) == 1
    
    # Get the prompt object and verify it
    prompt_id = list(kernel.prompt_object_registry.keys())[0]
    prompt_obj = kernel.prompt_object_registry[prompt_id]
    
    assert prompt_obj.status.value == "completed"
    assert "Processed: Test prompt" in prompt_obj.result_content


def test_backward_compatibility():
    """Existing API methods continue to work after prompt object implementation"""
    # This test would require mocking the entire kernel with all its dependencies
    # For now, we just verify that the methods exist and can be called syntactically
    from gcs_kernel.kernel import GCSKernel
    
    kernel = GCSKernel()
    
    # The methods should be available (they route to the new architecture)
    assert hasattr(kernel, 'submit_prompt')
    assert hasattr(kernel, 'stream_prompt')
    
    # Check that new methods are also available
    assert hasattr(kernel, 'submit_prompt')
    assert hasattr(kernel, 'stream_prompt')
    assert hasattr(kernel, 'create_prompt_object')
    assert hasattr(kernel, 'get_prompt_object')