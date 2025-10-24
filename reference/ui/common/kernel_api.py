"""
Kernel API client for UI components.
This provides a clean interface to the kernel that UI components can use.
"""

import asyncio
from typing import AsyncGenerator
from .base_ui import KernelAPIProtocol


class KernelAPIClient(KernelAPIProtocol):
    """API client that provides clean interface to the kernel for UI components."""
    
    def __init__(self, kernel):
        """
        Initialize the kernel API client.
        
        Args:
            kernel: The GCSKernel instance to communicate with
        """
        self.kernel = kernel
    
    async def send_user_prompt(self, prompt: str) -> str:
        """Send a user prompt and receive a complete response."""
        return await self.kernel.send_user_prompt(prompt)
    
    async def stream_user_prompt(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream a user prompt and receive chunks."""
        async for chunk in self.kernel.stream_user_prompt(prompt):
            yield chunk
    
    def get_kernel_status(self) -> str:
        """Get kernel status."""
        return f"Kernel running: {self.kernel.is_running()}"
    
    def list_registered_tools(self) -> list:
        """List registered tools."""
        if self.kernel.registry:
            tools = self.kernel.registry.get_all_tools()
            return list(tools.keys())
        return []