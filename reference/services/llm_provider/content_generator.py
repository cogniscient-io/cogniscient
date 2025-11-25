"""
LLM Content Generator for GCS Kernel LLM Provider Backend.

This module implements the LLM content generator that extends the base generator
and follows Qwen Code patterns for content generation, using Pydantic Settings.
It supports multiple LLM providers through the provider factory.
"""

import json
import logging
from typing import Any, AsyncIterator, Dict
from gcs_kernel.models import PromptObject
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.provider_factory import ProviderFactory
from services.tool_call_streaming_service import tool_call_streaming_service


# Set up logging
logger = logging.getLogger(__name__)


class LLMContentGenerator(BaseContentGenerator):
    """
    LLM-specific content generator that extends the base generator and follows
    Qwen Code patterns for content generation, using Pydantic Settings.
    Supports multiple LLM providers through the provider factory.
    """

    def __init__(self, adaptive_loop_service=None):
        # Initialize provider components
        # The provider factory will handle all configuration internally from settings
        self.provider_factory = ProviderFactory()

        # Let the provider factory create the provider with configuration from settings
        self.provider = self.provider_factory.create_provider_from_settings(adaptive_loop_service)
        self.pipeline = ContentGenerationPipeline(self.provider)
        
        # Initialize kernel reference (will be set by orchestrator)
        self.kernel = None

    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Generate a response to the given prompt object with potential tool calls.
        Operates on the live prompt object in place.

        Args:
            prompt_obj: The prompt object containing all necessary information

        Returns:
            None. Updates the prompt object in place. Raises exception if there's an error.
        """
        # Mark the prompt as processing
        prompt_obj.mark_processing()

        try:
            # Execute content generation through the pipeline using prompt object directly
            response = await self.pipeline.execute(prompt_obj)

            # Debug logging to see the raw response
            logger.debug(f"ContentGenerator - Raw response from pipeline: {response}")

            # Process the full response to update the prompt object
            self.process_full_response(prompt_obj, response)

        except Exception as e:
            prompt_obj.mark_error(str(e))
            raise

    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Stream a response to the given prompt object.

        Args:
            prompt_obj: The prompt object containing all necessary information

        Yields:
            Partial response strings as they become available
        """
        # Mark the prompt as processing
        prompt_obj.mark_processing()

        # Generate a unique ID for this streaming operation
        operation_id = f"{prompt_obj.prompt_id}_{id(prompt_obj)}"

        try:
            # Store all chunks to reconstruct the full response temporarily
            chunks_accumulated = []

            # Process streaming chunks from the pipeline and yield content as it comes
            async for chunk in self.pipeline.execute_stream(prompt_obj):
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})

                    # Yield content chunks as they become available
                    content = delta.get("content", "")
                    if content:
                        yield content

                    # Process any tool call deltas using the new streaming service
                    tool_calls_delta = delta.get("tool_calls")
                    if tool_calls_delta:
                        # Process each tool call delta with the streaming service
                        completed_tool_calls = tool_call_streaming_service.process_streaming_chunk(
                            chunk, operation_id
                        )

                        # Add completed tool calls to the prompt object if any
                        for tool_call in completed_tool_calls:
                            from gcs_kernel.tool_call_model import ToolCall
                            openai_tool_call = ToolCall.ensure_openai_format(tool_call)
                            prompt_obj.add_tool_call(openai_tool_call)

                # Store the chunk to reconstruct the full response later
                chunks_accumulated.append(chunk)

            # After streaming completes, get any remaining completed tool calls
            final_completed_tool_calls = tool_call_streaming_service.get_completed_tool_calls(operation_id)

            # Add any final completed tool calls to the prompt object
            for tool_call in final_completed_tool_calls:
                from gcs_kernel.tool_call_model import ToolCall
                openai_tool_call = ToolCall.ensure_openai_format(tool_call)
                prompt_obj.add_tool_call(openai_tool_call)

            # After streaming completes, reconstruct the full response from accumulated chunks
            # NOTE: For OpenAI-compatible APIs including vLLM, the streaming response provides
            # content deltas during the stream and potentially a final chunk with finish_reason,
            # but may not include post-processing metadata like usage statistics that would
            # be available in a non-streaming response. The process_streaming_chunks method
            # reconstructs the complete message content and structure from the streamed deltas.
            full_response = self.process_streaming_chunks(chunks_accumulated, operation_id)

            # Process the reconstructed full response
            self.process_full_response(prompt_obj, full_response)

        except Exception as e:
            # Reset the parser state if there's an error
            tool_call_streaming_service.reset_parser(operation_id)
            prompt_obj.mark_error(str(e))
            raise

    def process_full_response(self, prompt_obj: 'PromptObject', full_response: Dict[str, Any]) -> None:
        """
        Process the full response from either generate_response or stream_response
        and update the prompt object with the result content and tool calls.
        Both methods now pass the same format - a complete response dict.

        Args:
            prompt_obj: The prompt object to update
            full_response: The complete response from the LLM provider in OpenAI format
        """
        logger.debug(f"ContentGenerator process_full_response - received full_response: {full_response}")

        if full_response:
            # Extract content from the complete response
            choices = full_response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                prompt_obj.result_content = message.get("content", "")

                logger.debug(f"ContentGenerator process_full_response - extracted content: '{prompt_obj.result_content}'")

                # Add any tool calls to the prompt object (but don't execute them)
                # Execution is handled by the orchestrator/turn manager
                tool_calls = message.get("tool_calls", [])
                logger.debug(f"ContentGenerator process_full_response - found {len(tool_calls)} tool calls: {tool_calls}")

                if tool_calls:
                    for tool_call in tool_calls:
                        # Ensure tool call is in OpenAI format using ToolCall utility
                        from gcs_kernel.tool_call_model import ToolCall
                        openai_tool_call = ToolCall.ensure_openai_format(tool_call)
                        logger.debug(f"ContentGenerator process_full_response - adding tool call: {openai_tool_call}")
                        prompt_obj.add_tool_call(openai_tool_call)

                    logger.debug(f"ContentGenerator process_full_response - after adding tool calls, prompt_obj.tool_calls: {prompt_obj.tool_calls}")
            else:
                # Fallback in case the response doesn't have choices
                prompt_obj.result_content = full_response.get('content', '')
                logger.debug(f"ContentGenerator process_full_response - no choices found, using fallback content: '{prompt_obj.result_content}'")

            prompt_obj.mark_completed(prompt_obj.result_content)

        logger.debug(f"ContentGenerator process_full_response - finished, result_content: '{prompt_obj.result_content}', tool_calls count: {len(prompt_obj.tool_calls)}")

    def process_streaming_chunks(self, chunks: list, operation_id: str = None) -> Dict[str, Any]:
        """
        Process accumulated streaming chunks into a complete response.

        Args:
            chunks: List of streaming response chunks
            operation_id: Optional operation ID to reference completed tool calls from streaming service

        Returns:
            Complete response in OpenAI format
        """
        # Initialize variables to collect the full response for potential tool calls
        accumulated_content = ""
        final_finish_reason = None  # Track the finish reason from the final chunk

        # Process each chunk to accumulate content
        for chunk in chunks:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})

                # Handle content chunks
                content = delta.get("content", "")
                if content:
                    accumulated_content += content

                # Check if this chunk contains the finish_reason (which would be in the choice, not delta)
                # This is important for capturing the final message object's finish_reason
                chunk_finish_reason = choices[0].get("finish_reason")
                if chunk_finish_reason:
                    # If we have a finish_reason in this chunk, it's likely the final chunk
                    final_finish_reason = chunk_finish_reason

        # Construct the full response
        full_response = {
            "choices": []
        }

        # Add the message to the choices
        message_obj = {
            "role": "assistant"
        }
        if accumulated_content:
            message_obj["content"] = accumulated_content

        # If we have an operation ID, get completed tool calls from the streaming service
        if operation_id:
            # Get completed tool calls for this operation without permanently removing them
            completed_tool_calls = tool_call_streaming_service.peek_completed_tool_calls(operation_id)
            if completed_tool_calls:
                # Format tool calls in OpenAI format
                formatted_tool_calls = []
                for tc in completed_tool_calls:
                    formatted_tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("args", {}))
                        }
                    })
                message_obj["tool_calls"] = formatted_tool_calls

        # Use the finish_reason from the final chunk if available, otherwise determine it based on tool calls
        finish_reason = final_finish_reason if final_finish_reason else (
            "tool_calls" if message_obj.get("tool_calls") else "stop"
        )

        full_response["choices"].append({
            "index": 0,
            "message": message_obj,
            "finish_reason": finish_reason
        })

        logger.debug(f"ContentGenerator process_streaming_chunks - accumulated_content: '{accumulated_content}', finish_reason: {finish_reason}")

        return full_response

