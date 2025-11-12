"""
Main GCS Kernel implementation.

This module implements the core GCSKernel class which provides
the foundational services for the Generic Control System Kernel.
"""

import uuid
from typing import Dict, Any, Optional

from gcs_kernel.models import ResourceQuota, PromptObject, MCPConfig
from gcs_kernel.event_loop import EventLoop
from gcs_kernel.registry import ToolRegistry
from gcs_kernel.resource_manager import ResourceAllocationManager
from gcs_kernel.security import SecurityLayer
from gcs_kernel.logger import EventLogger
from gcs_kernel.mcp.client_manager import MCPClientManager
from gcs_kernel.tool_execution_manager import ToolExecutionManager
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService
from services.llm_provider.content_generator import LLMContentGenerator
from common.settings import settings

# Tool registration imports (all consolidated at top of file)
from gcs_kernel.tools.file_operations import register_file_operation_tools
from gcs_kernel.tools.shell_command import register_shell_command_tools
from gcs_kernel.tools.system_tools import register_system_tools
from gcs_kernel.tools.mcp_tools import register_mcp_tools


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
        # Initialize MCP client manager first - use config if provided, otherwise default
        mcp_config = config.get('mcp_config', None) if config else None
        if mcp_config is None:
            mcp_config = MCPConfig(server_url="http://localhost:8000")
        self.mcp_client_manager = MCPClientManager(mcp_config)
        
        # Initialize registry with access to the MCP client manager
        self.registry = ToolRegistry(mcp_client_manager=self.mcp_client_manager)
        
        self.resource_manager = ResourceAllocationManager()
        self.security_layer = SecurityLayer()
        self.logger = EventLogger()
        
        # Initialize prompt object registry
        self.prompt_object_registry = {}
        
        # Initialize the unified ToolExecutionManager for handling all tool execution scenarios
        self.tool_execution_manager = ToolExecutionManager(
            kernel_registry=self.registry,
            mcp_client=self.mcp_client_manager,  # Use manager instead of single client
            logger=self.logger
        )
        
        # Initialize AI orchestrator with direct kernel access for simplified architecture
        # Create the Adaptive Loop Service (without orchestrator initially)
        from services.adaptive_loop.adaptive_loop_service import AdaptiveLoopService
        self.adaptive_loop_service = AdaptiveLoopService(
            mcp_client=self.mcp_client_manager,
            ai_orchestrator=None  # Will be set after creation
        )
        
        # Create content generator with the adaptive loop service
        content_generator = LLMContentGenerator(adaptive_loop_service=self.adaptive_loop_service)
        content_generator.kernel = self  # Set kernel reference for model info updates
        
        # Initialize orchestrator as the primary AI interaction handler
        self.ai_orchestrator = AIOrchestratorService(
            self.mcp_client_manager,
            content_generator=content_generator,
            kernel=self
        )
        
        # Now set the orchestrator in the adaptive loop service
        self.adaptive_loop_service.ai_orchestrator = self.ai_orchestrator
        
        # Set kernel services for direct access by orchestrator
        self.ai_orchestrator.set_kernel_services(
            registry=self.registry,
            # Use the tool_execution_manager instead of the old scheduler
            tool_execution_manager=self.tool_execution_manager
        )
        
        # Initialize with resource quotas
        self.resource_quota = ResourceQuota(**self.config.get('resource_quota', {}))

        # Initialize the Tool Discovery Service
        from services.tool_discovery.mcp_discovery import ToolDiscoveryService
        self.tool_discovery_service = ToolDiscoveryService(self.registry)
        self.tool_discovery_service.logger = self.logger  # Set logger

        # Set up shutdown flag
        self._running = False
        # Set up initialization flag
        self._fully_initialized = False

    async def fetch_model_info_and_update_settings(self):
        """
        Fetch model information from the provider and update system settings accordingly.
        Uses .env setting as fallback if model information cannot be retrieved.
        """
        # Try to get the provider from the content generator
        if self.ai_orchestrator and self.ai_orchestrator.content_generator:
            provider = self.ai_orchestrator.content_generator.provider
            model_name = self.ai_orchestrator.content_generator.provider.model
            
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                # Fetch model information
                model_info = await provider.get_model_info(model_name)
                
                # Extract max context length from model information
                max_context_length = model_info.get('max_context_length', settings.llm_max_context_length)
                
                logger.info(f"Model {model_name} has max context length: {max_context_length}")
                
                # Update the settings value with the actual model capability
                old_max_context_length = settings.llm_max_context_length
                settings.llm_max_context_length = max_context_length
                
                logger.info(f"Updated llm_max_context_length from {old_max_context_length} to {max_context_length}")
                
                # Return the actual model context length for immediate use
                return max_context_length
            except Exception as e:
                logger.error(f"Failed to fetch model info for {model_name}: {str(e)}")
                # Fallback to .env setting
                logger.info(f"Using fallback max_context_length: {settings.llm_max_context_length}")
                return settings.llm_max_context_length
        else:
            logger.error("Could not access provider to fetch model information")
            return settings.llm_max_context_length



    async def run(self):
        """
        Start the GCS Kernel and its event loop.
        
        This method initializes all components and starts the main event loop
        that processes streaming AI responses and tool execution events.
        """
        self._running = True
        
        # Initialize all components
        await self._initialize_components()
        
        # Connect the kernel registry to the MCP manager so external tools can be registered
        await self._connect_registry_to_mcp()
        
        # Set up logger for MCP manager after initialization
        self.mcp_client_manager.logger = self.logger
        
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
        import time
        start_time = time.time()
        
        if self.logger:
            self.logger.debug("Starting kernel component initialization")
        
        # Initialize security first
        if self.logger:
            self.logger.debug("Initializing security layer...")
        await self.security_layer.initialize()
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"Security layer initialized (elapsed: {elapsed:.2f}s)")
        
        # Initialize resource manager
        if self.logger:
            self.logger.debug("Initializing resource manager...")
        await self.resource_manager.initialize()
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"Resource manager initialized (elapsed: {elapsed:.2f}s)")
        
        # Initialize logger
        if self.logger:
            self.logger.debug("Initializing logger...")
        await self.logger.initialize()
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"Logger initialized (elapsed: {elapsed:.2f}s)")
        
        # Initialize MCP manager with logger reference
        self.mcp_client_manager.logger = self.logger
        if self.logger:
            self.logger.debug("Initializing MCP manager...")
        await self.mcp_client_manager.initialize()
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"MCP manager initialized (elapsed: {elapsed:.2f}s)")
        
        # Connect the MCP client manager to the tool discovery service
        self.mcp_client_manager._tool_discovery_service = self.tool_discovery_service
        
        # Initialize registry with reference to kernel for system tools
        if self.logger:
            self.logger.debug("Initializing registry...")
        await self.registry.initialize(kernel=self)
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"Registry initialized (elapsed: {elapsed:.2f}s)")
        
        # Register all tools after the registry is initialized
        if self.logger:
            self.logger.debug("Starting tool registration...")
        
        tool_start_time = time.time()
        await register_file_operation_tools(self)
        if self.logger:
            elapsed = time.time() - tool_start_time
            total_elapsed = time.time() - start_time
            self.logger.debug(f"File operation tools registered (step: {elapsed:.2f}s, total: {total_elapsed:.2f}s)")
        
        await register_shell_command_tools(self)
        if self.logger:
            elapsed = time.time() - tool_start_time
            total_elapsed = time.time() - start_time
            self.logger.debug(f"Shell command tools registered (step: {elapsed:.2f}s, total: {total_elapsed:.2f}s)")
        
        await register_system_tools(self)
        if self.logger:
            elapsed = time.time() - tool_start_time
            total_elapsed = time.time() - start_time
            self.logger.debug(f"System tools registered (step: {elapsed:.2f}s, total: {total_elapsed:.2f}s)")
        
        await register_mcp_tools(self)
        if self.logger:
            elapsed = time.time() - tool_start_time
            total_elapsed = time.time() - start_time
            self.logger.debug(f"MCP tools registered (step: {elapsed:.2f}s, total: {total_elapsed:.2f}s)")
        
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"All tools registered (elapsed: {elapsed:.2f}s)")
        
        # Initialize tool execution manager
        # No initialization needed as it happens in the constructor
        
        # AI orchestrator is initialized with content generator in constructor
        
        # Set a readiness flag that works across async/sync boundaries
        self._fully_initialized = True
        if self.logger:
            elapsed = time.time() - start_time
            self.logger.debug(f"Kernel fully initialized (elapsed: {elapsed:.2f}s)")

    async def _connect_registry_to_mcp(self):
        """
        Connect the kernel registry to the MCP manager so external tools can be registered.
        """
        # Register notification handlers to manage tools dynamically
        self.mcp_client_manager.register_notification_handler("tool_added", self._on_tool_added)
        self.mcp_client_manager.register_notification_handler("tool_removed", self._on_tool_removed)
        self.mcp_client_manager.register_notification_handler("tool_updated", self._on_tool_updated)
    
    def _on_tool_added(self, server_id: str, tool_data: dict):
        """
        Handle when an external server notifies that a tool has been added.
        """
        if self.logger:
            self.logger.info(f"Kernel: Tool added notification from server {server_id}: {tool_data.get('tool_name', 'Unknown')}")
        
        # Pass the event to the tool discovery service
        try:
            tool_name = tool_data.get('tool_name')
            server_url = tool_data.get('server_url')  # Assuming server_url is passed in tool_data
            if tool_name and server_url:
                if self.logger:
                    self.logger.info(f"Kernel: Scheduling tool addition - {tool_name} from server {server_id}")
                # This is an async method, so we'll schedule it
                import asyncio
                asyncio.create_task(self.tool_discovery_service.handle_tool_added(server_id, tool_name, server_url, tool_data))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Kernel: Error handling tool added notification: {e}")
    
    def _on_tool_removed(self, server_id: str, tool_data: dict):
        """
        Handle when an external server notifies that a tool has been removed.
        """
        if self.logger:
            self.logger.info(f"Tool removed notification from server {server_id}: {tool_data.get('tool_name', 'Unknown')}")
        
        # Pass the event to the tool discovery service
        try:
            tool_name = tool_data.get('tool_name')
            if tool_name:
                import asyncio
                asyncio.create_task(self.tool_discovery_service.handle_tool_removed(server_id, tool_name))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error handling tool removed notification: {e}")
    
    def _on_tool_updated(self, server_id: str, tool_data: dict):
        """
        Handle when an external server notifies that a tool has been updated.
        """
        if self.logger:
            self.logger.info(f"Tool updated notification from server {server_id}: {tool_data.get('tool_name', 'Unknown')}")
        
        # Pass the event to the tool discovery service
        try:
            tool_name = tool_data.get('tool_name')
            server_url = tool_data.get('server_url')  # Assuming server_url is passed in tool_data
            if tool_name and server_url:
                import asyncio
                asyncio.create_task(self.tool_discovery_service.handle_tool_updated(server_id, tool_name, server_url, tool_data))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error handling tool updated notification: {e}")

    async def _cleanup_components(self):
        """
        Clean up all kernel components during shutdown.
        
        This method performs cleanup operations for all components in reverse
        order of initialization.
        """
        # Clean up components in reverse order
        await self.mcp_client_manager.shutdown()
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
            # Use settings value directly (which can be updated at runtime)
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
            # Use settings value directly (which can be updated at runtime)
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

