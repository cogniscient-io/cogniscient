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
    async def generate_response(self, prompt: str, system_context: str = None) -> Any:
        """
        Generate a response to the given prompt with potential tool calls.
        
        Args:
            prompt: The input prompt
            system_context: Optional system context/prompt to provide to the LLM
            
        Returns:
            The generated response with potential tool calls
        """
        pass
    
    @abstractmethod
    async def stream_response(self, prompt: str, system_context: str = None) -> AsyncIterator[str]:
        """
        Stream a response to the given prompt.
        
        Args:
            prompt: The input prompt
            system_context: Optional system context/prompt to provide to the LLM
            
        Yields:
            Partial response strings as they become available
        """
        pass