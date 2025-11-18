"""
OpenAI Provider Implementation for GCS Kernel LLM Provider Backend.

This module implements the OpenAI provider following Qwen Code patterns.
"""

import httpx
from typing import Dict, Any
from gcs_kernel.models import PromptObject
from services.llm_provider.providers.base_provider import BaseProvider
from .openai_converter import OpenAIConverter


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation following Qwen Code patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI provider with configuration.
        Uses OpenAI-specific defaults when values are not provided in config.
        
        Args:
            config: Dictionary containing provider configuration
                   Expected keys: api_key, model, base_url, timeout, max_retries
        """
        # Set OpenAI-specific defaults if not provided in config
        config = config.copy()  # Avoid modifying the original config
        if "model" not in config:
            config["model"] = "gpt-4-turbo"
        if "base_url" not in config:
            config["base_url"] = "https://api.openai.com/v1"
        
        # Call the parent constructor with the updated config
        super().__init__(config)
        
        # Initialize the converter for this provider
        self._converter = OpenAIConverter(self.model)
    
    @property
    def converter(self):
        """
        The converter for this OpenAI provider to transform data between kernel and provider formats.
        This returns an OpenAI-compatible converter with minimal transformations.
        """
        return self._converter
    
    def build_headers(self) -> Dict[str, str]:
        """
        Build headers for OpenAI API requests following standard patterns.
        
        Returns:
            Dictionary of headers for OpenAI API requests
        """
        if not self.api_key:
            raise ValueError("API key is required for OpenAI provider")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        return headers
    
    def build_client(self):
        """
        Build the OpenAI API client.
        
        Returns:
            Initialized httpx.AsyncClient instance
        """
        return httpx.AsyncClient(timeout=self.timeout, headers=self.build_headers())
    
    def build_request(self, prompt_obj: 'PromptObject') -> Dict[str, Any]:
        """
        Build the request with OpenAI-specific features from a PromptObject.
        
        Args:
            prompt_obj: The PromptObject containing all necessary information
            
        Returns:
            Request with OpenAI-specific format and features
        """
        # Start with the messages from the prompt object
        # OpenAI-compliant: messages should contain the complete conversation history
        messages = prompt_obj.conversation_history.copy()
        
        # Log the messages for debugging to see if system message is present
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"OpenAIProvider build_request - conversation history: {messages}")
        
        # Create the OpenAI request from the prompt object fields
        openai_request = {
            "messages": messages,
            "model": self.model
        }
        
        # Add optional parameters if present in the prompt object

        if prompt_obj.max_tokens is not None:
            openai_request["max_tokens"] = prompt_obj.max_tokens
        if prompt_obj.temperature:
            openai_request["temperature"] = prompt_obj.temperature
        
        # Add tools if specified in the prompt object
        if prompt_obj.tool_policy and prompt_obj.tool_policy.value != "none":
            # In a real implementation, we would fetch tools based on policy
            # For now, we'll use any custom tools in the prompt object
            if prompt_obj.custom_tools:
                openai_request["tools"] = prompt_obj.custom_tools
        
        # Add the user ID for tracking
        if prompt_obj.user_id:
            openai_request["user"] = prompt_obj.user_id
        elif prompt_obj.prompt_id:
            # Use prompt_id if user_id is not available
            openai_request["user"] = prompt_obj.prompt_id
        
        # Add other fields that may be relevant from the prompt object
        if prompt_obj.streaming_enabled:
            openai_request["stream"] = True

        # Convert the request to OpenAI format using the converter
        openai_request = self.converter.convert_kernel_request_to_provider(openai_request)
        
        return openai_request

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model by querying the OpenAI API.
        This includes model capabilities like maximum context length.
        
        Args:
            model_name: Name of the model to get information for

        Returns:
            Dictionary containing model information including capabilities
        """
        import httpx
        import logging
        logger = logging.getLogger(__name__)

        # Build headers for the request
        headers = self.build_headers()

        # Use the models endpoint to get information about the model
        url = f"{self.base_url}/models/{model_name}"
        
        try:
            # Create a temporary client for this request
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    model_data = response.json()
                    logger.info(f"Successfully retrieved model info for {model_name}")
                    
                    # Extract max context length - some OpenAI API responses include this information
                    # In the future, we could also make a separate call to model-specific endpoints
                    # that provide more detailed information including context window size
                    max_context_length = None
                    
                    # Some OpenAI API responses include context length in various fields
                    # Check for different possible field names (including the VLLM response format like Qwen3)
                    if 'max_model_len' in model_data:
                        # VLLM and many other backends use this field name
                        max_context_length = model_data['max_model_len']
                    elif 'max_context_length' in model_data:
                        max_context_length = model_data['max_context_length']
                    elif 'max_input_tokens' in model_data:
                        max_context_length = model_data['max_input_tokens']
                    
                    # Here we go!!!!  The first Adaptive Loop in the system!
                    # If we couldn't extract from the API, use the AI service to determine the value
                    # This pattern allows us to adaptively learn about new models without hardcoding values
                    # increasing the capabilities of the system over time, if we were to keep track
                    # of these adaptively learned values in a persistent store.
                    if max_context_length is None:
                        # Prepare context for AI processing
                        context_data = {
                            "model_response": model_data,
                            "model_name": model_name,
                            "missing_field": "max_context_length",
                            "possible_field_names": [
                                "max_model_len", "max_context_length", "context_length",
                                "max_tokens", "max_input_tokens", "max_seq_len", "max_position_embeddings"
                            ]
                        }

                        # Use the adaptive loop service if available
                        if hasattr(self, 'adaptive_loop_service') and self.adaptive_loop_service:
                            ai_suggested_value = await self.adaptive_loop_service.adapt_async(
                                context=context_data,
                                problem_description=f"Find the maximum context length field in the model response for {model_name}",
                                fallback_value=4096  # Default fallback
                            )
                            logger.info(f"AI suggested max_context_length: {ai_suggested_value}")
                            max_context_length = ai_suggested_value
                        else:
                            # If adaptive loop service is not available, use intelligent defaults as fallback
                            if 'gpt-4-turbo' in model_name or 'gpt-4o' in model_name:
                                max_context_length = 128000
                            elif 'gpt-4' in model_name:
                                max_context_length = 128000
                            elif 'gpt-3.5-turbo' in model_name:
                                max_context_length = 16384
                            else:
                                max_context_length = 4096  # Default fallback
    
                    # Extract relevant information from the model data
                    # TODO: Yes, we can and should use the adaptive loop for all the fields
                    result = {
                        'id': model_data.get('id'),
                        'object': model_data.get('object'),
                        'created': model_data.get('created'),
                        'owned_by': model_data.get('owned_by'),
                        'max_context_length': max_context_length,
                        'capabilities': {
                            # Additional capabilities could be included here
                        }
                    }
                    return result
                else:
                    logger.error(f"Failed to retrieve model info: {response.status_code} - {response.text}")
                    # Return default info with the fallback value from settings
                    from common.settings import settings
                    return {
                        'id': model_name,
                        'max_context_length': settings.llm_max_tokens,
                        'capabilities': {}
                    }
        except Exception as e:
            logger.error(f"Error retrieving model info for {model_name}: {str(e)}")
            # Return default info with the fallback value from settings
            from common.settings import settings
            return {
                'id': model_name,
                'max_context_length': settings.llm_max_tokens,
                'capabilities': {}
            }

    def set_adaptive_error_service(self, adaptive_loop_service):
        """
        Set the adaptive loop service for this provider (using legacy method name for compatibility).

        Args:
            adaptive_loop_service: The adaptive loop service instance
        """
        self.adaptive_loop_service = adaptive_loop_service