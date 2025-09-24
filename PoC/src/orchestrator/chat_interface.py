"""Chat Interface for LLM-Enhanced Adaptive Control System."""

import logging
from typing import Dict, Any, List
from src.services.llm_service import LLMService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ChatInterface:
    """Chat interface for human-in-the-loop interaction with the LLM orchestrator."""

    def __init__(self, orchestrator, max_history_length: int = None, compression_threshold: int = None):
        """Initialize chat interface with orchestrator.
        
        Args:
            orchestrator: The LLM orchestrator instance.
            max_history_length (int, optional): Maximum number of conversation turns to keep.
            compression_threshold (int, optional): Compress when history reaches this length.
        """
        self.orchestrator = orchestrator
        self.llm_service = LLMService()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = max_history_length or settings.max_history_length
        self.compression_threshold = compression_threshold or settings.compression_threshold
        
        # Validate parameters
        if self.compression_threshold >= self.max_history_length:
            raise ValueError("Compression threshold must be less than max history length")
        
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
        
        # Check if token counts are available in the result
        if isinstance(result, dict) and "token_counts" in result:
            token_counts = result["token_counts"]
            response = result.get("response", "")
            
            # Format the response to include token counts
            response_with_tokens = f"{response}\n\n[Token Usage: Input: {token_counts['input_tokens']}, Output: {token_counts['output_tokens']}, Total: {token_counts['total_tokens']}]"
            
            # Add the response with token counts to conversation history
            self.conversation_history.append({"role": "assistant", "content": response_with_tokens})
            
            # Update the result to include the formatted response
            result["response_with_tokens"] = response_with_tokens
        else:
            # Add response to conversation history as before
            response = result.get("response", result) if isinstance(result, dict) else result
            self.conversation_history.append({"role": "assistant", "content": response})
        
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
    
    def get_context_window_size(self) -> int:
        """Get the current context window size (total characters in conversation history).
        
        Returns:
            int: Total number of characters in the conversation history.
        """
        total_chars = 0
        for turn in self.conversation_history:
            total_chars += len(turn.get("content", ""))
        return total_chars
    
    def set_compression_parameters(self, max_history_length: int = None, compression_threshold: int = None) -> None:
        """Set compression parameters.
        
        Args:
            max_history_length (int, optional): Maximum number of conversation turns to keep.
            compression_threshold (int, optional): Compress when history reaches this length.
        """
        if max_history_length is not None:
            self.max_history_length = max_history_length
        if compression_threshold is not None:
            self.compression_threshold = compression_threshold
            
        # Validate parameters
        if self.compression_threshold >= self.max_history_length:
            raise ValueError("Compression threshold must be less than max history length")
    
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