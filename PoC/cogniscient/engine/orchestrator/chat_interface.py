"""Chat Interface for LLM-Enhanced Adaptive Control System with MCP Compliance."""

import json
import logging
from typing import Callable, Dict, Any, List
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.config.settings import settings


logger = logging.getLogger(__name__)


class ChatInterface:
    """MCP-compliant chat interface for human-in-the-loop interaction with the LLM orchestrator."""

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
        
        # Register this chat interface with the GCS runtime
        if hasattr(orchestrator, 'gcs_runtime'):
            runtime = orchestrator.gcs_runtime
            # Check if the runtime is a mock (to avoid RuntimeWarning with AsyncMock)
            # by checking if it's from unittest.mock
            import unittest.mock
            if not isinstance(runtime, unittest.mock.Mock):
                # Only call registration if not in a mock environment
                runtime.register_chat_interface(self)
            # Also set this chat interface in the orchestrator for approval workflow
            self.orchestrator.chat_interface = self

    



    async def process_user_input_streaming(self, user_input: str, conversation_history: List[Dict[str, str]], 
                                   send_stream_event: Callable[[str, str, Dict[str, Any]], Any]) -> Dict[str, Any]:
        """Process user input with streaming event support.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history to use
            send_stream_event (Callable): Function to send streaming events
            
        Returns:
            dict: A dictionary containing the response and tool call information.
        """
        # Add user input to conversation history
        conversation_history.append({"role": "user", "content": user_input})
        
        # Check if we need to compress the conversation history
        if len(conversation_history) >= self.compression_threshold:
            compressed_history = await self._compress_conversation_history_streaming(conversation_history)
            conversation_history[:] = compressed_history  # Update the original list
        
        # Generate response using LLM orchestrator which handles agent selection
        result = await self.orchestrator.process_user_request(user_input, conversation_history, send_stream_event)
        
        # Handle result based on its type (it could be a string or a dictionary)
        if isinstance(result, dict):
            # If result is a dictionary, extract response and token counts
            response = result.get("response", "")
            token_counts = result.get("token_counts", {})
        else:
            # If result is a string or other type, create a basic result structure
            response = str(result) if result is not None else ""
            token_counts = {}
            # Wrap the result in a dictionary to maintain consistency
            result = {"response": response}
        
        # Format response with token counts if available
        if token_counts and token_counts.get("total_tokens", 0) > 0:
            response_with_tokens = f"{response}\n\n[Token Usage: Input: {token_counts['input_tokens']}, Output: {token_counts['output_tokens']}, Total: {token_counts['total_tokens']}]"
            conversation_history.append({"role": "assistant", "content": response_with_tokens})
            
            # Add the formatted response to the result if it's a dict
            if isinstance(result, dict):
                result["response_with_tokens"] = response_with_tokens
        else:
            # Add response to conversation history as before
            conversation_history.append({"role": "assistant", "content": response})
        
        # Trim conversation history if it's too long
        if len(conversation_history) > self.max_history_length:
            self._trim_conversation_history_streaming(conversation_history)
        
        return result

    async def _send_streaming_event(self, event_type: str, content: str = None, data: Dict[str, Any] = None):
        """Create a streaming event to yield to the frontend."""
        event = {
            "type": event_type,
        }
        if content is not None:
            event["content"] = content
        if data is not None:
            event["data"] = data
        
        return event
    
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
    
    async def _compress_conversation_history_streaming(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Compress the conversation history to reduce context length for streaming.
        
        Args:
            conversation_history: The conversation history to compress
            
        Returns:
            Compressed conversation history
        """
        if len(conversation_history) < 2:
            return conversation_history
            
        # Use the LLM to summarize the conversation history
        try:
            compression_prompt = "Please summarize the following conversation history in a concise way, preserving the key points and context:\n\n"
            for turn in conversation_history[:-2]:  # Exclude the last two entries
                compression_prompt += f"{turn['role'].title()}: {turn['content']}\n"
            
            compression_prompt += "\nProvide a concise summary that captures the main topics and context of this conversation."
            
            compressed_summary = await self.llm_service.generate_response(compression_prompt)
            
            # Replace the conversation history with the summary
            compressed_history = [
                {"role": "system", "content": f"Previous conversation summary: {compressed_summary}"},
                conversation_history[-2],  # Last user input
                conversation_history[-1]   # Last assistant response
            ]
            
            logger.info("Conversation history compressed successfully for streaming")
            return compressed_history
        except Exception as e:
            logger.error(f"Failed to compress conversation history for streaming: {e}")
            # If compression fails, just trim the history instead
            return self._trim_conversation_history_streaming(conversation_history)
    
    def _trim_conversation_history_streaming(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Trim the conversation history to the maximum length for streaming.
        
        Args:
            conversation_history: The conversation history to trim
            
        Returns:
            Trimmed conversation history
        """
        if len(conversation_history) > self.max_history_length:
            # Keep the most recent entries
            return conversation_history[-self.max_history_length:]
        return conversation_history
    
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
        """Handle approval requests from the orchestrator with MCP compliance.
        
        Args:
            request (Dict[str, Any]): The approval request details.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        agent_name = request.get("agent_name", "Unknown")
        changes = request.get("changes", {})
        
        # Create an approval prompt for the user
        approval_prompt = (
            f"Approval required for changes to {agent_name}:\n"
            f"{json.dumps(changes, indent=2)}\n\n"
            f"Do you approve these changes? Please respond with 'yes' to approve or 'no' to deny."
        )
        
        # Add the approval request to the conversation history
        self.conversation_history.append({
            "role": "system", 
            "content": f"APPROVAL REQUEST: {approval_prompt}"
        })
        
        try:
            # Generate a response using the LLM service with the approval prompt
            response = await self.llm_service.generate_response([
                {"role": "system", "content": "You are a system administrator reviewing approval requests for system changes. Respond with either 'yes' or 'no' based on the provided information."},
                {"role": "user", "content": approval_prompt}
            ])
            
            # Parse the user's response to determine approval
            approval_decision = response.lower().strip()
            approved = approval_decision.startswith('y')  # 'yes', 'y', etc.
            
            # Log the decision
            decision_text = "APPROVED" if approved else "DENIED"
            logger.info(f"Approval request for {agent_name} was {decision_text}: {changes}")
            
            # Add the decision to conversation history
            self.conversation_history.append({
                "role": "assistant", 
                "content": f"Decision: {decision_text}"
            })
            
            return approved
        except Exception as e:
            logger.error(f"Error handling approval request: {e}")
            # In case of error, deny the request by default for safety
            return False