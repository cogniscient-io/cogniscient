"""
LLM Content Generator for GCS Kernel LLM Provider Backend.

This module implements the LLM content generator that extends the base generator
and follows Qwen Code patterns for content generation, using Pydantic Settings.
It supports multiple LLM providers through the provider factory.
"""

from typing import Any, Dict, AsyncIterator
from gcs_kernel.models import ToolResult
from services.config import settings
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.pipeline import ContentGenerationPipeline
from services.llm_provider.providers.provider_factory import ProviderFactory


class LLMContentGenerator(BaseContentGenerator):
    """
    LLM-specific content generator that extends the base generator and follows 
    Qwen Code patterns for content generation, using Pydantic Settings.
    Supports multiple LLM providers through the provider factory.
    """
    
    def __init__(self):
        # Get settings from config service
        llm_config = settings
        
        # Use the settings to access settings
        self.api_key = llm_config.llm_api_key
        if not self.api_key:
            raise ValueError("API key is required but not provided in environment variables")
        self.model = llm_config.llm_model
        self.base_url = llm_config.llm_base_url
        self.timeout = llm_config.llm_timeout
        self.max_retries = llm_config.llm_max_retries
        
        # Initialize provider components
        self.provider_factory = ProviderFactory()
        provider_type = llm_config.llm_provider_type
        provider_config = {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
        self.provider = self.provider_factory.create_provider(provider_type, provider_config)
        self.pipeline = ContentGenerationPipeline(self.provider)
    
    async def generate_response(self, prompt: str, system_context: str = None, tools: list = None) -> Any:
        """
        Generate a response to the given prompt with potential tool calls.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            prompt: The input prompt
            system_context: Optional system context/prompt to provide to the LLM
            tools: Optional list of tools to provide to the LLM for native function calling
            
        Returns:
            The generated response with potential tool calls
        """
        # Prepare the request in the format expected by the pipeline
        llm_config = settings
        request = {
            "prompt": prompt,
            "model": self.model,
            "temperature": llm_config.llm_temperature,
            "max_tokens": llm_config.llm_max_tokens
        }
        
        # Add system context if provided
        if system_context:
            request["system_prompt"] = system_context
        
        # Add tools if provided
        if tools:
            request["tools"] = tools
        
        # Generate content using the pipeline
        response = await self.generate_content(request, user_prompt_id=f"prompt_{id(prompt)}")
        
        # Use the shared helper method to format the response consistently
        return self._format_response(response)
    
