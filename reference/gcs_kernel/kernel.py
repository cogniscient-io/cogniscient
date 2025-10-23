"""
Main GCS Kernel implementation.

This module implements the core GCSKernel class which provides
the foundational services for the Generic Control System Kernel.
"""

import asyncio
from typing import Dict, Any, Optional

from gcs_kernel.models import ResourceQuota
from gcs_kernel.event_loop import EventLoop
from gcs_kernel.scheduler import ToolExecutionScheduler
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.resource_manager import ResourceAllocationManager
from gcs_kernel.security import SecurityLayer
from gcs_kernel.logger import EventLogger
from gcs_kernel.mcp.client import MCPClient


class GCSKernel:
    """
    Core GCS Kernel class implementing the main orchestration functionality.
    
    The GCS Kernel provides operating-system-like services for streaming AI agent
    orchestration, including event loop management, tool execution scheduling,
    resource allocation, and security enforcement.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the GCS Kernel with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Initialize core services
        self.event_loop = EventLoop()
        self.scheduler = ToolExecutionScheduler()
        self.registry = ToolRegistry()
        self.resource_manager = ResourceAllocationManager()
        self.security_layer = SecurityLayer()
        self.logger = EventLogger()
        self.mcp_client = MCPClient()
        
        # Initialize with resource quotas
        self.resource_quota = ResourceQuota(**self.config.get('resource_quota', {}))
        
        # Set up shutdown flag
        self._running = False

    async def run(self):
        """
        Start the GCS Kernel and its event loop.
        
        This method initializes all components and starts the main event loop
        that processes streaming AI responses and tool execution events.
        """
        self._running = True
        
        # Initialize all components
        await self._initialize_components()
        
        # Start the event loop
        await self.event_loop.run()

    async def shutdown(self):
        """
        Gracefully shut down the GCS Kernel.
        
        This method performs a graceful shutdown sequence, stopping the event
        loop and cleaning up all components.
        """
        self._running = False
        
        # Stop the event loop first
        await self.event_loop.shutdown()
        
        # Clean up components
        await self._cleanup_components()

    async def _initialize_components(self):
        """
        Initialize all kernel components in proper order.
        
        This method initializes each component in the required order to ensure
        proper dependencies are met.
        """
        # Initialize security first
        await self.security_layer.initialize()
        
        # Initialize resource manager
        await self.resource_manager.initialize()
        
        # Initialize registry
        await self.registry.initialize()
        
        # Initialize scheduler
        await self.scheduler.initialize()
        
        # Initialize logger
        await self.logger.initialize()
        
        # Initialize MCP client
        await self.mcp_client.initialize()

    async def _cleanup_components(self):
        """
        Clean up all kernel components during shutdown.
        
        This method performs cleanup operations for all components in reverse
        order of initialization.
        """
        # Clean up components in reverse order
        await self.mcp_client.shutdown()
        await self.logger.shutdown()
        await self.scheduler.shutdown()
        await self.registry.shutdown()
        await self.resource_manager.shutdown()
        await self.security_layer.shutdown()

    def is_running(self) -> bool:
        """
        Check if the kernel is currently running.
        
        Returns:
            True if the kernel is running, False otherwise
        """
        return self._running