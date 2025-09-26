"""Module for user request processing functionality in LLM Orchestration Engine."""

import logging
from typing import AsyncGenerator, Callable, Dict, Any, List
from src.ucs_runtime import UCSRuntime
from src.services.llm_service import LLMService
from src.orchestrator.streaming_user_request_processor import StreamingUserRequestProcessor
from src.orchestrator.non_streaming_user_request_processor import NonStreamingUserRequestProcessor

logger = logging.getLogger(__name__)


class UserRequestProcessor:
    """Handles processing of user requests with LLM to determine appropriate agents."""

    def __init__(self, ucs_runtime: UCSRuntime, llm_service: LLMService):
        """Initialize the user request processor.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime instance to manage agents.
            llm_service (LLMService): The LLM service instance.
        """
        self.ucs_runtime = ucs_runtime
        self.llm_service = llm_service
        
        # Initialize the specialized processors
        self.streaming_processor = StreamingUserRequestProcessor(ucs_runtime, llm_service)
        self.non_streaming_processor = NonStreamingUserRequestProcessor(ucs_runtime, llm_service)

    async def process_user_request_streaming(self, user_input: str, conversation_history: List[Dict[str, str]], 
                                           send_stream_event: Callable[[str, str, Dict[str, Any]], Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process user request using LLM to determine appropriate agents with streaming support.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            send_stream_event (Callable): Function to send streaming events
            
        Yields:
            dict: Streaming events containing response parts, tool calls, etc.
        """
        async for result in self.streaming_processor.process_user_request_streaming(
            user_input, conversation_history, send_stream_event
        ):
            yield result

    async def process_user_request(self, user_input: str, conversation_history: List[Dict[str, str]]) -> dict:
        """Process user request using LLM to determine appropriate agents.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        return await self.non_streaming_processor.process_user_request(user_input, conversation_history)

    def _calculate_context_size(self, conversation_history: List[Dict[str, str]]) -> int:
        """Calculate the total context size in characters.
        
        Args:
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            int: Total number of characters in the conversation history.
        """
        return self.non_streaming_processor._calculate_context_size(conversation_history)

    async def _compress_conversation_history(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Compress the conversation history to reduce context size.
        
        Args:
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            List[Dict[str, str]]: Compressed conversation history.
        """
        return await self.non_streaming_processor._compress_conversation_history(conversation_history)

    def _generate_error_response(self, tool_calls: List[Dict[str, Any]], user_input: str) -> str:
        """Generate a correct response when we know the domain doesn't exist or the website is inaccessible.
        
        Args:
            tool_calls (List[Dict[str, Any]]): The tool calls that were made.
            user_input (str): The original user input.
            
        Returns:
            str: A correct response based on the tool call results.
        """
        return self.non_streaming_processor._generate_error_response(tool_calls, user_input)

    def _extract_suggested_agents(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract suggested agents from the LLM's response text.
        
        Args:
            response_text (str): The LLM's response text.
            
        Returns:
            List[Dict[str, Any]]: A list of suggested agents.
        """
        return self.non_streaming_processor._extract_suggested_agents(response_text)

    def _parse_llm_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text that should contain a JSON object.
        
        Args:
            response_text (str): The raw text response from the LLM.
            
        Returns:
            Dict[str, Any]: The parsed JSON object, or an error object if parsing fails.
        """
        return self.non_streaming_processor._parse_llm_json_response(response_text)