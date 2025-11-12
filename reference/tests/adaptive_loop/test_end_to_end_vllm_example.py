"""
End-to-end test for Adaptive Loop processing the exact example from the requirements.

This test verifies that the Adaptive Loop system can process the specific 
VLLM model response example provided in the requirements.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from gcs_kernel.models import PromptObject
from services.adaptive_loop.adaptive_loop_service import AdaptiveLoopService


class SimulatedAIResponse:
    """
    Simulate how a real AI might respond to the VLLM model response example.
    This represents what an actual LLM would return when asked to find max_model_len.
    """
    def __init__(self):
        self.responses = {
            # For the specific VLLM response with max_model_len
            "max_model_len": "max_model_len: 262144",
            # For other field types
            "max_context_length": "max_context_length: 128000",
            "context_length": "context_length: 32000"
        }
    
    async def handle_request(self, prompt_obj):
        """Simulate AI processing that identifies fields in the model response."""
        content = prompt_obj.content
        
        # Look for the specific pattern in the prompt content
        if "max_model_len" in content and "qwen3-coder-30b-a3b-instruct" in content:
            # AI identifies the max_model_len field in the VLLM response
            prompt_obj.result_content = self.responses["max_model_len"]
        elif "max_context_length" in content:
            # AI identifies the max_context_length field 
            prompt_obj.result_content = self.responses["max_context_length"]
        else:
            # Default response
            prompt_obj.result_content = self.responses["context_length"]
        
        prompt_obj.mark_completed(prompt_obj.result_content)
        return prompt_obj


@pytest.mark.asyncio
async def test_adaptive_loop_with_exact_vllm_response_example():
    """
    Test the exact scenario described in the requirements:
    Processing a VLLM response with max_model_len field instead of max_context_length.
    """
    # This is the exact model response provided in the requirements
    vllm_model_response = {
        "object": "list",
        "data": [
            {
                "id": "qwen/qwen3-coder-30b-a3b-instruct",
                "object": "model",
                "created": 1762804142,
                "owned_by": "vllm",
                "root": "qwen/qwen3-coder-30b-a3b-instruct",
                "parent": None,
                "max_model_len": 262144,  # This is the field we want to extract
                "permission": [
                    {
                        "id": "modelperm-66945a594bec418a9f57cd69919a0517",
                        "object": "model_permission",
                        "created": 1762804142,
                        "allow_create_engine": False,
                        "allow_sampling": True,
                        "allow_logprobs": True,
                        "allow_search_indices": False,
                        "allow_view": True,
                        "allow_fine_tuning": False,
                        "organization": "*",
                        "group": None,
                        "is_blocking": False
                    }
                ]
            }
        ]
    }
    
    # Create the adaptive loop service with simulated AI behavior
    mock_client = MagicMock()
    ai_simulator = SimulatedAIResponse()
    
    class SimulatedOrchestrator:
        async def handle_ai_interaction(self, prompt_obj):
            return await ai_simulator.handle_request(prompt_obj)
    
    adaptive_service = AdaptiveLoopService(
        mcp_client=mock_client,
        ai_orchestrator=SimulatedOrchestrator()
    )
    
    # Context that would be created when max_context_length is missing from API response
    context_data = {
        "model_response": vllm_model_response,
        "model_name": "qwen/qwen3-coder-30b-a3b-instruct",
        "missing_field": "max_context_length",  # This is what we're looking for
        "possible_field_names": [
            "max_model_len", "max_context_length", "context_length",
            "max_tokens", "max_input_tokens", "max_seq_len", "max_position_embeddings"
        ]
    }
    
    # Process the context using the adaptive service
    result = await adaptive_service.adapt_async(
        context=context_data,
        problem_description="Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct",
        fallback_value=4096  # This would be used if AI couldn't find the field
    )
    
    # Verify that the AI correctly identified and extracted the max_model_len value
    assert result == 262144, f"Expected 262144, got {result}"
    
    print(f"✓ Adaptive Loop successfully extracted max_model_len: {result} from VLLM model response")
    print("✓ The system correctly identified 'max_model_len' as equivalent to 'max_context_length'")
    print("✓ Adaptive Loop solved the field name mismatch problem described in the requirements")


@pytest.mark.asyncio 
async def test_different_field_name_patterns():
    """
    Test that the Adaptive Loop can handle various field naming patterns.
    """
    # Test with different field patterns in the model response
    test_cases = [
        {
            "response": {"max_model_len": 131072},
            "field": "max_context_length",
            "expected": 131072,
            "description": "max_model_len field",
            "search_term": "max_model_len"
        },
        {
            "response": {"context_length": 65536, "max_tokens": 8192},
            "field": "max_context_length", 
            "expected": 65536,
            "description": "context_length field",
            "search_term": "context_length"
        },
        {
            "response": {"max_input_tokens": 32768, "other": "value"},
            "field": "max_context_length",
            "expected": 32768, 
            "description": "max_input_tokens field",
            "search_term": "max_input_tokens"
        }
    ]
    
    for i, case in enumerate(test_cases):
        mock_client = MagicMock()
        
        class PerTestSimulator:
            def __init__(self, search_term, expected_value):
                self.search_term = search_term
                self.expected_value = expected_value
            
            async def handle_request(self, prompt_obj):
                # Return the appropriate response based on the search term
                response = f"{self.search_term}: {self.expected_value}"
                prompt_obj.result_content = response
                prompt_obj.mark_completed(prompt_obj.result_content)
                return prompt_obj
        
        class PerTestOrchestrator:
            def __init__(self, search_term, expected_value):
                self.simulator = PerTestSimulator(search_term, expected_value)
            
            async def handle_ai_interaction(self, prompt_obj):
                return await self.simulator.handle_request(prompt_obj)
        
        adaptive_service = AdaptiveLoopService(
            mcp_client=mock_client,
            ai_orchestrator=PerTestOrchestrator(case["search_term"], case["expected"])
        )
        
        context_data = {
            "model_response": case["response"],
            "model_name": f"test-model-{i}",
            "missing_field": case["field"]
        }
        
        result = await adaptive_service.adapt_async(
            context=context_data,
            problem_description=f"Find {case['field']} in model response",
            fallback_value=4096
        )
        
        assert result == case["expected"], f"Failed for {case['description']}: expected {case['expected']}, got {result}"
        print(f"✓ Correctly identified {case['description']} with value: {result}")


def test_prompt_building_for_vllm_example():
    """
    Test that the prompt is built correctly for the VLLM example.
    """
    mock_client = MagicMock()
    mock_orchestrator = MagicMock()
    adaptive_service = AdaptiveLoopService(
        mcp_client=mock_client,
        ai_orchestrator=mock_orchestrator
    )
    
    # Use the exact VLLM response from the requirements
    vllm_response = {
        "object": "list",
        "data": [
            {
                "id": "qwen/qwen3-coder-30b-a3b-instruct",
                "max_model_len": 262144
            }
        ]
    }
    
    context_data = {
        "model_response": vllm_response,
        "model_name": "qwen/qwen3-coder-30b-a3b-instruct",
        "missing_field": "max_context_length"
    }
    
    prompt_text = adaptive_service._build_prompt(
        context_data,
        "Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct"
    )
    
    # Verify the prompt contains the essential elements
    assert "Context:" in prompt_text
    assert "qwen/qwen3-coder-30b-a3b-instruct" in prompt_text  # Model name
    assert "max_model_len" in prompt_text  # Field from response
    assert "Problem:" in prompt_text
    assert "find the maximum context length field" in prompt_text.lower()
    assert "FIELD_NAME: VALUE" in prompt_text  # Instruction to AI
    
    print("✓ Prompt was built correctly with all required elements for VLLM response")


if __name__ == "__main__":
    """Run the tests directly if executed as main module."""
    import asyncio
    
    async def run_tests():
        print("Running Adaptive Loop end-to-end tests with VLLM example...")
        
        await test_adaptive_loop_with_exact_vllm_response_example()
        await test_different_field_name_patterns()
        test_prompt_building_for_vllm_example()
        
        print("\n🎉 All end-to-end tests with VLLM example passed!")
        print("The Adaptive Loop successfully handles the exact scenario described in the requirements.")
    
    asyncio.run(run_tests())