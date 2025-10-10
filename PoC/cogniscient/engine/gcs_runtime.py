"""Generic Control System (GCS) Runtime for PoC.
Following the ringed architecture refactoring, this is now the kernel layer
that manages services and coordinates system operations.
"""

from cogniscient.engine.kernel import Kernel
from cogniscient.engine.services.config_service import ConfigServiceImpl
from cogniscient.engine.services.agent_service import AgentServiceImpl
from cogniscient.engine.services.llm_service import LLMServiceImpl
from cogniscient.engine.services.auth_service import AuthServiceImpl
from cogniscient.engine.services.storage_service import StorageServiceImpl
from cogniscient.engine.services.system_parameters_service import SystemParametersService
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings


class GCSRuntime:
    """Core GCS runtime refactored to follow ringed architecture as the kernel."""

    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK"):
        """Initialize the GCS runtime following the ringed architecture.
        
        Args:
            config_dir (str): Directory to load agent configurations from.
            agents_dir (str): Directory where agent modules are located.
        """
        # Initialize the kernel
        self.kernel = Kernel()
        
        # Initialize system services in dependency order
        self.config_service = ConfigServiceImpl(config_dir=config_dir)
        self.system_parameters_service = SystemParametersService()
        self.agent_service = AgentServiceImpl(
            agents_dir=agents_dir,
            runtime_ref=self
        )
        
        # Initialize attributes needed by session manager
        self.agents = {}
        self.chat_interfaces = []
        self.current_config_name = "default"
        
        # Initialize token manager for OAuth
        self.token_manager = TokenManager(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        # Initialize LLM service with token manager
        from cogniscient.llm.llm_service import LLMService
        llm_service_internal = LLMService(self.token_manager)
        llm_service_internal.set_provider(settings.default_provider)
        
        # Initialize MCP service
        self.mcp_service = None
        
        # Initialize the contextual LLM service with MCP client service as None initially
        # Will be updated once MCP service is initialized
        from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService
        self.llm_service = ContextualLLMService(
            provider_manager=llm_service_internal,
            mcp_client_service=None
        )
        
        # Initialize auth and storage services
        self.auth_service = AuthServiceImpl(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        self.storage_service = StorageServiceImpl()
        
        # Register services with the kernel
        self.kernel.register_service("config", self.config_service)
        self.kernel.register_service("agent", self.agent_service)
        self.kernel.register_service("llm", LLMServiceImpl(
            provider_manager=llm_service_internal,
            mcp_client_service=None  # Will be updated after MCP initialization
        ))
        self.kernel.register_service("auth", self.auth_service)
        self.kernel.register_service("storage", self.storage_service)
        self.kernel.register_service("system_params", self.system_parameters_service)
        
        # Initialize the MCP service after all other components
        # This prevents initialization order issues
        self.mcp_service = MCPService(self)
        
        # Update the LLM service with MCP client service now that it's available
        self.llm_service.mcp_client_service = self.mcp_service.mcp_client
        
        # Also update the LLM service in the kernel
        llm_service_impl_kernel = LLMServiceImpl(
            provider_manager=llm_service_internal,
            mcp_client_service=self.mcp_service.mcp_client
        )
        llm_service_impl_kernel.set_runtime(self)  # Set runtime for the kernel's LLM service instance
        self.kernel.service_registry["llm"] = llm_service_impl_kernel
        
        # Set runtime reference in services that need access to MCP
        self.config_service.set_runtime(self)
        self.system_parameters_service.set_runtime(self)
        self.agent_service.set_runtime(self)
        self.storage_service.set_runtime(self)
        self.auth_service.set_runtime(self)
        # Note: self.llm_service is ContextualLLMService which doesn't have set_runtime method
        # The LLMServiceImpl instance in kernel registry has runtime set separately
        
        # Register MCP tools for services that have them - now that MCP service is initialized
        self.config_service.register_mcp_tools()
        self.system_parameters_service.register_mcp_tools()
        self.agent_service.register_mcp_tools()
        self.storage_service.register_mcp_tools()
        # Use the LLM service from the kernel's service registry
        llm_service_impl = self.kernel.service_registry.get("llm")
        if llm_service_impl and hasattr(llm_service_impl, "register_mcp_tools"):
            llm_service_impl.register_mcp_tools()
        self.auth_service.register_mcp_tools()
    
    def register_chat_interface(self, chat_interface):
        """Register a chat interface with the runtime."""
        self.chat_interfaces.append(chat_interface)
    
    def unregister_chat_interface(self, chat_interface):
        """Unregister a chat interface from the runtime."""
        if chat_interface in self.chat_interfaces:
            self.chat_interfaces.remove(chat_interface)
    
    def get_current_config_name(self):
        """Get the name of the current configuration."""
        return self.current_config_name




























    def start_kernel_loop(self):
        """
        Start the kernel's main control loop which manages system operations.
        This is the 'brain' of the system that coordinates all agent activities.
        """
        return self.kernel.start_system()

    async def shutdown(self) -> None:
        """Shutdown all services."""
        # Shutdown services through the kernel
        await self.kernel.shutdown()
        
        # Shutdown MCP services to properly close connections
        if hasattr(self, 'mcp_service') and self.mcp_service:
            try:
                await self.mcp_service.mcp_client.shutdown()
            except Exception as e:
                print(f"Warning: Error during MCP service shutdown: {e}")
        
        # Ensure proper cleanup of any remaining async resources, especially LiteLLM's resources
        try:
            # Try to close the LLM service which should handle LiteLLM adapter cleanup
            if hasattr(self, 'llm_service') and self.llm_service and hasattr(self.llm_service, 'close'):
                await self.llm_service.close()
        except Exception as e:
            print(f"Warning: Error during LLM service cleanup: {e}")
            # If the above fails, try a different approach
            try:
                import gc
                # Force garbage collection to clean up any remaining resources
                gc.collect()
            except Exception:
                pass  # If all else fails, just continue