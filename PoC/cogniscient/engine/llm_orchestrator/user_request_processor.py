"""Module for user request processing functionality in LLM Orchestration Engine."""

import logging
from typing import Callable, Dict, Any, List
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService
from cogniscient.llm.llm_provider_service import LLMService
from cogniscient.engine.llm_orchestrator.base_user_request_handler import BaseUserRequestHandler

logger = logging.getLogger(__name__)


class UserRequestProcessor(BaseUserRequestHandler):
    """Handles processing of user requests with LLM to determine appropriate agents."""

    def __init__(self, gcs_runtime: GCSRuntime, llm_service: ContextualLLMService = None, provider_manager: LLMService = None):
        """Initialize the user request processor.
        
        Args:
            gcs_runtime (GCSRuntime): The GCS runtime instance to manage agents.
            llm_service (ContextualLLMService): The contextual LLM service instance.
            provider_manager (LLMService): The LLM service instance for LLM operations.
        """
        # Use the contextual LLM service from the GCS runtime if available
        if llm_service is not None:
            actual_service = llm_service
        elif hasattr(gcs_runtime, 'llm_service') and gcs_runtime.llm_service:
            actual_service = gcs_runtime.llm_service
        elif provider_manager:
            from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService
            actual_service = ContextualLLMService(provider_manager=provider_manager)
        else:
            raise ValueError("Either llm_service, gcs_runtime with llm_service, or provider_manager must be provided")
        
        super().__init__(gcs_runtime, actual_service)

    async def process_user_request(self, user_input: str, conversation_history: List[Dict[str, str]], 
                                send_stream_event: Callable[[str, str, Dict[str, Any]], Any]) -> Dict[str, Any]:
        """Process user request using LLM to determine appropriate agents with streaming support.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            send_stream_event (Callable): Function to send streaming events
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        # Execute the request logic which will send events via send_stream_event
        result = await self._execute_request_logic(
            user_input=user_input,
            conversation_history=conversation_history,
            send_stream_event=send_stream_event
        )
        
        return result