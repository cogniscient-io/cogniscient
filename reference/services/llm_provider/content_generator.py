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
        
        # Use the converter to properly format the response
        # But first check if the response is already in the expected kernel format (from pipeline)
        if isinstance(response, dict) and "content" in response and "tool_calls" in response:
            # The response is already in the expected format (likely from pipeline)
            formatted_response = response
        else:
            try:
                formatted_response = self.converter.convert_provider_response_to_kernel(response)
            except Exception:
                # If converter fails (e.g., in mock scenarios), use fallback format
                # This handles cases where the response format doesn't match expected structure
                formatted_response = {
                    "content": response.get("content", "") if isinstance(response, dict) else str(response),
                    "tool_calls": response.get("tool_calls", []) if isinstance(response, dict) else []
                }
        
        # Additional processing: Check if the LLM returned JSON tool calls in the content
        # and extract them if the tool_calls field is empty
        content = formatted_response.get("content", "")
        tool_calls = formatted_response.get("tool_calls", [])
        
        # Debug: Print what we got from the pipeline before processing
        print(f"DEBUG: Content generator received from pipeline - content: {repr(content)}, tool_calls: {tool_calls}")
        
        # If no tool calls were extracted by the converter but content might contain them
        if not tool_calls and content.strip():
            extracted_tool_calls = self._extract_tool_calls_from_content(content)
            if extracted_tool_calls:
                # Update tool calls and clean content
                tool_calls = extracted_tool_calls
                # Remove tool call JSON from content
                cleaned_content = self._remove_tool_calls_from_content(content)
                content = cleaned_content
        
        # Convert to the expected response format
        # Also convert tool call dictionaries to proper ToolCall objects if they aren't already
        from .tool_call_processor import ToolCall
        
        processed_tool_calls = []
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                # Convert dictionary to ToolCall object
                # Handle different possible structures of tool call dictionaries
                if "function" in tool_call:  # OpenAI-style structure
                    function_data = tool_call.get("function", {})
                    # Parse arguments string to dictionary if needed
                    arguments = function_data.get("arguments", {})
                    if isinstance(arguments, str):
                        import json
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, keep original string value
                            arguments = function_data.get("arguments", {})
                    
                    processed_tool_calls.append(ToolCall(
                        id=tool_call.get("id", ""),
                        name=function_data.get("name", ""),
                        arguments=arguments
                    ))
                else:  # Direct structure
                    processed_tool_calls.append(ToolCall(
                        id=tool_call.get("id", ""),
                        name=tool_call.get("name", ""),
                        arguments=tool_call.get("arguments", {})
                    ))
            else:
                # Already a ToolCall object
                processed_tool_calls.append(tool_call)
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
                self.name = "openai_response"  # For attribute access
        
        return ResponseObj(
            content=content,
            tool_calls=processed_tool_calls
        )
    
    def _extract_tool_calls_from_content(self, content: str):
        """
        Extract potential tool calls from content that might include JSON objects.
        
        Args:
            content: The content string that might contain JSON tool calls
        Returns:
            List of extracted tool call objects, or empty list if none found
        """
        import re
        import json
        import logging
        
        # More comprehensive regex pattern to match JSON objects representing tool calls
        # Handles multiple JSON objects in the same content
        tool_call_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{(?:[^{}]|{[^{}]*})*\}\s*\}'
        
        # Find all occurrences of potential tool call JSON
        potential_tool_calls = re.findall(tool_call_pattern, content)
        
        extracted_calls = []
        
        for potential_call in potential_tool_calls:
            try:
                tool_call = json.loads(potential_call.strip())
                # Validate that it has the expected structure
                if "name" in tool_call and "parameters" in tool_call:
                    extracted_calls.append(tool_call)
            except json.JSONDecodeError as e:
                logging.debug(f"Failed to parse potential tool call JSON: {potential_call}, Error: {e}")
                # Skip invalid JSON
                continue
        
        return extracted_calls
    
    def _remove_tool_calls_from_content(self, content: str) -> str:
        """
        Remove JSON tool calls from content string.
        
        Args:
            content: The content string that might contain JSON tool calls
        Returns:
            Content string with JSON tool calls removed
        """
        import re
        
        # Pattern to match tool calls and remove them
        tool_call_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}'
        
        # Remove all tool call JSON objects from the content
        cleaned_content = re.sub(tool_call_pattern, '', content).strip()
        
        # Also remove any lines that are just whitespace or braces
        lines = cleaned_content.split('\n')
        cleaned_lines = [line for line in lines if line.strip() and not line.strip() in ['{', '}', ''] and not line.strip().startswith('//')]
        
        return '\n'.join(cleaned_lines).strip()
    
    async def process_tool_result(self, tool_result: ToolResult, conversation_history: list = None) -> Any:
        """
        Process a tool result and continue the conversation.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            tool_result: The result from a tool execution
            conversation_history: The conversation history to maintain context
            
        Returns:
            The updated response after processing the tool result
        """
        # Prepare the request in the format expected by the pipeline
        # This should send the tool result back to the LLM to continue the conversation
        llm_config = settings
        
        # Use the conversation history if provided, otherwise create minimal messages array
        if conversation_history:
            # Create messages array from the conversation history
            messages = conversation_history.copy()  # Use existing conversation
            
            # Add the tool result as a new message
            messages.append({
                "role": "tool",
                "content": tool_result.llm_content,
                "tool_call_id": tool_result.tool_name  # Using tool name as identifier if no specific ID is available
            })
        else:
            # Create a minimal messages array with just the tool result
            # This is a fallback when conversation history isn't provided
            messages = [
                {
                    "role": "tool",
                    "content": tool_result.llm_content,
                    "tool_call_id": tool_result.tool_name
                }
            ]
        
        # Create the request with the full conversation context
        request = {
            "messages": messages,
            "model": self.model,
            "temperature": llm_config.llm_temperature,
            "max_tokens": llm_config.llm_max_tokens
        }
        
        # Generate content using the pipeline with the full conversation context
        response = await self.generate_content(request, user_prompt_id=f"tool_result_{id(tool_result)}")
        
        # Use the converter to properly format the response
        # But first check if the response is already in the expected kernel format (from pipeline)
        if isinstance(response, dict) and "content" in response and "tool_calls" in response:
            # The response is already in the expected format (likely from pipeline)
            formatted_response = response
        else:
            try:
                formatted_response = self.converter.convert_provider_response_to_kernel(response)
            except Exception:
                # If converter fails (e.g., in mock scenarios), use fallback format
                formatted_response = {
                    "content": response.get("content", "") if isinstance(response, dict) else str(response),
                    "tool_calls": response.get("tool_calls", []) if isinstance(response, dict) else []
                }
        
        # Additional processing: Check if the LLM returned JSON tool calls in the content
        # and extract them if the tool_calls field is empty
        content = formatted_response.get("content", "")
        tool_calls = formatted_response.get("tool_calls", [])
        
        # Debug: Print what we got from the pipeline before processing
        print(f"DEBUG: Content generator received from pipeline in process_tool_result - content: {repr(content)}, tool_calls: {tool_calls}")
        
        # If no tool calls were extracted by the converter but content might contain them
        if not tool_calls and content.strip():
            extracted_tool_calls = self._extract_tool_calls_from_content(content)
            if extracted_tool_calls:
                # Update tool calls and clean content
                tool_calls = extracted_tool_calls
                # Remove tool call JSON from content
                cleaned_content = self._remove_tool_calls_from_content(content)
                content = cleaned_content
        
        # Convert to the expected response format
        # Also convert tool call dictionaries to proper ToolCall objects if they aren't already
        from .tool_call_processor import ToolCall
        
        processed_tool_calls = []
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                # Convert dictionary to ToolCall object
                # Handle different possible structures of tool call dictionaries
                if "function" in tool_call:  # OpenAI-style structure
                    function_data = tool_call.get("function", {})
                    # Parse arguments string to dictionary if needed
                    arguments = function_data.get("arguments", {})
                    if isinstance(arguments, str):
                        import json
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, keep original string value
                            arguments = function_data.get("arguments", {})
                    
                    processed_tool_calls.append(ToolCall(
                        id=tool_call.get("id", ""),
                        name=function_data.get("name", ""),
                        arguments=arguments
                    ))
                else:  # Direct structure
                    processed_tool_calls.append(ToolCall(
                        id=tool_call.get("id", ""),
                        name=tool_call.get("name", ""),
                        arguments=tool_call.get("arguments", {})
                    ))
            else:
                # Already a ToolCall object
                processed_tool_calls.append(tool_call)
        
        class ResponseObj:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else []
                self.name = "openai_response"  # For attribute access
        
        return ResponseObj(
            content=content,
            tool_calls=processed_tool_calls
        )
    
    async def stream_response(self, prompt: str, system_context: str = None, tools: list = None) -> AsyncIterator[str]:
        """
        Stream a response to the given prompt.
        Implements the interface expected by the ai_orchestrator.
        
        Args:
            prompt: The input prompt
            system_context: Optional system context/prompt to provide to the LLM
            tools: Optional list of tools to provide to the LLM for native function calling
            
        Yields:
            Partial response strings as they become available
        """
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