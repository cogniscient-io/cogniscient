"""
Content Generator Interface for GCS Kernel LLM Provider Backend.

This module defines the core interfaces following ContentGenerator patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol, AsyncIterator
import asyncio

# Import PromptObject for type hints
if False:  # Avoid circular import issues
    from gcs_kernel.models import PromptObject


class ContentGenerator(Protocol):
    """
    Protocol for AI content generation providers.
    """
    
    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Generate a response to the given prompt object with potential tool calls.
        Operates on the live prompt object in place.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Returns:
            None. Updates the prompt object in place. Raises exception if there's an error.
        """
        ...
    
    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Stream a response to the given prompt object.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Yields:
            Partial response strings as they become available
        """
        ...
    
    def process_streaming_chunks(self, chunks: list) -> Dict[str, Any]:
        """
        Process accumulated streaming chunks into a complete response.
        
        Args:
            chunks: List of streaming response chunks
            
        Returns:
            Complete response in OpenAI format
        """
        ...


class OpenAICompatibleProvider(ABC):
    """
    Abstract base class for OpenAI-compatible providers.
    """
    
    @abstractmethod
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for API requests.
        
        Returns:
            Dictionary of headers to include in API requests
        """
        pass
    
    @abstractmethod
    def build_client(self):
        """
        Build the API client.
        
        Returns:
            Initialized API client instance
        """
        pass
    
    @abstractmethod
    def build_request(self, request: Dict[str, Any], user_prompt_id: str) -> Dict[str, Any]:
        """
        Enhance the OpenAI-compatible request with provider-specific features.
        
        Args:
            request: The base OpenAI-compatible request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            Enhanced request with provider-specific features
        """
        pass