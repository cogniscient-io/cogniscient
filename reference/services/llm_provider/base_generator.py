"""
Abstract Base Content Generator for GCS Kernel LLM Provider Backend.

This module defines the abstract base class for content generators that
the ai_orchestrator will depend on, providing proper abstraction.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from gcs_kernel.models import PromptObject


class BaseContentGenerator(ABC):
    """
    Abstract base class for content generators that the ai_orchestrator will use.
    This provides proper abstraction between the orchestrator and specific implementations.
    The actual initialization and configuration is up to each implementation.
    """
    
    @abstractmethod
    async def generate_response(self, prompt_obj: 'PromptObject') -> None:
        """
        Generate a response to the given prompt object with potential tool calls.
        Operates on the live prompt object in place.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Returns:
            None. Updates the prompt object in place. Raises exception if there's an error.
        """
        pass
    
    @abstractmethod
    async def stream_response(self, prompt_obj: 'PromptObject') -> AsyncIterator[str]:
        """
        Stream a response to the given prompt object.
        
        Args:
            prompt_obj: The prompt object containing all necessary information
            
        Yields:
            Partial response strings as they become available
        """
        pass
    
    def process_streaming_chunks(self, chunks: list) -> Dict[str, Any]:
        """
        Process accumulated streaming chunks into a complete response.
        
        Args:
            chunks: List of streaming response chunks
            
        Returns:
            Complete response in OpenAI format
        """
        # Default implementation that just returns an empty response
        # Subclasses should override this with their specific logic
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": "stop"
            }]
        }
    
