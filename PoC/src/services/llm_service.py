"""
Generic LLM service using LiteLLM for transport.
"""

import json
import logging
from typing import Dict, Any, Optional, List
import litellm
from litellm import acompletion
from src.config.settings import settings

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging

logger = logging.getLogger(__name__)


class LLMService:
    """Generic service for interacting with LLM APIs using LiteLLM."""
    
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        """Initialize the LLM service.
        
        Args:
            model (str, optional): The model to use. If not provided, will use settings.
            api_key (str, optional): API key for the LLM provider.
            base_url (str, optional): Base URL for the LLM API.
        """
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        
        # Configure API keys if provided
        if self.api_key:
            # Try to infer the provider from the base_url or model name
            if self.base_url and "openai" in self.base_url:
                litellm.openai_key = self.api_key
            elif self.base_url and "anthropic" in self.base_url:
                litellm.anthropic_key = self.api_key
            elif "ollama" in self.model:
                # For Ollama, we don't need an API key, but we need to set the base URL
                pass
            else:
                # Default to OpenAI key if we can't determine the provider
                litellm.openai_key = self.api_key

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        return_token_counts: bool = False,  # New parameter to return token counts
        **kwargs
    ) -> str | Dict[str, Any]:
        """Generate a response from the LLM API.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries with 'role' and 'content'.
            model (str, optional): The model to use. If not provided, uses the instance model.
            temperature (float): Temperature for generation (0.0 to 1.0).
            max_tokens (int, optional): Maximum number of tokens to generate.
            return_token_counts (bool): Whether to return token count information.
            **kwargs: Additional arguments to pass to the LLM API.
            
        Returns:
            Union[str, Dict[str, Any]]: The generated response content or a dict with response and token counts.
        """
        try:
            # Use the provided model or the instance model
            model_to_use = model or self.model
            if not model_to_use:
                raise ValueError("No model specified. Please provide a model name.")
            
            # Prepare the request
            request_kwargs = {
                "model": model_to_use,
                "messages": messages,
                "temperature": temperature,
            }
            
            # Add optional parameters
            if max_tokens:
                request_kwargs["max_tokens"] = max_tokens
            if self.base_url and "ollama" in model_to_use:
                # For Ollama, we need to make sure we don't append /v1
                base_url = self.base_url.rstrip('/v1').rstrip('/') if self.base_url else None
                if base_url:
                    request_kwargs["api_base"] = base_url
            elif self.base_url:
                request_kwargs["base_url"] = self.base_url
                
            # Add any additional kwargs
            request_kwargs.update(kwargs)
            
            # Count input tokens before making the API request
            input_tokens = litellm.token_counter(
                model=model_to_use,
                messages=messages
            )
            
            # Make the API request
            response = await acompletion(**request_kwargs)
            
            # Count output tokens from the response
            output_tokens = litellm.token_counter(
                model=model_to_use,
                text=response.choices[0].message.content
            )
            
            # Log token usage
            logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {input_tokens + output_tokens}")
            
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Return token counts if requested
            if return_token_counts:
                return {
                    "response": content,
                    "token_counts": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    }
                }
            
            return content
                    
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            error_response = f"Error: Unable to generate response ({str(e)})"
            
            # Return error response with token counts if requested
            if return_token_counts:
                return {
                    "response": error_response,
                    "token_counts": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    }
                }
            
            return error_response