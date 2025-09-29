"""Module for streaming user request processing functionality in LLM Orchestration Engine."""

import logging
from typing import AsyncGenerator, Callable, Dict, Any, List
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.orchestrator.base_user_request_handler import BaseUserRequestHandler

logger = logging.getLogger(__name__)


class StreamingUserRequestProcessor(BaseUserRequestHandler):
    """Handles processing of user requests with streaming support."""

    def __init__(self, gcs_runtime: GCSRuntime, llm_service: LLMService):
        """Initialize the streaming user request processor.
        
        Args:
            gcs_runtime (GCSRuntime): The GCS runtime instance to manage agents.
            llm_service (LLMService): The LLM service instance.
        """
        super().__init__(gcs_runtime, llm_service)

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
        result = await self._execute_request_logic(
            user_input=user_input,
            conversation_history=conversation_history,
            streaming=True,
            send_stream_event=send_stream_event
        )
        
        # Yield the final result
        yield result