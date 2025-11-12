"""
Test suite for Adaptive Loop Service.

This module tests the AdaptiveLoopService functionality,
including AI-assisted adaptation and fallback mechanisms.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from gcs_kernel.models import PromptObject
from services.adaptive_loop.adaptive_loop_service import AdaptiveLoopService


class MockOrchestrator:
    """Mock AI orchestrator for testing."""
    async def handle_ai_interaction(self, prompt_obj):
        # Mock response based on the content of the prompt
        if "max_context_length" in prompt_obj.content and "gpt-4-turbo" in prompt_obj.content:
            # Simulate the AI recognizing max_context_length in a model response
            prompt_obj.result_content = "max_tokens: 128000"
            prompt_obj.mark_completed(prompt_obj.result_content)
        elif "NOT_FOUND" in prompt_obj.content:
            # Simulate the AI not finding the information
            prompt_obj.result_content = "NOT_FOUND"
            prompt_obj.mark_completed(prompt_obj.result_content)
        else:
            # Default response
            prompt_obj.result_content = "max_context_length: 8000"
            prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj


class FailingOrchestrator:
    """Mock orchestrator that always fails."""
    async def handle_ai_interaction(self, prompt_obj):
        prompt_obj.mark_error("AI processing failed")
        return prompt_obj


@pytest.fixture
def mock_client():
    """Create a mock MCP client for testing."""
    return MagicMock()


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    return MockOrchestrator()


@pytest.fixture
def adaptive_loop_service(mock_client, mock_orchestrator):
    """Create an adaptive loop service instance for testing."""
    return AdaptiveLoopService(
        mcp_client=mock_client,
        ai_orchestrator=mock_orchestrator
    )


@pytest.mark.asyncio
async def test_adaptive_loop_success(adaptive_loop_service):
    """Test successful AI processing of context."""
    context_data = {
        "model_response": {
            "id": "gpt-4-turbo-2024-04-09",
            "object": "model", 
            "created": 1686935002,
            "owned_by": "openai",
            "max_tokens": 128000  # This is what the AI should identify
        },
        "model_name": "gpt-4-turbo",
        "missing_field": "max_context_length"
    }
    
    result = await adaptive_loop_service.adapt_async(
        context=context_data,
        problem_description="Find the maximum context length field in the model response for gpt-4-turbo",
        fallback_value=4096
    )
    
    # Should return the value identified by AI (128000)
    assert result == 128000


@pytest.mark.asyncio
async def test_adaptive_loop_with_fallback():
    """Test fallback when AI processing fails."""
    mock_client = MagicMock()
    failing_service = AdaptiveLoopService(
        mcp_client=mock_client,
        ai_orchestrator=FailingOrchestrator()
    )
    
    context_data = {
        "model_response": {"some": "data"},
        "model_name": "test-model",
        "missing_field": "max_tokens"
    }
    
    result = await failing_service.adapt_async(
        context=context_data,
        problem_description="This should fail and use fallback",
        fallback_value=9999
    )
    
    # Should return the fallback value since AI failed
    assert result == 9999


@pytest.mark.asyncio
async def test_adaptive_loop_ai_returns_not_found():
    """Test when AI explicitly returns NOT_FOUND, fallback should be used."""
    mock_client = MagicMock()
    
    class NotFoundOrchestrator:
        async def handle_ai_interaction(self, prompt_obj):
            prompt_obj.result_content = "NOT_FOUND"
            prompt_obj.mark_completed(prompt_obj.result_content)
            return prompt_obj
    
    not_found_service = AdaptiveLoopService(
        mcp_client=mock_client,
        ai_orchestrator=NotFoundOrchestrator()
    )
    
    result = await not_found_service.adapt_async(
        context={"some": "data"},
        problem_description="AI should respond with NOT_FOUND",
        fallback_value=7777
    )
    
    # Should return the fallback value since AI responded with NOT_FOUND
    assert result == 7777


def test_parse_ai_response_integer():
    """Test parsing AI response for integer values."""
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    service = AdaptiveLoopService(mock_client, mock_orchestrator)
    
    result = service._parse_ai_response("max_context_length: 16000")
    assert result == 16000


def test_parse_ai_response_float():
    """Test parsing AI response for float values."""
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    service = AdaptiveLoopService(mock_client, mock_orchestrator)
    
    result = service._parse_ai_response("max_tokens: 32.5")
    assert result == 32.5


def test_parse_ai_response_not_found():
    """Test parsing AI response for NOT_FOUND."""
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    service = AdaptiveLoopService(mock_client, mock_orchestrator)
    
    result = service._parse_ai_response("NOT_FOUND")
    assert result is None


def test_parse_ai_response_string():
    """Test parsing AI response for string values."""
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    service = AdaptiveLoopService(mock_client, mock_orchestrator)
    
    result = service._parse_ai_response("model_name: gpt-4-turbo")
    assert result == "gpt-4-turbo"


def test_build_prompt():
    """Test building the AI prompt."""
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    service = AdaptiveLoopService(mock_client, mock_orchestrator)
    
    context = {"test": "data"}
    problem = "Find the answer"
    
    prompt = service._build_prompt(context, problem)
    
    assert "Context: {'test': 'data'}" in prompt
    assert "Problem: Find the answer" in prompt
    assert "Please analyze the context data" in prompt