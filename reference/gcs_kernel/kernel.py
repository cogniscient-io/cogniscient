"""
Main GCS Kernel implementation.

This module implements the core GCSKernel class which provides
the foundational services for the Generic Control System Kernel.
"""

import asyncio
from typing import Dict, Any, Optional

from gcs_kernel.models import ResourceQuota, ToolInclusionConfig
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
        
        # Initialize prompt configuration registry
        self.prompt_config_registry = {}
        
        # Initialize AI orchestrator with direct kernel access for simplified architecture
        from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
        from services.llm_provider.content_generator import LLMContentGenerator
        from services.config import settings
        # Create content generator using settings
        content_generator = LLMContentGenerator()
        # Initialize orchestrator as the primary AI interaction handler
        self.ai_orchestrator = AIOrchestratorService(
            kernel_client=self.mcp_client,
            content_generator=content_generator,
            kernel=self
        )
        # Set kernel services for direct access by orchestrator
        self.ai_orchestrator.set_kernel_services(
            registry=self.registry,
            scheduler=self.scheduler
        )
        
        # Connect scheduler to the registry so it can execute tools
        self.scheduler.tool_registry = self.registry
        
        # Initialize with resource quotas
        self.resource_quota = ResourceQuota(**self.config.get('resource_quota', {}))
        
        # Set up shutdown flag
        self._running = False
        # Set up initialization flag
        self._fully_initialized = False

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
        
        # Initialize registry with reference to kernel for system tools
        await self.registry.initialize(kernel=self)
        
        # Initialize scheduler
        await self.scheduler.initialize()
        
        # Initialize logger
        await self.logger.initialize()
        
        # Initialize MCP client
        await self.mcp_client.initialize()
        
        # AI orchestrator is initialized with content generator in constructor
        
        # Set a readiness flag that works across async/sync boundaries
        self._fully_initialized = True

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

    def register_prompt_config(self, prompt_id: str, config: 'ToolInclusionConfig'):
        """
        Register a prompt configuration with the kernel.
        
        Args:
            prompt_id: Unique identifier for the prompt
            config: The tool inclusion configuration for the prompt
        """
        self.prompt_config_registry[prompt_id] = config

    def get_prompt_config(self, prompt_id: str) -> Optional['ToolInclusionConfig']:
        """
        Get the configuration for a specific prompt.
        
        Args:
            prompt_id: Unique identifier for the prompt
            
        Returns:
            The tool inclusion configuration for the prompt, or None if not found
        """
        return self.prompt_config_registry.get(prompt_id)

    def remove_prompt_config(self, prompt_id: str):
        """
        Remove a prompt configuration from the registry.
        
        Args:
            prompt_id: Unique identifier for the prompt
        """
        if prompt_id in self.prompt_config_registry:
            del self.prompt_config_registry[prompt_id]

    async def send_user_prompt(self, prompt: str) -> str:
        """
        Handle a user prompt through the AI orchestrator.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The AI response string
        """
        return await self.ai_orchestrator.handle_ai_interaction(prompt)

    async def stream_user_prompt(self, prompt: str):
        """
        Stream a user prompt through the AI orchestrator.
        
        Args:
            prompt: The user's input prompt
            
        Yields:
            Partial response strings as they become available
        """
        async for chunk in self.ai_orchestrator.stream_ai_interaction(prompt):
            yield chunk