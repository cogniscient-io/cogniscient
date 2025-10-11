"""
Conversation Manager Service for Adaptive Control System that handles
context and history management with MCP-discovered tools integration.

This service manages conversation history, compresses it when necessary,
and maintains context with MCP-discovered tools.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from cogniscient.engine.services.service_interface import Service
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class ConversationManagerService(Service):
    """
    Service that manages conversation history, compresses it when necessary,
    and maintains context with MCP-discovered tools.
    """
    
    def __init__(self,
                 max_history_length: int = 20,
                 max_context_tokens: int = 4096,
                 compression_threshold: int = 10,
                 mcp_service: Optional[MCPService] = None):
        """
        Initialize the conversation manager service.
        
        Args:
            max_history_length: Maximum number of conversation turns to keep
            max_context_tokens: Maximum number of tokens in context
            compression_threshold: Number of turns after which compression is applied
            mcp_service: MCP service for MCP-discovered tools context
        """
        self.max_history_length = max_history_length
        self.max_context_tokens = max_context_tokens
        self.compression_threshold = compression_threshold
        self.mcp_service = mcp_service
        
        # Store conversation histories by session ID
        self.conversation_histories: Dict[str, List[Dict[str, str]]] = {}
        self.conversation_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Statistics for monitoring
        self.total_conversations = 0
        self.compressed_conversations = 0
        self.context_updates = 0
        
        self.gcs_runtime = None  # Will be set by runtime
        
    async def initialize(self) -> bool:
        """
        Initialize the conversation manager service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Initialize MCP service if provided
        if self.mcp_service and hasattr(self.mcp_service, 'initialize'):
            await self.mcp_service.initialize()
        return True
        
    async def shutdown(self) -> bool:
        """
        Shutdown the conversation manager service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Clear all conversation histories
        self.conversation_histories.clear()
        self.conversation_contexts.clear()
        return True

    def set_runtime(self, runtime):
        """
        Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def create_conversation_session(self, session_id: str, initial_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique identifier for the conversation session
            initial_context: Initial context for the conversation
            
        Returns:
            True if session was created successfully, False otherwise
        """
        if session_id in self.conversation_histories:
            logger.warning(f"Conversation session {session_id} already exists")
            return False
        
        self.conversation_histories[session_id] = []
        self.conversation_contexts[session_id] = initial_context or {}
        self.total_conversations += 1
        logger.info(f"Created new conversation session: {session_id}")
        return True

    def end_conversation_session(self, session_id: str) -> bool:
        """
        End a conversation session and clean up resources.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            True if session was ended successfully, False otherwise
        """
        if session_id not in self.conversation_histories:
            logger.warning(f"Conversation session {session_id} does not exist")
            return False
        
        # Remove the conversation history and context
        del self.conversation_histories[session_id]
        del self.conversation_contexts[session_id]
        logger.info(f"Ended conversation session: {session_id}")
        return True

    def add_message_to_conversation(self, 
                                   session_id: str, 
                                   role: str, 
                                   content: str,
                                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Unique identifier for the conversation session
            role: Role of the message sender (e.g., 'user', 'assistant', 'system')
            content: Content of the message
            metadata: Optional metadata to associate with the message
            
        Returns:
            True if message was added successfully, False otherwise
        """
        if session_id not in self.conversation_histories:
            logger.error(f"Conversation session {session_id} does not exist")
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time(),
            "metadata": metadata or {}
        }
        
        self.conversation_histories[session_id].append(message)
        
        # Check if we need to compress the history
        if len(self.conversation_histories[session_id]) > self.compression_threshold:
            self._compress_history_if_needed(session_id)
        
        # Limit history length
        if len(self.conversation_histories[session_id]) > self.max_history_length:
            # Remove oldest messages
            excess = len(self.conversation_histories[session_id]) - self.max_history_length
            self.conversation_histories[session_id] = self.conversation_histories[session_id][excess:]
        
        logger.debug(f"Added message to conversation {session_id}, now has {len(self.conversation_histories[session_id])} messages")
        return True

    def _compress_history_if_needed(self, session_id: str):
        """
        Compress the conversation history if it exceeds the threshold.
        
        Args:
            session_id: Unique identifier for the conversation session
        """
        history = self.conversation_histories[session_id]
        
        if len(history) <= self.compression_threshold:
            return  # No need to compress yet
        
        # In a real implementation, we would use techniques like:
        # - Summarizing conversation segments
        # - Removing less important messages
        # - Using embeddings to identify key points
        # For now, we'll just log that compression would happen
        
        logger.info(f"Compression would be applied to conversation {session_id}, "
                   f"which has {len(history)} messages (threshold: {self.compression_threshold})")
        
        self.compressed_conversations += 1

    def get_conversation_history(self, 
                                session_id: str, 
                                limit: Optional[int] = None,
                                include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get the conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session
            limit: Optional limit on the number of messages to return
            include_system: Whether to include system messages
            
        Returns:
            List of messages in the conversation history
        """
        if session_id not in self.conversation_histories:
            logger.warning(f"Conversation session {session_id} does not exist")
            return []
        
        history = self.conversation_histories[session_id]
        
        if not include_system:
            history = [msg for msg in history if msg.get("role") != "system"]
        
        if limit:
            return history[-limit:]
        
        return history

    def update_conversation_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """
        Update the context for a conversation session.
        
        Args:
            session_id: Unique identifier for the conversation session
            context_updates: Dictionary of context updates to apply
            
        Returns:
            True if context was updated successfully, False otherwise
        """
        if session_id not in self.conversation_contexts:
            logger.error(f"Conversation session {session_id} does not exist")
            return False
        
        # Update the context with new information
        self.conversation_contexts[session_id].update(context_updates)
        self.context_updates += 1
        logger.debug(f"Updated context for conversation {session_id}")
        return True

    def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the context for a conversation session.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            Context dictionary for the conversation, or None if session doesn't exist
        """
        return self.conversation_contexts.get(session_id)

    async def get_context_with_mcp_tools(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation context enriched with MCP-discovered tools information.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            Context dictionary enhanced with MCP tools information
        """
        base_context = self.get_conversation_context(session_id) or {}
        
        # If MCP service is available, add MCP tools information
        if self.mcp_service:
            try:
                mcp_tools = await self.mcp_service.discover_agent_tools()
                base_context["mcp_discovered_tools"] = mcp_tools
                base_context["mcp_connected_agents"] = self.mcp_service.get_connected_agents()
            except Exception as e:
                logger.error(f"Error getting MCP tools for context: {e}")
                base_context["mcp_error"] = str(e)
        
        return base_context

    def clear_conversation_history(self, session_id: str) -> bool:
        """
        Clear the conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            True if history was cleared successfully, False otherwise
        """
        if session_id not in self.conversation_histories:
            logger.error(f"Conversation session {session_id} does not exist")
            return False
        
        self.conversation_histories[session_id] = []
        logger.info(f"Cleared conversation history for {session_id}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the conversation manager.
        
        Returns:
            Dictionary with usage statistics
        """
        # Calculate some derived statistics
        total_messages = sum(len(history) for history in self.conversation_histories.values())
        
        return {
            "total_conversations": self.total_conversations,
            "active_sessions": len(self.conversation_histories),
            "total_messages": total_messages,
            "compressed_conversations": self.compressed_conversations,
            "context_updates": self.context_updates,
            "avg_messages_per_session": total_messages / max(1, len(self.conversation_histories))
        }

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a conversation session.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            Summary of the conversation session, or None if session doesn't exist
        """
        if session_id not in self.conversation_histories:
            return None
        
        history = self.conversation_histories[session_id]
        
        # Calculate summary information
        user_messages = [m for m in history if m.get("role") == "user"]
        assistant_messages = [m for m in history if m.get("role") == "assistant"]
        
        # Get time span of conversation
        if history:
            start_time = history[0].get("timestamp", 0)
            end_time = history[-1].get("timestamp", 0)
            duration = end_time - start_time
        else:
            duration = 0
        
        return {
            "session_id": session_id,
            "total_messages": len(history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "system_messages": len([m for m in history if m.get("role") == "system"]),
            "duration_seconds": duration,
            "has_context": bool(self.conversation_contexts.get(session_id)),
            "context_keys": list(self.conversation_contexts.get(session_id, {}).keys()) if self.conversation_contexts.get(session_id) else []
        }