"""
Main GCS Kernel implementation.

This module implements the core GCSKernel class which provides
the foundational services for the Generic Control System Kernel.
"""

import uuid
from typing import Dict, Any, Optional

from gcs_kernel.models import ResourceQuota, PromptObject
from gcs_kernel.event_loop import EventLoop
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.resource_manager import ResourceAllocationManager
from gcs_kernel.security import SecurityLayer
from gcs_kernel.logger import EventLogger
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.tool_execution_manager import ToolExecutionManager
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from services.config import settings


class GCSKernel:
    """
    Core GCS Kernel class implementing the main orchestration functionality.
    
    The GCS Kernel provides operating-system-like services for streaming AI agent
    orchestration, including event loop management, tool execution via ToolExecutionManager,
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
        self.registry = ToolRegistry()
        self.resource_manager = ResourceAllocationManager()
        self.security_layer = SecurityLayer()
        self.logger = EventLogger()
        self.mcp_client = MCPClient()
        
        # Initialize prompt object registry
        self.prompt_object_registry = {}
        
        # Initialize the unified ToolExecutionManager for handling all tool execution scenarios
        self.tool_execution_manager = ToolExecutionManager(
            kernel_registry=self.registry,
            mcp_client=self.mcp_client,
            logger=self.logger
        )
        
        # Initialize AI orchestrator with direct kernel access for simplified architecture
        # Create content generator using settings
        content_generator = LLMContentGenerator()
        # Initialize orchestrator as the primary AI interaction handler
        self.ai_orchestrator = AIOrchestratorService(
            self.mcp_client,
            content_generator=content_generator,
            kernel=self
        )
        # Set kernel services for direct access by orchestrator
        self.ai_orchestrator.set_kernel_services(
            registry=self.registry,
            # Use the tool_execution_manager instead of the old scheduler
            tool_execution_manager=self.tool_execution_manager
        )
        
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
        
        # Initialize tool execution manager
        # No initialization needed as it happens in the constructor
        
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
        
        # Shutdown the tool execution manager
        await self.tool_execution_manager.shutdown()
        
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



    def create_prompt_object(self, content: str, **kwargs) -> PromptObject:
        """Create a new prompt object with the given content and additional properties."""
        # Apply system defaults if not provided in kwargs
        if kwargs.get('max_tokens') is None:
            kwargs['max_tokens'] = settings.llm_max_tokens
        if kwargs.get('temperature') is None:
            kwargs['temperature'] = settings.llm_temperature
        
        prompt_obj = PromptObject.create(
            content=content,
            **kwargs
        )
        # Register the prompt object
        self.prompt_object_registry[prompt_obj.prompt_id] = prompt_obj
        return prompt_obj

    def get_prompt_object(self, prompt_id: str) -> Optional[PromptObject]:
        """
        Get a prompt object by its ID.
        
        Args:
            prompt_id: The ID of the prompt object
            
        Returns:
            The prompt object if found, None otherwise
        """
        return self.prompt_object_registry.get(prompt_id)

    async def submit_prompt(self, content: str, **kwargs) -> str:
        """
        Submit a new prompt for processing using the new architecture.
        
        Args:
            content: The prompt content
            **kwargs: Additional properties to set on the prompt object
            
        Returns:
            The processed result content
        """
        # Apply system defaults if not provided in kwargs
        if kwargs.get('max_tokens') is None:
            kwargs['max_tokens'] = settings.llm_max_tokens
        if kwargs.get('temperature') is None:
            kwargs['temperature'] = settings.llm_temperature
        
        # Create a prompt object from the input using the factory method
        prompt_obj = PromptObject.create(
            content=content,
            streaming_enabled=False,
            **kwargs
        )
        
        # Register the prompt object
        self.prompt_object_registry[prompt_obj.prompt_id] = prompt_obj
        
        # Process through the orchestrator using prompt object
        if self.ai_orchestrator:
            # Use the orchestrator method that works with prompt objects directly
            result_prompt_obj = await self.ai_orchestrator.handle_ai_interaction(prompt_obj)
            
            # Update the registry with the processed prompt object
            self.prompt_object_registry[prompt_obj.prompt_id] = result_prompt_obj
            
            # Return the result content
            return result_prompt_obj.result_content

    async def stream_prompt(self, content: str, **kwargs):
        """
        Stream a prompt for processing using the new architecture.
        
        Args:
            content: The prompt content
            **kwargs: Additional properties to set on the prompt object
            
        Yields:
            Partial response strings as they become available
        """
        # Apply system defaults if not provided in kwargs
        if kwargs.get('max_tokens') is None:
            kwargs['max_tokens'] = settings.llm_max_tokens
        if kwargs.get('temperature') is None:
            kwargs['temperature'] = settings.llm_temperature
        
        # Create a prompt object from the input using the factory method
        prompt_obj = PromptObject.create(
            content=content,
            streaming_enabled=True,
            **kwargs
        )
        
        # Register the prompt object
        self.prompt_object_registry[prompt_obj.prompt_id] = prompt_obj
        
        # Stream through the orchestrator using prompt object
        if self.ai_orchestrator:
            # For streaming, we use the orchestrator method that works with prompt objects
            async for chunk in self.ai_orchestrator.stream_ai_interaction(prompt_obj):
                yield chunk

