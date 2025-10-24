"""
OpenAI Content Generator for GCS Kernel LLM Provider Backend.

This module implements the OpenAI content generator that extends the base generator
and follows Qwen Code patterns for content generation, using Pydantic Settings.
"""

from typing import Any, Dict, AsyncIterator
from gcs_kernel.models import ToolResult
from services.llm_provider.config import llm_settings
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.provider_factory import ProviderFactory


class OpenAIContentGenerator(BaseContentGenerator):
    """
    OpenAI content generator that extends the base generator and follows 
    Qwen Code patterns for content generation, using Pydantic Settings.
    """
    
    def __init__(self):
        # Use the Pydantic settings to access settings
        self.api_key = llm_settings.api_key
        if not self.api_key:
            raise ValueError("API key is required but not provided in environment variables")
        self.model = llm_settings.model
        self.base_url = llm_settings.base_url
        self.timeout = llm_settings.timeout
        self.max_retries = llm_settings.max_retries
        
        # Initialize base class with config values
        config_for_base = {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
        super().__init__(config_for_base)
        
        # Initialize provider components
        self.provider_factory = ProviderFactory()
        provider_type = llm_settings.provider_type
        provider_config = {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
        self.provider = self.provider_factory.create_provider(provider_type, provider_config)
        self.pipeline = ContentGenerationPipeline(self.provider)
    
    async def generate_response(self, prompt: str) -> Any:
        """
        Generate a response to the given prompt with potential tool calls.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            prompt: The input prompt
            
        Returns:
            The generated response with potential tool calls
        """
        # Prepare the request in the format expected by the pipeline
        request = {
            "prompt": prompt,
            "model": self.model,
            "temperature": llm_settings.temperature,
            "max_tokens": llm_settings.max_tokens
        }
        
        # Generate content using the pipeline
        response = await self.generate_content(request, user_prompt_id=f"prompt_{id(prompt)}")
        
        # Convert to the expected response format
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
                self.name = "openai_response"  # For attribute access
        
        return ResponseObj(
            content=response.get("content", ""),
            tool_calls=response.get("tool_calls", [])
        )
    
    async def process_tool_result(self, tool_result: ToolResult) -> Any:
        """
        Process a tool result and continue the conversation.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            tool_result: The result from a tool execution
            
        Returns:
            The updated response after processing the tool result
        """
        # For now, return a simple response indicating the tool was processed
        # In a full implementation, this would send the tool result back to the LLM
        class ResponseObj:
            def __init__(self, content):
                self.content = content
        
        return ResponseObj(content=f"Processed tool result: {tool_result.return_display}")
    
    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Stream a response to the given prompt.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            prompt: The input prompt
            
        Yields:
            Partial response strings as they become available
        """
        request = {
            "prompt": prompt,
            "model": self.model,
            "temperature": llm_settings.temperature,
            "max_tokens": llm_settings.max_tokens
        }
        
        async for chunk in self.generate_content_stream(request, user_prompt_id=f"stream_{id(prompt)}"):
            yield chunk

    # Methods following Qwen Code patterns
    async def generate_content(self, request: Dict[str, Any], user_prompt_id: str) -> Any:
        """
        Generate content following Qwen Code patterns.
        
        Args:
            request: The content generation request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            The generated content response
        """
        return await self.pipeline.execute(request, user_prompt_id)
    
    async def generate_content_stream(self, request: Dict[str, Any], user_prompt_id: str) -> AsyncIterator[Any]:
        """
        Generate content in streaming mode following Qwen Code patterns.
        
        Args:
            request: The content generation request
            user_prompt_id: Unique identifier for the user prompt
            
        Yields:
            Partial content responses as they become available
        """
        async for chunk in self.pipeline.execute_stream(request, user_prompt_id):
            yield chunk
    
    async def count_tokens(self, request: Dict[str, Any]) -> Dict[str, int]:
        """
        Count tokens in the request following Qwen Code patterns.
        
        Args:
            request: The request to count tokens for
            
        Returns:
            Token count information
        """
        # For now, return a rough estimate based on character count
        # In a full implementation, this would use a proper token counting library
        content = request.get("prompt", "")
        total_tokens = max(1, len(content) // 4)  # Rough estimate: 1 token ≈ 4 characters
        return {
            "total_tokens": total_tokens,
            "prompt_tokens": total_tokens,
            "completion_tokens": 0  # Will be updated after generation
        }
    
    async def embed_content(self, request: Dict[str, Any]) -> Any:
        """
        Generate embeddings following Qwen Code patterns.
        
        Args:
            request: The embedding request with content
            
        Returns:
            Embedding response
        """
        # Extract text from request
        text = request.get("content", "")
        
        # In a real implementation, this would call the provider's embedding API
        # For now, return a placeholder
        # This would need to be implemented properly with the actual provider
        return {
            "embedding": [0.0] * 1536,  # Example: OpenAI's embedding dimension
            "model": self.provider.model
        }