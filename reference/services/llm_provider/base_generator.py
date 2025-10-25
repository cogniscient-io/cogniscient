"""
Abstract Base Content Generator for GCS Kernel LLM Provider Backend.

This module defines the abstract base class for content generators that
the ai_orchestrator will depend on, providing proper abstraction.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseContentGenerator(ABC):
    """
    Abstract base class for content generators that the ai_orchestrator will use.
    This provides proper abstraction between the orchestrator and specific implementations.
    The actual initialization and configuration is up to each implementation.
    """
    
    @abstractmethod
    async def generate_response(self, prompt: str) -> Any:
        """
        Generate a response to the given prompt with potential tool calls.
        
        Args:
            prompt: The input prompt
            
        Returns:
            The generated response with potential tool calls
        """
        pass
    
    @abstractmethod
    async def process_tool_result(self, tool_result: Any, conversation_history: list = None) -> Any:
        """
        Process a tool result and continue the conversation.
        
        Args:
            tool_result: The result from a tool execution
            conversation_history: The conversation history to maintain context
            
        Returns:
            The updated response after processing the tool result
        """
        pass
    
    @abstractmethod
    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Stream a response to the given prompt.
        
        Args:
            prompt: The input prompt
            
        Yields:
            Partial response strings as they become available
        """
        pass