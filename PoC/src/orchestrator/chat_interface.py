"""Chat Interface for LLM-Enhanced Adaptive Control System."""

import logging
from typing import Dict, Any, List
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ChatInterface:
    """Chat interface for human-in-the-loop interaction with the LLM orchestrator."""

    def __init__(self, orchestrator):
        """Initialize chat interface with orchestrator.
        
        Args:
            orchestrator: The LLM orchestrator instance.
        """
        self.orchestrator = orchestrator
        self.llm_service = LLMService()
        self.conversation_history: List[Dict[str, str]] = []

    async def process_user_input(self, user_input: str) -> dict:
        """Process user input and generate response using LLM-driven agent selection.
        
        Args:
            user_input (str): The user's input message.
            
        Returns:
            dict: A dictionary containing the response and tool call information.
        """
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Generate response using LLM orchestrator which handles agent selection
        result = await self.orchestrator.process_user_request(user_input, self.conversation_history)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": result.get("response", result)})
        
        return result
    
    async def handle_approval_request(self, request: Dict[str, Any]) -> bool:
        """Handle approval requests from the orchestrator.
        
        Args:
            request (Dict[str, Any]): The approval request details.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        # In a real implementation, this would present the approval request to the user
        # and wait for their response. For now, we'll log the request and return False.
        logger.warning(f"Approval request received: {request}")
        # For this implementation, we'll return False to indicate denial
        # A real implementation would have a mechanism to get user input
        return False