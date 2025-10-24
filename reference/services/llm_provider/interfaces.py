"""
Content Generator Interface for GCS Kernel LLM Provider Backend.

This module defines the core interfaces following ContentGenerator patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol, AsyncIterator
import asyncio


class ContentGenerator(Protocol):
    """
    Protocol for AI content generation providers.
    """
    
    async def generate_content(self, request: Dict[str, Any], user_prompt_id: str) -> Any:
        """
        Generate content based on the provided request.
        
        Args:
            request: The content generation request with prompt and context
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            The generated content response
        """
        ...
    
    async def generate_content_stream(self, request: Dict[str, Any], user_prompt_id: str) -> AsyncIterator[Any]:
        """
        Generate content in streaming mode following.
        
        Args:
            request: The content generation request with prompt and context
            user_prompt_id: Unique identifier for the user prompt
            
        Yields:
            Partial content responses as they become available
        """
        ...
    
    async def count_tokens(self, request: Dict[str, Any]) -> Dict[str, int]:
        """
        Count the number of tokens in the provided request.
        
        Args:
            request: The request to count tokens for
            
        Returns:
            Token count information
        """
        ...
        
    async def embed_content(self, request: Dict[str, Any]) -> Any:
        """
        Generate embeddings for the provided content following.
        
        Args:
            request: The embedding request with content
            
        Returns:
            Embedding response
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