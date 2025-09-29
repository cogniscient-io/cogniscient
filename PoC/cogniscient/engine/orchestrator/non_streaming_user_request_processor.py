"""Module for non-streaming user request processing functionality in LLM Orchestration Engine."""

import logging
from typing import Dict, Any, List
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.orchestrator.base_user_request_handler import BaseUserRequestHandler

logger = logging.getLogger(__name__)


class NonStreamingUserRequestProcessor(BaseUserRequestHandler):
    """Handles processing of user requests without streaming support."""

    def __init__(self, gcs_runtime: GCSRuntime, llm_service: LLMService):
        """Initialize the non-streaming user request processor.
        
        Args:
            gcs_runtime (GCSRuntime): The GCS runtime instance to manage agents.
            llm_service (LLMService): The LLM service instance.
        """
        super().__init__(gcs_runtime, llm_service)

    async def process_user_request(self, user_input: str, conversation_history: List[Dict[str, str]]) -> dict:
        """Process user request using LLM to determine appropriate agents.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        return await self._execute_request_logic(
            user_input=user_input,
            conversation_history=conversation_history,
            streaming=False
        )