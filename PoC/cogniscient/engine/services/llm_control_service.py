"""
LLM Control Service that handles retry logic, error handling, and orchestration
that was previously embedded in the LLM service itself.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator, Callable
from cogniscient.engine.config.settings import settings
from cogniscient.llm.llm_provider_service import LLMService
from cogniscient.engine.services.service_interface import Service

logger = logging.getLogger(__name__)


class LLMControlService(Service):
    """
    Service that handles LLM orchestration, including retry logic, error handling,
    and request management that belongs in the system control layer rather than
    the LLM provider implementation.
    """
    
    def __init__(self, llm_service: LLMService, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the LLM control service.
        
        Args:
            llm_service: The underlying LLM service to delegate to
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
        """
        self.llm_service = llm_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Statistics for monitoring
        self.total_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        
    async def initialize(self):
        """Initialize the service and register with MCP if available."""
        # Initialize the underlying LLM service
        if hasattr(self.llm_service, 'initialize'):
            await self.llm_service.initialize()
    
    async def shutdown(self):
        """Shutdown the service and underlying LLM service."""
        if hasattr(self.llm_service, 'close'):
            await self.llm_service.close()
    
    async def generate_response_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Generate a response with retry logic and error handling.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for generation
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Generated response content or None if all retries failed
        """
        self.total_requests += 1
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Attempt to generate response
                response = await self.llm_service.generate_response(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # If successful, return the response
                if response is not None:
                    return response
                
            except Exception as e:
                logger.warning(f"LLM request failed on attempt {attempt + 1}: {str(e)}")
                last_exception = e
                
                # If we're on the last attempt, break to return the error
                if attempt == self.max_retries:
                    break
                
                # Wait before retrying
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # If all attempts failed
        self.failed_requests += 1
        logger.error(f"LLM request failed after {self.max_retries + 1} attempts: {str(last_exception)}")
        
        # Return an error response instead of raising
        error_response = f"Error: Unable to generate response after {self.max_retries + 1} attempts"
        return error_response
    
    async def generate_response_with_streaming(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream_handler: Optional[Callable[[str, str], Any]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a response with streaming support and error handling.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for generation
            temperature: Temperature for generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            stream_handler: Optional handler to process streaming chunks
            **kwargs: Additional arguments to pass to the LLM
            
        Yields:
            Chunks of the response
        """
        self.total_requests += 1
        
        try:
            # Attempt to generate response with streaming
            response = await self.llm_service.generate_response(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,  # Enable streaming
                **kwargs
            )
            
            # Check if response is an async generator
            if hasattr(response, '__aiter__'):
                async for chunk in response:
                    # Call the stream handler if provided
                    if stream_handler:
                        try:
                            stream_handler("chunk", str(chunk))
                        except Exception as e:
                            logger.warning(f"Stream handler error: {e}")
                    
                    # Yield the chunk
                    yield chunk
            else:
                # If not streaming, return as a single chunk
                yield {"content": response, "type": "complete"}
                
        except Exception as e:
            logger.error(f"Streaming LLM request failed: {str(e)}")
            self.failed_requests += 1
            
            # Yield an error chunk
            yield {
                "content": f"Error: Unable to generate streaming response: {str(e)}",
                "type": "error"
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about LLM service usage.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.total_requests - self.failed_requests) / self.total_requests if self.total_requests > 0 else 0,
            "active_provider": getattr(self.llm_service, 'current_provider', 'unknown')
        }
    
    async def switch_provider(self, provider_name: str) -> bool:
        """
        Switch the active LLM provider.
        
        Args:
            provider_name: Name of the provider to switch to
            
        Returns:
            True if provider was switched successfully, False otherwise
        """
        try:
            success = self.llm_service.set_provider(provider_name)
            logger.info(f"Provider switched to: {provider_name}" if success else f"Failed to switch to provider: {provider_name}")
            return success
        except Exception as e:
            logger.error(f"Error switching provider to {provider_name}: {str(e)}")
            return False
    
    async def validate_provider_credentials(self, provider_name: str) -> bool:
        """
        Validate credentials for a specific provider.
        
        Args:
            provider_name: Name of the provider to validate credentials for
            
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            return await self.llm_service.check_provider_credentials(provider_name)
        except Exception as e:
            logger.error(f"Error validating credentials for {provider_name}: {str(e)}")
            return False

    async def get_available_providers(self) -> List[str]:
        """
        Get a list of available providers.
        
        Returns:
            List of available provider names
        """
        try:
            return await self.llm_service.get_available_providers()
        except Exception as e:
            logger.error(f"Error getting available providers: {str(e)}")
            return []