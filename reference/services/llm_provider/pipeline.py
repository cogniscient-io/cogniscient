"""
Content Generation Pipeline for GCS Kernel LLM Provider Backend.

This module implements the content generation pipeline following Qwen Code's ContentGenerationPipeline patterns.
"""

import asyncio
import json
from typing import Any, Dict, AsyncIterator
import httpx
from services.llm_provider.converter import ContentConverter
from services.llm_provider.providers.base_provider import BaseOpenAIProvider


class ContentGenerationPipeline:
    """
    Processing pipeline for content generation following Qwen Code's ContentGenerationPipeline pattern.
    """
    
    def __init__(self, provider: BaseOpenAIProvider):
        self.provider = provider
        self.converter = ContentConverter(provider.model)
        
    async def execute(self, request: Dict[str, Any], user_prompt_id: str) -> Any:
        """
        Execute content generation request following Qwen Code patterns.
        
        Args:
            request: The content generation request
            user_prompt_id: Unique identifier for the user prompt
            
        Returns:
            The generated content response
        """
        # Convert request to provider format
        provider_request = self.converter.convert_kernel_request_to_provider(request)
        
        # Enhance request with provider-specific features
        enhanced_request = self.provider.build_request(provider_request, user_prompt_id)
        
        # Call the provider API
        async with httpx.AsyncClient(timeout=self.provider.timeout) as client:
            headers = self.provider.build_headers()
            response = await client.post(
                f"{self.provider.base_url}/chat/completions",
                headers=headers,
                json=enhanced_request
            )
            response.raise_for_status()
            provider_response = response.json()
            
        # Convert response back to kernel format
        kernel_response = self.converter.convert_provider_response_to_kernel(provider_response)
        return kernel_response
    
    async def execute_stream(self, request: Dict[str, Any], user_prompt_id: str) -> AsyncIterator[str]:
        """
        Execute streaming content generation request following Qwen Code patterns.
        
        Args:
            request: The content generation request
            user_prompt_id: Unique identifier for the user prompt
            
        Yields:
            Partial content responses as they become available
        """
        # Convert request to provider format for streaming
        request_copy = request.copy()
        request_copy["stream"] = True
        provider_request = self.converter.convert_kernel_request_to_provider(request_copy)
        
        # Enhance request with provider-specific features
        enhanced_request = self.provider.build_request(provider_request, user_prompt_id)
        
        # Call the provider API with streaming
        async with httpx.AsyncClient(timeout=self.provider.timeout) as client:
            headers = self.provider.build_headers()
            async with client.stream(
                "POST",
                f"{self.provider.base_url}/chat/completions",
                headers=headers,
                json=enhanced_request
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix
                        if line and line != "[DONE]":
                            try:
                                chunk = json.loads(line)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                continue