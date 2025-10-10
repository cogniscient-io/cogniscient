"""
LiteLLM adapter for interacting with LLM APIs.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
import litellm
from litellm import acompletion
from cogniscient.engine.config.settings import settings

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging

logger = logging.getLogger(__name__)


class LiteLLMAdapter:
    """Adapter for interacting with LLM APIs using LiteLLM."""
    
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None, token_manager=None):
        """Initialize the LiteLLM adapter.
        
        Args:
            model (str, optional): The model to use. If not provided, will use settings.
            api_key (str, optional): API key for the LLM provider.
            base_url (str, optional): Base URL for the LLM API.
            token_manager: Token manager for handling authentication for providers like Qwen.
        """
        self.model = model or settings.llm_model
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.token_manager = token_manager  # Store for authentication when needed
        
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

    async def close(self):
        """Close any resources held by the adapter, particularly async HTTP clients."""
        try:
            import gc
            
            # Process any pending logs to prevent the async_success_handler warning
            if hasattr(litellm, 'batch_logging'):
                await litellm.batch_logging()

            # Try to explicitly handle any pending async_success_handler tasks
            # But avoid complex task management that can cause recursion
            try:
                loop = asyncio.get_running_loop()
                
                # Get all pending tasks
                all_pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                
                # Cancel logging-related tasks specifically
                for task in all_pending_tasks:
                    if 'async_success_handler' in str(task) or 'Logging.async_success_handler' in str(task):
                        try:
                            task.cancel()
                        except Exception:
                            pass  # Task already cancelled or done
                            
            except RuntimeError:
                # No running event loop, we can't check for pending tasks
                pass

            # Close all cached async HTTP clients to prevent resource leaks
            # Try direct access to async client sessions
            if hasattr(litellm, 'aclient_session') and litellm.aclient_session:
                try:
                    await litellm.aclient_session.aclose()
                except Exception:
                    pass  # Ignore errors during session close

            # Try to properly close module-level clients
            if hasattr(litellm, 'module_level_aclient'):
                try:
                    close_method = litellm.module_level_aclient.close
                    # Check if the close method is async (coroutine)
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        # If it's not a coroutine, call it directly
                        close_method()
                except Exception:
                    pass  # Ignore errors during close attempt

            if hasattr(litellm, 'module_level_client'):
                try:
                    litellm.module_level_client.close()
                except Exception:
                    pass  # Ignore errors during close attempt

            # Try to properly close cached clients in LLMClientCache
            if hasattr(litellm, 'in_memory_llm_clients_cache'):
                try:
                    # Get the cached clients and close them
                    cache = litellm.in_memory_llm_clients_cache
                    if hasattr(cache, 'cache_dict'):
                        for key, cached_client in list(cache.cache_dict.items()):
                            if hasattr(cached_client, 'aclose'):
                                # Async close method
                                try:
                                    await cached_client.aclose()
                                except Exception:
                                    pass  # Ignore errors during close attempt
                            elif hasattr(cached_client, 'close'):
                                # Check if close method is async (coroutine)
                                close_method = cached_client.close
                                if asyncio.iscoroutinefunction(close_method):
                                    try:
                                        await close_method()
                                    except Exception:
                                        pass  # Ignore errors during close attempt
                                else:
                                    # Sync close method
                                    try:
                                        close_method()
                                    except Exception:
                                        pass  # Ignore errors during close attempt
                        # Clear the cache after closing
                        cache.cache_dict.clear()
                except Exception:
                    pass  # Ignore errors during cache cleanup

            # Additional cleanup for async success handler tasks if they exist
            # Clear callback lists to prevent async handlers from running
            if hasattr(litellm, 'success_callback'):
                litellm.success_callback = []
            if hasattr(litellm, 'failure_callback'):
                litellm.failure_callback = []
            if hasattr(litellm, 'async_success_callback'):
                litellm.async_success_callback = []
            if hasattr(litellm, '_async_success_callback'):
                litellm._async_success_callback = []
            if hasattr(litellm, '_async_failure_callback'):
                litellm._async_failure_callback = []
            if hasattr(litellm, 'logging_obj'):
                # Force process any pending logging
                litellm.success_callback = []
                litellm.async_success_callback = []

            # Wait a bit more for any remaining async operations to complete
            try:
                loop = asyncio.get_running_loop()
                # Small delay to allow any final cleanup, but avoid complex task management
                await asyncio.sleep(0.05)  # Reduced sleep time
            except RuntimeError:
                # No running event loop
                pass

            # Specifically try to close any lingering aiohttp connections
            # This is the key fix for the unclosed client session warnings
            try:
                # Access internal aiohttp connections in LiteLLM and close them
                if hasattr(litellm, 'llm_provider_handlers') and litellm.llm_provider_handlers:
                    for provider_handler in litellm.llm_provider_handlers.values():
                        if hasattr(provider_handler, 'async_client') and provider_handler.async_client:
                            try:
                                await provider_handler.async_client.aclose()
                            except Exception:
                                pass  # Ignore errors during close attempt
            except Exception:
                pass  # Ignore if this attribute doesn't exist

            # Additional aiohttp-specific cleanup - try to close any lingering aiohttp resources
            try:
                # Access aiohttp connector connections and close them
                if hasattr(litellm, 'aclient_session') and litellm.aclient_session:
                    if hasattr(litellm.aclient_session, '_connector'):
                        try:
                            await litellm.aclient_session._connector.close()
                        except Exception:
                            pass  # Connector might already be closed
            except Exception:
                pass  # Safe to ignore if these attributes don't exist

            # Force garbage collection to clean up any remaining resources
            gc.collect()
        except Exception as e:
            logger.warning(f"Error while closing LiteLLM async clients: {e}")

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        return_token_counts: bool = False,  # New parameter to return token counts
        stream: bool = False,  # New parameter to enable streaming
        provider: str = "litellm",  # Provider-specific logic
        **kwargs
    ) -> str | Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """Generate a response from the LLM API.
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries with 'role' and 'content'.
            model (str, optional): The model to use. If not provided, uses the instance model.
            temperature (float): Temperature for generation (0.0 to 1.0).
            max_tokens (int, optional): Maximum number of tokens to generate.
            return_token_counts (bool): Whether to return token count information.
            stream (bool): Whether to stream the response.
            provider (str): The provider to use (e.g., "litellm", "qwen")
            **kwargs: Additional arguments to pass to the LLM API.
            
        Returns:
            Union[str, Dict[str, Any], AsyncGenerator]: The generated response content, a dict with response and token counts,
            or an async generator for streaming responses.
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
            if stream:
                request_kwargs["stream"] = True
            if self.base_url and "ollama" in model_to_use:
                # For Ollama, we need to make sure we don't append /v1
                base_url = self.base_url.rstrip('/v1').rstrip('/') if self.base_url else None
                if base_url:
                    request_kwargs["api_base"] = base_url
            elif self.base_url:
                request_kwargs["base_url"] = self.base_url

            # Handle Qwen/DashScope-specific logic
            if provider == "qwen":
                if self.token_manager:
                    # Get valid token for authentication
                    token = await self.token_manager.get_valid_access_token()
                    if not token:
                        logger.error("No valid access token available for Qwen provider")
                        # For both streaming and non-streaming return None as expected by tests
                        if stream:
                            async def none_generator():
                                yield {
                                    "content": None,
                                    "type": "error"
                                }
                                if return_token_counts:
                                    yield {
                                        "type": "token_counts",
                                        "token_counts": {
                                            "input_tokens": 0,
                                            "output_tokens": 0,
                                            "total_tokens": 0
                                        }
                                    }
                            
                            return none_generator()
                        else:
                            # Return None as expected by tests when no token is available
                            if return_token_counts:
                                return {
                                    "response": None,
                                    "token_counts": {
                                        "input_tokens": 0,
                                        "output_tokens": 0,
                                        "total_tokens": 0
                                    }
                                }
                            
                            return None
                    
                    # Add authentication headers to kwargs
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "api-key": token  # DashScope also expects this header
                    }
                    
                    # Update kwargs to include headers
                    if "headers" in request_kwargs:
                        request_kwargs["headers"].update(headers)
                    else:
                        request_kwargs["headers"] = headers
                
                # Set base_url for DashScope-compatible endpoint
                request_kwargs["api_base"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            # Add any additional kwargs
            request_kwargs.update(kwargs)
            
            # Handle custom headers - if headers are provided in kwargs, ensure they're properly formatted
            if "headers" in request_kwargs and request_kwargs["headers"]:
                # Ensure headers are properly formatted for LiteLLM
                headers = request_kwargs["headers"]
                if isinstance(headers, dict):
                    # LiteLLM expects headers to be merged properly
                    pass  # Already in the right format
                else:
                    # If it's not a dict, try to convert or skip
                    del request_kwargs["headers"]  # Remove invalid headers
            
            if stream:
                # Return an async generator for streaming
                async def stream_generator():
                    full_content = ""
                    input_tokens = 0
                    output_tokens = 0
                    
                    # Count input tokens before starting to stream
                    try:
                        input_tokens = litellm.token_counter(
                            model=model_to_use,
                            messages=messages
                        )
                    except:
                        input_tokens = 0  # Fallback if token counting fails
                    
                    # Get the streaming response - acompletion with stream=True must be awaited in async context
                    response_stream = await acompletion(**request_kwargs)
                    
                    # Iterate over the response stream
                    async for chunk in response_stream:
                        content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                        full_content += content
                        
                        # Yield the chunk as it comes
                        yield {
                            "content": content,
                            "type": "chunk"
                        }
                        
                        # Update output token count as we go, if possible
                        try:
                            # Some providers include usage in chunks
                            if hasattr(chunk, 'usage') and chunk.usage:
                                if hasattr(chunk.usage, 'completion_tokens'):
                                    output_tokens = chunk.usage.completion_tokens
                        except:
                            pass  # Ignore if usage info isn't available
                    
                    # If output tokens weren't available during streaming, count at the end
                    if output_tokens == 0:
                        try:
                            output_tokens = litellm.token_counter(
                                model=model_to_use,
                                text=full_content
                            )
                        except:
                            output_tokens = 0  # Fallback if token counting fails
                    
                    # Log token usage
                    logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {input_tokens + output_tokens}")
                    
                    if return_token_counts:
                        yield {
                            "type": "token_counts",
                            "token_counts": {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens
                            }
                        }
                
                return stream_generator()
            else:
                # Make the API request (non-streaming)
                response = await acompletion(**request_kwargs)
                
                # Extract the content from the response
                content = response.choices[0].message.content
                
                # Count tokens from the response - these are often available in the response itself
                input_tokens = getattr(response, 'usage', {}).get('prompt_tokens', 0)
                output_tokens = getattr(response, 'usage', {}).get('completion_tokens', 0)
                if input_tokens == 0:
                    # Fallback to manual token counting
                    input_tokens = litellm.token_counter(model=model_to_use, messages=messages)
                if output_tokens == 0:
                    # Fallback to manual token counting
                    output_tokens = litellm.token_counter(model=model_to_use, text=content)
                
                # Log token usage
                logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {input_tokens + output_tokens}")
                
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
            
            # For streaming, we'd need to handle this differently
            if stream:
                async def error_generator():
                    yield {
                        "content": error_response,
                        "type": "error"
                    }
                    if return_token_counts:
                        yield {
                            "type": "token_counts",
                            "token_counts": {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "total_tokens": 0
                            }
                        }
                
                return error_generator()
            else:
                # Return error response with token counts if requested (non-streaming)
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