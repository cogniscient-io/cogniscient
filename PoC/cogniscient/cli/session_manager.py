"""
Session management for Cogniscient interactive CLI.

This module handles session state, conversation history, and context tracking.
"""
from typing import Any, Dict, List
from datetime import datetime
from cogniscient.engine.gcs_runtime import GCSRuntime

class SessionManager:
    """
    Manages session state for the interactive CLI.
    """
    
    def __init__(self, gcs_runtime: GCSRuntime):
        """
        Initialize the session manager.
        
        Args:
            gcs_runtime: GCS runtime instance to maintain session context
        """
        self.gcs_runtime = gcs_runtime
        self.conversation_history: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
        self.session_context: Dict[str, Any] = {}
        self.temporary_states: Dict[str, Any] = {}
        
        # Register this session manager with the GCS runtime
        # so it can be notified of configuration changes
        self.gcs_runtime.register_chat_interface(self)
    
    def add_interaction(self, user_input: str, response: str) -> None:
        """
        Add a user interaction to the conversation history.
        
        Args:
            user_input: The user's input
            response: The system's response
        """
        interaction = {
            "timestamp": datetime.now(),
            "user_input": user_input,
            "response": response
        }
        self.conversation_history.append(interaction)
    
    def get_recent_context(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent interactions from the conversation history.
        
        Args:
            count: Number of recent interactions to return
            
        Returns:
            List of recent interactions
        """
        return self.conversation_history[-count:]
    
    def clear_conversation_history(self) -> None:
        """
        Clear the conversation history.
        """
        self.conversation_history = []
    
    def update_session_context(self, key: str, value: Any) -> None:
        """
        Update a value in the session context.
        
        Args:
            key: Context key to update
            value: Value to set
        """
        self.session_context[key] = value
    
    def get_session_context(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the session context.
        
        Args:
            key: Context key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value from session context or default
        """
        return self.session_context.get(key, default)
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        return {
            "start_time": self.session_start_time,
            "interaction_count": len(self.conversation_history),
            "active_config": self.gcs_runtime.config_service.get_current_config_name(),
            "active_agents": list(self.gcs_runtime.agents.keys()),
            "session_context": self.session_context
        }
    
    def close_session(self) -> None:
        """
        Clean up the session before closing.
        """
        # Unregister from the GCS runtime
        self.gcs_runtime.unregister_chat_interface(self)
    
    def set_temporary_state(self, key: str, value: Any) -> None:
        """
        Set a temporary state for multi-step workflows.
        
        Args:
            key: Key for the temporary state
            value: Value to store
        """
        self.temporary_states[key] = value
    
    def get_temporary_state(self, key: str, default: Any = None) -> Any:
        """
        Get a temporary state value.
        
        Args:
            key: Key for the temporary state
            default: Default value if key doesn't exist
            
        Returns:
            Value or default
        """
        return self.temporary_states.get(key, default)
    
    def clear_temporary_state(self, key: str = None) -> None:
        """
        Clear temporary state(s).
        
        Args:
            key: Optional key to clear only that specific state; if None, clear all
        """
        if key is None:
            self.temporary_states.clear()
        else:
            self.temporary_states.pop(key, None)
    
    def get_interaction_by_index(self, index: int) -> Dict[str, Any]:
        """
        Get a specific interaction from the conversation history by index.
        
        Args:
            index: Zero-based index of the interaction to retrieve
            
        Returns:
            The interaction at the specified index, or None if index is out of range
        """
        if 0 <= index < len(self.conversation_history):
            return self.conversation_history[index]
        return None
    
    def find_recent_interactions_by_content(self, content_keyword: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find recent interactions that contain a specific keyword.
        
        Args:
            content_keyword: Keyword to search for in interactions
            limit: Maximum number of results to return
            
        Returns:
            List of matching interactions
        """
        keyword_lower = content_keyword.lower()
        matches = []
        
        # Search from most recent to oldest
        for interaction in reversed(self.conversation_history):
            if (keyword_lower in interaction.get('user_input', '').lower() or
                keyword_lower in interaction.get('response', '').lower()):
                matches.append(interaction)
                if len(matches) >= limit:
                    break
        
        # Reverse back to chronological order
        matches.reverse()
        return matches