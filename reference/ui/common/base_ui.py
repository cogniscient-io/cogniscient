"""
Common base UI classes and interfaces for different UI implementations.
This module provides a base UI class that can be extended for both CLI and web UI.
"""

import asyncio
from typing import AsyncGenerator, Any, Protocol
from abc import ABC, abstractmethod


class KernelAPIProtocol(Protocol):
    """Protocol for kernel API access."""
    
    async def send_user_prompt(self, prompt: str) -> str:
        """Send a user prompt and receive a complete response."""
        ...
    
    async def stream_user_prompt(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream a user prompt and receive chunks."""
        ...
    
    def get_kernel_status(self) -> str:
        """Get kernel status."""
        ...
    
    def list_registered_tools(self) -> list:
        """List registered tools."""
        ...
    
    async def get_available_tools(self):
        """Get all available tools from the kernel."""
        ...
    
    async def execute_tool(self, tool_name: str, params: dict):
        """Execute a specific tool with parameters."""
        ...
    
    async def get_tool_result(self, execution_id: str):
        """Get the result of a tool execution."""
        ...


class BaseUI(ABC):
    """Base UI class that provides common functionality for different UI implementations."""
    
    def __init__(self, kernel_api: KernelAPIProtocol):
        self.kernel_api = kernel_api
    
    @abstractmethod
    async def display_streaming_response(self, prompt: str) -> str:
        """Display a streaming response from the kernel."""
        pass
    
    @abstractmethod
    async def display_response(self, prompt: str) -> str:
        """Display a non-streaming response from the kernel."""
        pass
    
    def get_kernel_status(self) -> str:
        """Get kernel status from the kernel API."""
        return self.kernel_api.get_kernel_status()
    
    def list_tools(self) -> list:
        """List available tools from the kernel API."""
        return self.kernel_api.list_registered_tools()


class StreamingHandler:
    """Handles streaming responses with proper async resource management."""
    
    def __init__(self):
        self._active_tasks = set()
    
    async def handle_streaming_with_callback(
        self, 
        stream_generator: AsyncGenerator[str, None], 
        chunk_callback
    ) -> str:
        """
        Handle a streaming generator with a callback for each chunk.
        
        Args:
            stream_generator: The async generator producing chunks
            chunk_callback: Function to call for each chunk received
            
        Returns:
            Complete response string
        """
        response_chunks = []
        
        try:
            async for chunk in stream_generator:
                response_chunks.append(chunk)
                if chunk_callback:
                    chunk_callback(chunk)
        except Exception as e:
            # Handle any errors during streaming
            if chunk_callback:
                chunk_callback(f"\nError during streaming: {str(e)}")
            raise
        
        return "".join(response_chunks)
    
    async def safely_cancel_tasks(self):
        """Safely cancel any remaining tasks."""
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
        self._active_tasks.clear()