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

    async def process_user_input(self, user_input: str) -> str:
        """Process user input and generate response.
        
        Args:
            user_input (str): The user's input message.
            
        Returns:
            str: The generated response.
        """
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Generate response using LLM
        response = await self.llm_service.generate_response(user_input)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
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