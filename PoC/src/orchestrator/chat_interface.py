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
        self.max_history_length = 20  # Maximum number of conversation turns to keep
        self.compression_threshold = 15  # Compress when history reaches this length
        
        # Register this chat interface with the UCS runtime
        if hasattr(orchestrator, 'ucs_runtime'):
            orchestrator.ucs_runtime.register_chat_interface(self)

    async def process_user_input(self, user_input: str) -> dict:
        """Process user input and generate response using LLM-driven agent selection.
        
        Args:
            user_input (str): The user's input message.
            
        Returns:
            dict: A dictionary containing the response and tool call information.
        """
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Check if we need to compress the conversation history
        if len(self.conversation_history) >= self.compression_threshold:
            await self._compress_conversation_history()
        
        # Generate response using LLM orchestrator which handles agent selection
        result = await self.orchestrator.process_user_request(user_input, self.conversation_history)
        
        # Add response to conversation history
        self.conversation_history.append({"role": "assistant", "content": result.get("response", result)})
        
        # Trim conversation history if it's too long
        if len(self.conversation_history) > self.max_history_length:
            self._trim_conversation_history()
        
        return result
    
    async def _compress_conversation_history(self) -> None:
        """Compress the conversation history to reduce context length."""
        if len(self.conversation_history) < 2:
            return
            
        # Use the LLM to summarize the conversation history
        try:
            compression_prompt = "Please summarize the following conversation history in a concise way, preserving the key points and context:\n\n"
            for turn in self.conversation_history[:-2]:  # Exclude the last two entries
                compression_prompt += f"{turn['role'].title()}: {turn['content']}\n"
            
            compression_prompt += "\nProvide a concise summary that captures the main topics and context of this conversation."
            
            compressed_summary = await self.llm_service.generate_response(compression_prompt)
            
            # Replace the conversation history with the summary
            self.conversation_history = [
                {"role": "system", "content": f"Previous conversation summary: {compressed_summary}"},
                self.conversation_history[-2],  # Last user input
                self.conversation_history[-1]   # Last assistant response
            ]
            
            logger.info("Conversation history compressed successfully")
        except Exception as e:
            logger.error(f"Failed to compress conversation history: {e}")
            # If compression fails, just trim the history instead
            self._trim_conversation_history()
    
    def _trim_conversation_history(self) -> None:
        """Trim the conversation history to the maximum length."""
        if len(self.conversation_history) > self.max_history_length:
            # Keep the most recent entries
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
    
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