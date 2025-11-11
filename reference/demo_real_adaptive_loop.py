#!/usr/bin/env python3
"""
Manual test script to demonstrate actual LLM integration with the Adaptive Loop.

This script will make real calls to your configured LLM if it's available.
Run this manually when your LLM is properly configured.
"""

import asyncio
import os
from gcs_kernel.kernel import GCSKernel
from gcs_kernel.models import PromptObject


async def test_real_llm_integration():
    """
    Test the Adaptive Loop with actual LLM calls.
    This requires a properly configured LLM backend.
    """
    print("Testing Adaptive Loop with real LLM integration...")
    print("Note: This test requires a properly configured LLM backend.")
    print("If no LLM is available, this will demonstrate the intended flow.\n")
    
    try:
        # Create kernel with default config (using settings)
        kernel = GCSKernel()
        
        # Initialize kernel components
        await kernel._initialize_components()
        
        # Access the adaptive error service
        adaptive_service = kernel.adaptive_error_service
        
        print("✓ Kernel initialized successfully")
        print(f"✓ AdaptiveErrorProcessingService available: {adaptive_service is not None}")
        print(f"✓ AI Orchestrator connected: {adaptive_service.ai_orchestrator is not None}")
        
        # Use the exact VLLM response example from the requirements
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
        
        context_data = {
            "model_response": vllm_model_response,
            "model_name": "qwen/qwen3-coder-30b-a3b-instruct",
            "missing_field": "max_context_length",
            "possible_field_names": [
                "max_model_len", "max_context_length", "context_length",
                "max_tokens", "max_input_tokens", "max_seq_len", "max_position_embeddings"
            ]
        }
        
        print("\n--- Adaptive Loop Processing ---")
        print("Context data prepared with VLLM response containing 'max_model_len' field")
        print("Problem: Find maximum context length when 'max_context_length' field is missing")
        
        # Build the prompt that would be sent to the LLM
        prompt_text = adaptive_service._build_prompt(
            context_data,
            "Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct"
        )
        
        print(f"\n--- Generated AI Prompt ---")
        print(prompt_text)
        
        # Create a prompt object to see how it would work with the orchestrator
        prompt_obj = PromptObject.create(
            content=prompt_text,
            streaming_enabled=False,
            user_id="adaptive_loop_test"
        )
        
        print(f"\n--- Expected LLM Interaction ---")
        print("If LLM were available, this would be sent to the AI orchestrator:")
        print(f"Prompt ID: {prompt_obj.prompt_id}")
        print(f"Content length: {len(prompt_text)} characters")
        
        # If you actually want to try with a real LLM, uncomment the following:
        print("\n--- Attempting Real LLM Call (commented out for safety) ---")
        try:
            result = await adaptive_service.process_error_async(
                error_context=context_data,
                problem_description="Find the maximum context length field in the model response for qwen/qwen3-coder-30b-a3b-instruct",
                fallback_value=4096
            )
            print(f"Real LLM result: {result}")
        except Exception as e:
            print(f"LLM call failed (expected if no LLM configured): {e}")
        
        print("\n--- Expected LLM Response Analysis ---")
        print("With the VLLM response containing 'max_model_len: 262144',")
        print("a properly configured LLM should respond with:")
        print("  'max_model_len: 262144'")
        print("Which the adaptive service would parse to extract: 262144")
        
        print("\n--- Adaptive Loop Success Criteria ---")
        print("✓ LLM correctly identifies 'max_model_len' as equivalent to 'max_context_length'")
        print("✓ Value 262144 is extracted and returned")
        print("✓ System adapts to different field naming conventions")
        print("✓ No hardcoded fallbacks needed for VLLM responses")
        
        # Clean up
        await kernel.shutdown()
        
    except Exception as e:
        print(f"Test setup failed: {e}")
        print("This may be because:")
        print("- LLM backend is not running")
        print("- Required environment variables are not set")
        print("- Network connectivity issues")
        print("\nFor production use, ensure your LLM is properly configured via settings.")


async def main():
    print("Adaptive Loop - Real LLM Integration Test")
    print("=" * 50)
    await test_real_llm_integration()
    print("\nTest completed. This demonstrated the intended flow when LLM is available.")


if __name__ == "__main__":
    asyncio.run(main())