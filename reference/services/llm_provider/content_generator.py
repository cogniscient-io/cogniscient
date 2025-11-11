"""
LLM Content Generator for GCS Kernel LLM Provider Backend.

This module implements the LLM content generator that extends the base generator
and follows Qwen Code patterns for content generation, using Pydantic Settings.
It supports multiple LLM providers through the provider factory.
"""

import logging
from typing import Any, AsyncIterator, Dict
from gcs_kernel.models import PromptObject
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.provider_factory import ProviderFactory


# Set up logging
logger = logging.getLogger(__name__)


class LLMContentGenerator(BaseContentGenerator):
    """
    LLM-specific content generator that extends the base generator and follows
    Qwen Code patterns for content generation, using Pydantic Settings.
    Supports multiple LLM providers through the provider factory.
    """

    def __init__(self, adaptive_error_service=None):
        # Initialize provider components
        # The provider factory will handle all configuration internally from settings
        self.provider_factory = ProviderFactory()

        # Let the provider factory create the provider with configuration from settings
        self.provider = self.provider_factory.create_provider_from_settings(adaptive_error_service)
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

        try:
            # Store all chunks to reconstruct the full response later
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

                # Store the chunk to reconstruct the full response later
                chunks_accumulated.append(chunk)

            # Convert accumulated chunks to full response format and process it
            full_response = self.process_streaming_chunks(chunks_accumulated)
            self.process_full_response(prompt_obj, full_response)

        except Exception as e:
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

    def process_streaming_chunks(self, chunks: list) -> Dict[str, Any]:
        """
        Process accumulated streaming chunks into a complete response.

        Args:
            chunks: List of streaming response chunks

        Returns:
            Complete response in OpenAI format
        """
        # Initialize variables to collect the full response for potential tool calls
        accumulated_tool_calls = []
        accumulated_content = ""

        # Process each chunk to accumulate content and tool calls
        for chunk in chunks:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})

                # Handle content chunks
                content = delta.get("content", "")
                if content:
                    accumulated_content += content

                # Handle tool call chunks - OpenAI streams tool calls as deltas too
                tool_calls_delta = delta.get("tool_calls")
                if tool_calls_delta:
                    # Process tool call deltas
                    for tool_call_delta in tool_calls_delta:
                        index = tool_call_delta.get("index")
                        # Ensure we have enough slots in accumulated_tool_calls
                        while len(accumulated_tool_calls) <= index:
                            accumulated_tool_calls.append({
                                "id": "",
                                "type": "",
                                "function": {"name": "", "arguments": ""}
                            })

                        # Update the appropriate tool call slot with the delta info
                        current_tc = accumulated_tool_calls[index]
                        if "id" in tool_call_delta:
                            current_tc["id"] = tool_call_delta["id"]
                        if "type" in tool_call_delta:
                            current_tc["type"] = tool_call_delta["type"]
                        if "function" in tool_call_delta:
                            function_delta = tool_call_delta["function"]
                            if "name" in function_delta:
                                current_tc["function"]["name"] += function_delta["name"]
                            if "arguments" in function_delta:
                                current_tc["function"]["arguments"] += function_delta["arguments"]

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
        if accumulated_tool_calls:
            message_obj["tool_calls"] = accumulated_tool_calls

        finish_reason = "tool_calls" if accumulated_tool_calls else "stop"

        full_response["choices"].append({
            "index": 0,
            "message": message_obj,
            "finish_reason": finish_reason
        })

        logger.debug(f"ContentGenerator process_streaming_chunks - accumulated_content: '{accumulated_content}', accumulated_tool_calls: {accumulated_tool_calls}")

        return full_response

