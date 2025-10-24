"""
AI Orchestrator Service implementation for the GCS Kernel.

This module implements the AIOrchestratorService which manages AI interactions,
session management, and provider abstraction. It now uses the abstract
content generator backend following OpenAI-compatible patterns with Pydantic Settings.
"""

from typing import Any
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import ToolResult
from services.llm_provider.base_generator import BaseContentGenerator
from services.llm_provider.content_generator import OpenAIContentGenerator


class AIOrchestratorService:
    """
    AI Orchestrator Service that manages AI interactions and conversation session state.
    Uses any content generator that extends BaseContentGenerator.
    """
    
    def __init__(self, kernel_client: MCPClient):
        """
        Initialize the AI orchestrator with a kernel client.
        
        Args:
            kernel_client: MCP client for communicating with the kernel server
        """
        # Accept MCP client to communicate with kernel server
        self.kernel_client = kernel_client
        self.content_generator = None  # To be initialized with specific provider

    async def initialize_with_config(self):
        """
        Initialize the orchestrator with Pydantic settings.
        Creates and configures the appropriate content generator using settings.
        """
        # Create the appropriate content generator based on Pydantic settings
        # For now, we're using the OpenAI provider directly with its settings
        self.content_generator = OpenAIContentGenerator()

    async def initialize_with_provider(self, provider: BaseContentGenerator):
        """
        Initialize the orchestrator with a specific content generator provider.
        The provider should extend BaseContentGenerator.
        
        Args:
            provider: The content generator to use for AI interactions
        """
        self.content_generator = provider

    async def handle_ai_interaction(self, prompt: str) -> str:
        """
        Handle an AI interaction and process any tool calls.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The AI response string
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Use AI client to generate response with potential tool calls
        response = await self.content_generator.generate_response(prompt)
        
        # Process any tool calls in the response
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                # Submit tool execution through kernel using MCP
                execution_id = await self.kernel_client.submit_tool_execution(
                    tool_call.name,
                    tool_call.parameters
                )
                
                # Wait for tool execution to complete
                result = await self.kernel_client.get_execution_result(execution_id)
                
                # Process the result and continue interaction
                response = await self.content_generator.process_tool_result(result)
        
        return getattr(response, 'content', str(response))
    
    async def stream_ai_interaction(self, prompt: str):
        """
        Stream an AI interaction and process any tool calls.
        
        Args:
            prompt: The user's input prompt
        """
        if not self.content_generator:
            raise Exception("No content generator initialized")
        
        # Stream the response using the content generator's streaming capability
        async for chunk in self.content_generator.stream_response(prompt):
            yield chunk